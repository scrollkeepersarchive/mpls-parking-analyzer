from __future__ import annotations

import logging
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests

from src.config import MLB_TEAM_ID, TZ
from src.models import Event

log = logging.getLogger(__name__)

_BASE_URL = "https://statsapi.mlb.com/api/v1/schedule"
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
                "MLB API attempt %d/%d failed (%s); retrying in %.0fs",
                attempt + 1,
                _MAX_RETRIES,
                exc,
                delay,
            )
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def fetch_home_games(start: date, end: date) -> list[Event]:
    """Return Twins home games scheduled between start and end (inclusive)."""
    tz = ZoneInfo(TZ)
    params = {
        "sportId": 1,
        "teamId": MLB_TEAM_ID,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
    }

    try:
        data = _get_with_retry(params)
    except requests.RequestException as exc:
        log.error("Failed to fetch MLB schedule: %s", exc)
        return []

    _SKIP_STATES = {"Final", "Game Over", "Completed Early", "Cancelled", "Postponed"}

    events: list[Event] = []
    for date_entry in data.get("dates", []):
        for game in date_entry.get("games", []):
            status = game.get("status", {}).get("detailedState", "")
            if status in _SKIP_STATES:
                continue

            home_team = game.get("teams", {}).get("home", {}).get("team", {})
            if home_team.get("id") != MLB_TEAM_ID:
                continue  # away game

            game_date_str = game.get("gameDate", "")
            if not game_date_str:
                continue

            try:
                start_utc = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
                start_local = start_utc.astimezone(tz)
            except ValueError:
                log.warning("Unparseable gameDate: %s", game_date_str)
                continue

            away_name = (
                game.get("teams", {}).get("away", {}).get("team", {}).get("name", "Unknown")
            )
            venue = game.get("venue", {}).get("name", "Target Field")

            events.append(
                Event(
                    name=f"Twins vs {away_name}",
                    start_dt=start_local,
                    venue=venue,
                    source="mlb",
                    is_home_game=True,
                )
            )
            log.debug("MLB: %s at %s", events[-1].name, start_local.strftime("%Y-%m-%d %-I:%M %p"))

    log.info("MLB: found %d home game(s) in window", len(events))
    return events
