from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pathlib import Path

from src.config import (
    DRY_RUN,
    ENABLE_EMAIL,
    HTML_OUTPUT_PATH,
    LOOKAHEAD_DAYS,
    PUBLISH_HTML,
    TZ,
)
from src.models import Event
from src.notify import email, ntfy
from src.output import html as html_formatter
from src.output.formatter import format_digest
from src.scoring.impact import overall_impact, score_events
from src.sources import mlb, ticketmaster

_REPO_ROOT = Path(__file__).parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minneapolis Parking Analyzer")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=DRY_RUN,
        help="Print digest to stdout without sending notifications (also set DRY_RUN=1)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    tz = ZoneInfo(TZ)
    today = datetime.now(tz).date()
    end_date = today + timedelta(days=LOOKAHEAD_DAYS)

    log.info(
        "Running parking digest | window: %s – %s | dry_run=%s",
        today,
        end_date,
        args.dry_run,
    )

    # Fetch from all sources; each source handles its own errors gracefully
    all_events: list[Event] = []

    all_events.extend(mlb.fetch_home_games(today, end_date))
    all_events.extend(ticketmaster.fetch_events(today, end_date))

    log.info("Total events fetched: %d", len(all_events))

    scored = score_events(all_events)
    digest = format_digest(scored, report_date=today)
    impact = overall_impact(scored)

    # Always print to stdout (captured by GitHub Actions logs)
    print(digest)

    # Write HTML page for GitHub Pages (before notification check so it always runs)
    if PUBLISH_HTML:
        html_content = html_formatter.format_html(scored, report_date=today)
        output_path = _REPO_ROOT / HTML_OUTPUT_PATH
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")
        log.info("HTML digest written to %s", output_path)

    if args.dry_run:
        log.info("Dry-run mode: notifications suppressed")
        return

    subject = f"[{impact}] Downtown Parking Alert – {today.strftime('%a %b %-d')}"
    ntfy_priority = "high" if impact == "HIGH" else "default"

    email_sent = False
    if ENABLE_EMAIL:
        email_sent = email.send(subject, digest)
    else:
        log.info("Email disabled (ENABLE_EMAIL=0)")

    ntfy_sent = ntfy.send(subject, digest, priority=ntfy_priority)

    if not email_sent and not ntfy_sent:
        log.warning(
            "No notifications were sent — check ENABLE_EMAIL, SMTP, and/or NTFY_TOPIC configuration"
        )


if __name__ == "__main__":
    main()
