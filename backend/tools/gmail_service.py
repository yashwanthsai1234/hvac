"""Gmail API service for sending margin alert emails.

Adapted from Fortis project. Uses OAuth2 credentials already configured
at project root (credentials.json + token.json).
"""

import base64
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    logging.warning(
        "Google API libs not installed. Run: "
        "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    )
    Credentials = None
    Request = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
]

# Sender config
FROM_EMAIL = "yashwanthsai.v@gmail.com"
FROM_NAME = "HVAC Margin Rescue Agent"

# Project root for credentials
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class GmailService:
    """Lightweight Gmail sender for margin alert emails."""

    def __init__(self):
        self.service = None

    def authenticate(self):
        """Authenticate via OAuth2 using existing credentials."""
        if not Credentials:
            raise ImportError("Google API libraries not installed")

        token_path = PROJECT_ROOT / "token.json"
        creds_path = PROJECT_ROOT / "credentials.json"

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as f:
                f.write(creds.to_json())

        self.service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail API authenticated")
        return self.service

    def get_service(self):
        if not self.service:
            self.authenticate()
        return self.service

    def send_email(self, to: str, subject: str, html_body: str, text_body: str) -> dict:
        """Send an email via Gmail API.

        Args:
            to: recipient email address
            subject: email subject
            html_body: HTML content
            text_body: plain text fallback

        Returns:
            dict with message_id, thread_id, status
        """
        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["Subject"] = subject

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        try:
            service = self.get_service()
            sent = service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()

            logger.info(f"Email sent: {sent['id']} to {to}")
            return {
                "message_id": sent["id"],
                "thread_id": sent.get("threadId"),
                "status": "sent",
            }
        except Exception as e:
            logger.error(f"Gmail send failed: {e}")
            raise


# Singleton
gmail_service = GmailService()
