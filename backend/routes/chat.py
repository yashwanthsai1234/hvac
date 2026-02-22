"""Chat endpoint — streaming SSE chat with tool-calling via Claude Haiku."""

import json
import os

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.db.connection import get_db
from backend.tools.field_notes import get_field_notes
from backend.tools.labor_detail import get_labor_detail
from backend.tools.co_detail import get_co_detail
from backend.tools.rfi_detail import get_rfi_detail
from backend.tools.what_if_margin import what_if_margin
from backend.tools.send_email import send_email

router = APIRouter()

# Tool definitions for Claude
TOOLS = [
    {
        "name": "get_field_notes",
        "description": "Search field notes for a project. Can filter by date range and keyword.",
        "input_schema": {
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
    {
        "name": "get_labor_detail",
        "description": "Get labor hours and costs for a project, broken down by SOV line and role.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID"},
                "sov_line_id": {"type": "string", "description": "Optional SOV line ID to filter"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "get_co_detail",
        "description": "Get change order details for a project, optionally filtered by CO number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID"},
                "co_number": {"type": "string", "description": "Optional CO number to filter"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "get_rfi_detail",
        "description": "Get RFI details for a project, optionally filtered by RFI number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID"},
                "rfi_number": {"type": "string", "description": "Optional RFI number to filter"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "what_if_margin",
        "description": "Run a what-if margin scenario: co_rejected, co_approved, or labor_recovery.",
        "input_schema": {
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
    {
        "name": "send_email",
        "description": "Send a margin alert email for a project. Composes and stores the email.",
        "input_schema": {
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
    # Trim evidence and reasoning to keep context lean
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

    # Load portfolio context for portfolio-level questions
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
    """Streaming chat endpoint. Expects JSON body: {project_id, messages}."""
    body = await request.json()
    project_id = body.get("project_id")
    messages = body.get("messages", [])

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set", "reply": _fallback_reply(messages)}

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = _build_system_prompt(project_id)

    async def event_stream():
        nonlocal messages
        # Agentic loop: keep going while Claude wants to use tools
        max_iterations = 5
        for _ in range(max_iterations):
            response = client.messages.create(
                model="claude-haiku-4-20250414",
                max_tokens=2048,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )

            # Check if we need to handle tool use
            has_tool_use = any(b.type == "tool_use" for b in response.content)

            if not has_tool_use:
                # Pure text response — stream it out
                for block in response.content:
                    if block.type == "text":
                        yield f"data: {json.dumps({'type': 'text', 'content': block.text})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # Process tool calls
            assistant_content = []
            tool_results = []

            for block in response.content:
                if block.type == "text":
                    yield f"data: {json.dumps({'type': 'text', 'content': block.text})}\n\n"
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_name, 'input': tool_input})}\n\n"

                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": tool_name,
                        "input": tool_input,
                    })

                    # Execute tool
                    fn = TOOL_DISPATCH.get(tool_name)
                    if fn:
                        try:
                            result = fn(**tool_input)
                        except Exception as e:
                            result = {"error": str(e)}
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}

                    # Truncate large results
                    result_str = json.dumps(result)
                    if len(result_str) > 8000:
                        result_str = result_str[:8000] + '..."}'

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            # Add assistant message + tool results to conversation
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        # Safety: if we hit max iterations
        yield f"data: {json.dumps({'type': 'text', 'content': 'I reached the maximum number of tool calls. Please refine your question.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _fallback_reply(messages: list) -> str:
    """Generate a simple fallback reply when no API key is available."""
    last_msg = messages[-1]["content"] if messages else ""
    return (
        f"I received your question about: \"{last_msg[:100]}...\"\n\n"
        "However, the ANTHROPIC_API_KEY is not configured. "
        "Please set it in your environment to enable AI-powered chat.\n\n"
        "In the meantime, you can review the pre-computed dossier insights "
        "on the project detail page."
    )
