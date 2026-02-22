"""Email route — generate and store margin alert emails."""

import json
import os

from fastapi import APIRouter
from pydantic import BaseModel

from backend.tools.send_email import send_email
from backend.db.connection import get_db

router = APIRouter()


class EmailRequest(BaseModel):
    project_id: str
    to: str
    subject: str | None = None
    body: str | None = None


@router.post("/api/email/send")
async def send_alert_email(req: EmailRequest):
    """Send (store) a margin alert email. Auto-generates subject/body if omitted."""
    subject = req.subject
    body = req.body

    # Auto-generate from dossier if not provided
    if not subject or not body:
        db = get_db()
        row = db.execute(
            "SELECT dossier_json FROM dossiers WHERE project_id = ?",
            [req.project_id],
        ).fetchone()

        if row:
            dossier = json.loads(row["dossier_json"])
            name = dossier.get("name", req.project_id)
            status = dossier.get("status", "UNKNOWN")
            health = dossier.get("health_score", "N/A")
            trigger_count = dossier.get("trigger_summary", {}).get("total", 0)
            high_count = dossier.get("trigger_summary", {}).get("high", 0)

            financials = dossier.get("financials", {})
            erosion = financials.get("margin_erosion_pct", 0)
            realized = financials.get("realized_margin_pct", 0)
            bid = financials.get("bid_margin_pct", 0)

            if not subject:
                subject = f"[{status}] Margin Alert: {name} — Health {health}/100"

            if not body:
                body = (
                    f"## Margin Alert: {name}\n\n"
                    f"**Status:** {status} | **Health Score:** {health}/100\n\n"
                    f"### Financial Summary\n"
                    f"- Bid Margin: {bid:.1f}%\n"
                    f"- Realized Margin: {realized:.1f}%\n"
                    f"- Margin Erosion: {erosion:.1f}%\n\n"
                    f"### Issues Detected\n"
                    f"- Total triggers: {trigger_count}\n"
                    f"- High severity: {high_count}\n\n"
                )

                # Add top triggers
                triggers = dossier.get("triggers", [])
                high_triggers = [t for t in triggers if t.get("severity") == "HIGH"][:3]
                if high_triggers:
                    body += "### Top Issues\n"
                    for t in high_triggers:
                        body += f"- **{t.get('headline', 'N/A')}**\n"
                        reasoning = t.get("reasoning", {})
                        if reasoning.get("root_cause"):
                            body += f"  {reasoning['root_cause'][:150]}...\n"

                body += (
                    f"\n---\n"
                    f"View full dossier in the HVAC Margin Rescue dashboard.\n"
                )
        else:
            if not subject:
                subject = f"Margin Alert: {req.project_id}"
            if not body:
                body = f"Alert generated for project {req.project_id}. No dossier data available."

    result = send_email(
        project_id=req.project_id,
        to=req.to,
        subject=subject,
        body=body,
    )
    return result


@router.get("/api/emails")
async def list_emails():
    """List all stored emails."""
    email_file = os.path.join(
        os.path.dirname(__file__), "..", "data", "sent_emails.json"
    )
    if not os.path.exists(email_file):
        return []
    with open(email_file) as f:
        return json.load(f)
