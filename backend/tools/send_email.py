"""Tool: compose a margin alert email (stores locally, does not send)."""

import json
import os
from datetime import datetime

from backend.db.connection import get_db


def send_email(
    project_id: str,
    to: str,
    subject: str,
    body: str,
) -> dict:
    """Compose and store a margin alert email.

    In a production system this would integrate with SMTP/SendGrid.
    For the hackathon we store emails in a local JSON file and
    return confirmation.

    Parameters
    ----------
    project_id : str
        The project this email relates to.
    to : str
        Recipient email address.
    subject : str
        Email subject line.
    body : str
        Email body text (markdown OK).

    Returns
    -------
    dict
        Confirmation with email_id and timestamp.
    """
    email_record = {
        "email_id": f"EMAIL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "project_id": project_id,
        "to": to,
        "subject": subject,
        "body": body,
        "timestamp": datetime.now().isoformat(),
        "status": "queued",
    }

    # Store in a local JSON file
    email_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    email_file = os.path.join(email_dir, "sent_emails.json")

    existing = []
    if os.path.exists(email_file):
        with open(email_file) as f:
            existing = json.load(f)

    existing.append(email_record)

    with open(email_file, "w") as f:
        json.dump(existing, f, indent=2)

    return {
        "email_id": email_record["email_id"],
        "status": "queued",
        "to": to,
        "subject": subject,
        "timestamp": email_record["timestamp"],
        "message": "Email queued successfully. In production this would be sent via SMTP.",
    }
