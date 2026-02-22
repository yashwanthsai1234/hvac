"""Chat endpoint — streaming SSE chat with tool-calling via OpenAI."""

import json
import os

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from openai import OpenAI

from backend.db.connection import get_db
from backend.tools.field_notes import get_field_notes
from backend.tools.labor_detail import get_labor_detail
from backend.tools.co_detail import get_co_detail
from backend.tools.rfi_detail import get_rfi_detail
from backend.tools.what_if_margin import what_if_margin
from backend.tools.send_email import send_email

router = APIRouter()

MODEL = "gpt-4o-mini"

# OpenAI function definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_field_notes",
            "description": "Search field notes for a project. Can filter by date range and keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "End date YYYY-MM-DD"},
                    "keyword": {"type": "string", "description": "Keyword to search in note content"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_labor_detail",
            "description": "Get labor hours and costs for a project, broken down by SOV line and role.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "sov_line_id": {"type": "string", "description": "Optional SOV line ID to filter"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_co_detail",
            "description": "Get change order details for a project, optionally filtered by CO number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "co_number": {"type": "string", "description": "Optional CO number to filter"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rfi_detail",
            "description": "Get RFI details for a project, optionally filtered by RFI number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "rfi_number": {"type": "string", "description": "Optional RFI number to filter"},
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "what_if_margin",
            "description": "Run a what-if margin scenario: co_rejected, co_approved, or labor_recovery.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "scenario": {
                        "type": "string",
                        "enum": ["co_rejected", "co_approved", "labor_recovery"],
                        "description": "Scenario to run",
                    },
                    "co_number": {"type": "string", "description": "CO number (required for co_rejected/co_approved)"},
                },
                "required": ["project_id", "scenario"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send a margin alert email for a project. Composes and stores the email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body (markdown)"},
                },
                "required": ["project_id", "to", "subject", "body"],
            },
        },
    },
]

TOOL_DISPATCH = {
    "get_field_notes": get_field_notes,
    "get_labor_detail": get_labor_detail,
    "get_co_detail": get_co_detail,
    "get_rfi_detail": get_rfi_detail,
    "what_if_margin": what_if_margin,
    "send_email": send_email,
}


def _load_dossier_context(project_id: str) -> str:
    """Load the pre-computed dossier JSON as context for the chat."""
    db = get_db()
    row = db.execute(
        "SELECT dossier_json FROM dossiers WHERE project_id = ?",
        [project_id],
    ).fetchone()
    if not row:
        return f"No dossier found for project {project_id}."
    dossier = json.loads(row["dossier_json"])
    # Trim evidence to keep context lean
    for t in dossier.get("triggers", []):
        t.pop("evidence", None)
        if "reasoning" in t:
            t["reasoning"] = {
                "root_cause": t["reasoning"].get("root_cause", ""),
                "confidence": t["reasoning"].get("confidence", ""),
            }
    return json.dumps(dossier, indent=2)


def _build_system_prompt(project_id: str | None) -> str:
    """Build system prompt with optional project context."""
    base = (
        "You are the HVAC Margin Rescue Agent, an expert construction financial analyst. "
        "You help project managers identify and recover margin erosion on commercial HVAC projects.\n\n"
        "Guidelines:\n"
        "- Be direct, concise, and data-driven\n"
        "- Reference specific numbers, dates, and SOV lines\n"
        "- When discussing costs, always use dollar amounts\n"
        "- Suggest concrete recovery actions with estimated dollar impact\n"
        "- Use the available tools to look up live project data when needed\n"
    )

    if project_id and project_id != "PORTFOLIO":
        context = _load_dossier_context(project_id)
        base += f"\nCurrent project dossier (pre-analyzed):\n{context}\n"

    if project_id == "PORTFOLIO" or not project_id:
        db = get_db()
        row = db.execute(
            "SELECT dossier_json FROM dossiers WHERE project_id = 'PORTFOLIO'"
        ).fetchone()
        if row:
            base += f"\nPortfolio summary:\n{row['dossier_json']}\n"

    return base


@router.post("/api/chat")
async def chat(request: Request):
    """Streaming chat endpoint using OpenAI. Expects JSON: {project_id, messages}."""
    body = await request.json()
    project_id = body.get("project_id")
    messages = body.get("messages", [])

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY not set", "reply": _fallback_reply(messages)}

    client = OpenAI(api_key=api_key)
    system_prompt = _build_system_prompt(project_id)

    # Prepend system message
    oai_messages = [{"role": "system", "content": system_prompt}] + messages

    async def event_stream():
        nonlocal oai_messages
        max_iterations = 5

        for _ in range(max_iterations):
            response = client.chat.completions.create(
                model=MODEL,
                messages=oai_messages,
                tools=TOOLS,
                max_tokens=2048,
            )

            choice = response.choices[0]
            msg = choice.message

            # If no tool calls, return the text
            if not msg.tool_calls:
                if msg.content:
                    yield f"data: {json.dumps({'type': 'text', 'content': msg.content})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # Process tool calls
            oai_messages.append(msg.model_dump())

            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                yield f"data: {json.dumps({'type': 'tool_call', 'name': fn_name, 'input': fn_args})}\n\n"

                fn = TOOL_DISPATCH.get(fn_name)
                if fn:
                    try:
                        result = fn(**fn_args)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}

                result_str = json.dumps(result)
                if len(result_str) > 8000:
                    result_str = result_str[:8000] + '..."}'

                oai_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str,
                })

            # If there was text content alongside tool calls, stream it
            if msg.content:
                yield f"data: {json.dumps({'type': 'text', 'content': msg.content})}\n\n"

        yield f"data: {json.dumps({'type': 'text', 'content': 'Reached maximum tool call iterations.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _fallback_reply(messages: list) -> str:
    last_msg = messages[-1]["content"] if messages else ""
    return (
        f"I received your question: \"{last_msg[:100]}...\"\n\n"
        "However, OPENAI_API_KEY is not configured. "
        "Set it in your environment to enable AI chat."
    )
