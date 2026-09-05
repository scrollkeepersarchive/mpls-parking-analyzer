from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from src.config import NOTIFY_EMAIL, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER

log = logging.getLogger(__name__)


def send(subject: str, body: str) -> bool:
    """Send a plain-text email digest. Returns True on success."""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, NOTIFY_EMAIL]):
        log.warning(
            "Email not fully configured (need SMTP_HOST, SMTP_USER, SMTP_PASS, NOTIFY_EMAIL); "
            "skipping email notification"
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        log.info("Email sent to %s via %s:%s", NOTIFY_EMAIL, SMTP_HOST, SMTP_PORT)
        return True
    except smtplib.SMTPException as exc:
        log.error("Failed to send email: %s", exc)
        return False
