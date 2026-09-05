from __future__ import annotations

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests

from src.config import TZ
from src.models import Event

log = logging.getLogger(__name__)

_TIMEOUT = 15

try:
    from icalendar import Calendar as _Calendar

    _ICAL_AVAILABLE = True
except ImportError:
    _ICAL_AVAILABLE = False


def fetch_events(feed_url: str, start: date, end: date) -> list[Event]:
    """Fetch events from an iCal feed URL within [start, end] (inclusive)."""
    if not _ICAL_AVAILABLE:
        log.warning("icalendar package not installed; skipping iCal source")
        return []

    tz = ZoneInfo(TZ)

    try:
        resp = requests.get(feed_url, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("Failed to fetch iCal feed %s: %s", feed_url, exc)
        return []

    try:
        cal = _Calendar.from_ical(resp.content)
    except Exception as exc:
        log.error("Failed to parse iCal feed %s: %s", feed_url, exc)
        return []

    events: list[Event] = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        dtstart = component.get("DTSTART")
        if dtstart is None:
            continue

        dt = dtstart.dt
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            start_local = dt.astimezone(tz)
        else:
            # All-day event (date only) — treat as midnight local time
            start_local = datetime(dt.year, dt.month, dt.day, 0, 0, tzinfo=tz)

        if not (start <= start_local.date() <= end):
            continue

        summary = str(component.get("SUMMARY", "Unknown Event"))
        location = str(component.get("LOCATION", "Target Field"))

        events.append(
            Event(
                name=summary,
                start_dt=start_local,
                venue=location,
                source="ical",
                is_home_game=False,
            )
        )
        log.debug("iCal: '%s' at %s", summary, start_local.strftime("%Y-%m-%d %-I:%M %p"))

    log.info("iCal: found %d event(s) in window from %s", len(events), feed_url)
    return events
