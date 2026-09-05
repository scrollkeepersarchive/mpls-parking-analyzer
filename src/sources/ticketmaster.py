from __future__ import annotations

import logging
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests

from src.config import TICKETMASTER_API_KEY, TARGET_FIELD_VENUE_ID, TZ
from src.models import Event

log = logging.getLogger(__name__)

_BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
_TIMEOUT = 15
_MAX_RETRIES = 3


def _get_with_retry(params: dict) -> dict:
    delay = 1.0
    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.get(_BASE_URL, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            log.warning(
                "Ticketmaster API attempt %d/%d failed (%s); retrying in %.0fs",
                attempt + 1,
                _MAX_RETRIES,
                exc,
                delay,
            )
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def fetch_events(start: date, end: date) -> list[Event]:
    """Return Ticketmaster events at Target Field between start and end (inclusive)."""
    if not TICKETMASTER_API_KEY:
        log.warning("TICKETMASTER_API_KEY not set; skipping Ticketmaster source")
        return []

    tz = ZoneInfo(TZ)

    # Ticketmaster expects UTC ISO-8601 with Z suffix
    params: dict = {
        "apikey": TICKETMASTER_API_KEY,
        "startDateTime": f"{start.isoformat()}T00:00:00Z",
        "endDateTime": f"{end.isoformat()}T23:59:59Z",
        "size": 50,
        "sort": "date,asc",
    }

    if TARGET_FIELD_VENUE_ID:
        params["venueId"] = TARGET_FIELD_VENUE_ID
    else:
        # Fallback: keyword + city search when venue ID is not configured
        params["keyword"] = "Target Field"
        params["city"] = "Minneapolis"
        params["stateCode"] = "MN"
        params["countryCode"] = "US"

    try:
        data = _get_with_retry(params)
    except requests.RequestException as exc:
        log.error("Failed to fetch Ticketmaster events: %s", exc)
        return []

    raw_events = data.get("_embedded", {}).get("events", [])

    events: list[Event] = []
    for raw in raw_events:
        name = raw.get("name", "Unknown Event")
        start_info = raw.get("dates", {}).get("start", {})
        local_date_str = start_info.get("localDate", "")
        local_time_str = start_info.get("localTime", "00:00:00")

        if not local_date_str:
            continue

        try:
            naive_dt = datetime.strptime(
                f"{local_date_str} {local_time_str}", "%Y-%m-%d %H:%M:%S"
            )
            start_local = naive_dt.replace(tzinfo=tz)
        except ValueError:
            log.warning("Unparseable Ticketmaster date: %s %s", local_date_str, local_time_str)
            continue

        venues = raw.get("_embedded", {}).get("venues", [])
        venue_name = venues[0].get("name", "Target Field") if venues else "Target Field"

        events.append(
            Event(
                name=name,
                start_dt=start_local,
                venue=venue_name,
                source="ticketmaster",
                is_home_game=False,
            )
        )
        log.debug(
            "Ticketmaster: '%s' at %s", name, start_local.strftime("%Y-%m-%d %-I:%M %p")
        )

    log.info("Ticketmaster: found %d event(s) in window", len(events))
    return events
