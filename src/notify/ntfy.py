from __future__ import annotations

import logging

import requests

from src.config import NTFY_BASE_URL, NTFY_TOPIC

log = logging.getLogger(__name__)

_TIMEOUT = 10


def send(title: str, body: str, priority: str = "default") -> bool:
    """Send a push notification via ntfy.sh. Returns True on success."""
    if not NTFY_TOPIC:
        log.debug("NTFY_TOPIC not configured; skipping ntfy notification")
        return False

    url = f"{NTFY_BASE_URL.rstrip('/')}/{NTFY_TOPIC}"
    headers = {
        "Title": title,
        "Priority": priority,
        "Content-Type": "text/plain",
    }

    try:
        resp = requests.post(url, data=body.encode(), headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        log.info("ntfy notification sent to topic '%s' at %s", NTFY_TOPIC, NTFY_BASE_URL)
        return True
    except requests.RequestException as exc:
        log.error("Failed to send ntfy notification: %s", exc)
        return False
