from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    # override=False so GitHub Actions secrets take precedence over any local .env
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass  # Running without python-dotenv; env vars must be set externally


TZ = os.environ.get("TZ") or "America/Chicago"
LOOKAHEAD_DAYS = int(os.environ.get("LOOKAHEAD_DAYS") or "2")
ARRIVAL_WINDOW_START = os.environ.get("ARRIVAL_WINDOW_START") or "10:30"
ARRIVAL_WINDOW_END = os.environ.get("ARRIVAL_WINDOW_END") or "11:30"

# Optional — MLB source works without any API key
TICKETMASTER_API_KEY = os.environ.get("TICKETMASTER_API_KEY", "")
# Find Target Field's Ticketmaster venue ID at:
# https://app.ticketmaster.com/discovery/v2/venues.json?apikey=KEY&keyword=Target+Field&city=Minneapolis
TARGET_FIELD_VENUE_ID = os.environ.get("TARGET_FIELD_VENUE_ID", "")

# Optional — only needed when ENABLE_EMAIL=1
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT") or "587")
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "")

# Optional — ntfy is skipped when NTFY_TOPIC is blank
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_BASE_URL = os.environ.get("NTFY_BASE_URL") or "https://ntfy.sh"

DRY_RUN = os.environ.get("DRY_RUN", "0").strip().lower() in ("1", "true", "yes")
ENABLE_EMAIL = os.environ.get("ENABLE_EMAIL", "1").strip().lower() not in ("0", "false", "no")

# HTML page output (written to disk, then committed to GitHub Pages by the workflow)
PUBLISH_HTML = os.environ.get("PUBLISH_HTML", "0").strip().lower() in ("1", "true", "yes")
HTML_OUTPUT_PATH = os.environ.get("HTML_OUTPUT_PATH", "docs/index.html")

MLB_TEAM_ID = 142  # Minnesota Twins
