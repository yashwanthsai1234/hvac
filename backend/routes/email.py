"""Email route — send margin alert reports via Gmail API."""

import json
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader
import markdown

from backend.db.connection import get_db
from backend.tools.gmail_service import gmail_service

router = APIRouter()

TEMPLATE_DIR = Path(__file__).parent.parent / "email_templates"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


class EmailRequest(BaseModel):
    project_id: str
    to: str


def _build_alert_email(project_id: str) -> dict:
    """Build HTML and text email content from the dossier."""
    db = get_db()
    row = db.execute(
        "SELECT dossier_json FROM dossiers WHERE project_id = ?",
        [project_id],
    ).fetchone()

    if not row:
        return {
            "subject": f"Margin Alert: {project_id}",
            "html": f"<p>No dossier data for {project_id}.</p>",
            "text": f"No dossier data for {project_id}.",
        }

    d = json.loads(row["dossier_json"])
    name = d.get("name", project_id)
    status = d.get("status", "UNKNOWN")
    health = d.get("health_score", "N/A")
    fin = d.get("financials", {})

    # Status color mapping
    status_colors = {"RED": "#ef4444", "YELLOW": "#eab308", "GREEN": "#22c55e"}
    header_color = status_colors.get(status, "#6b7280")
    status_class = status.lower() if status in status_colors else "green"

    # Build markdown body
    body_md = f"""### Financial Summary

| Metric | Value |
|--------|-------|
| Contract Value | ${d.get('contract_value', 0):,.0f} |
| Bid Margin | {fin.get('bid_margin_pct', 0):.1f}% |
| Realized Margin | {fin.get('realized_margin_pct', 0):.1f}% |
| Margin Erosion | {fin.get('margin_erosion_pct', 0):.1f}% |
| Estimated Cost | ${fin.get('estimated_cost', 0):,.0f} |
| Actual Cost | ${fin.get('actual_cost', 0):,.0f} |
| Approved COs | ${fin.get('approved_cos', 0):,.0f} |
| Billing Lag | ${fin.get('billing_lag', 0):,.0f} ({fin.get('billing_lag_pct', 0):.1f}%) |

### Issues Detected ({d.get('trigger_summary', {}).get('total', 0)} total)

"""
    # Top triggers
    triggers = d.get("triggers", [])
    high_triggers = [t for t in triggers if t.get("severity") == "HIGH"][:5]

    for t in high_triggers:
        reasoning = t.get("reasoning", {})
        body_md += f"**{t.get('headline', 'N/A')}**\n\n"
        body_md += f"{reasoning.get('root_cause', 'No analysis available.')[:300]}\n\n"

        actions = reasoning.get("recovery_actions", [])
        if actions:
            body_md += "Recovery actions:\n"
            for a in actions[:3]:
                body_md += f"- {a}\n"
            body_md += "\n"

        recoverable = reasoning.get("recoverable_amount", 0)
        if recoverable > 0:
            body_md += f"*Estimated recoverable: ${recoverable:,.0f}*\n\n"

        body_md += "---\n\n"

    # Total recoverable
    total_recoverable = sum(
        t.get("reasoning", {}).get("recoverable_amount", 0) for t in triggers
    )
    if total_recoverable > 0:
        body_md += f"\n### Total Estimated Recoverable: ${total_recoverable:,.0f}\n"

    # Convert markdown to HTML
    body_html = markdown.markdown(body_md, extensions=["tables", "sane_lists"])

    # Render with template
    template = jinja_env.get_template("margin_alert.html")
    subject = f"[{status}] Margin Alert: {name} — Health {health}/100"

    html = template.render(
        subject=subject,
        project_name=name,
        status=status,
        status_class=status_class,
        health_score=health,
        header_color=header_color,
        body_html=body_html,
        generated_at=datetime.now().strftime("%b %d, %Y %I:%M %p"),
    )

    # Plain text version
    text = re.sub(r"<[^>]+>", "", body_md)

    return {"subject": subject, "html": html, "text": text}


@router.post("/api/email/send")
async def send_alert_email(req: EmailRequest):
    """Send a margin alert email via Gmail API."""
    email_content = _build_alert_email(req.project_id)

    try:
        result = gmail_service.send_email(
            to=req.to,
            subject=email_content["subject"],
            html_body=email_content["html"],
            text_body=email_content["text"],
        )
        return {
            "status": "sent",
            "message_id": result["message_id"],
            "to": req.to,
            "subject": email_content["subject"],
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "to": req.to,
            "subject": email_content["subject"],
        }
