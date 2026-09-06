from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.models import Event, ScoredEvent
from src.scoring.impact import score_events

TZ = ZoneInfo("America/Chicago")

# Fixed base date used by all factories so tests are deterministic
BASE_DATE = date(2026, 9, 6)


def make_event(
    name: str,
    hour: int,
    minute: int = 0,
    day_offset: int = 0,
    is_home_game: bool = False,
    source: str | None = None,
    venue: str = "Target Field",
) -> Event:
    """Create a timezone-aware Event relative to BASE_DATE."""
    if source is None:
        source = "mlb" if is_home_game else "ticketmaster"
    d = BASE_DATE + timedelta(days=day_offset)
    dt = datetime(d.year, d.month, d.day, hour, minute, tzinfo=TZ)
    return Event(name=name, start_dt=dt, venue=venue, source=source, is_home_game=is_home_game)


def make_scored(event: Event, impact: str, reason: str = "test") -> ScoredEvent:
    return ScoredEvent(event=event, impact=impact, reason=reason)


# ── Named scenarios ────────────────────────────────────────────────────────────
# Each entry: (description, list[Event])
# Call score_events() on the event list to get ScoredEvent results.

SCENARIOS: dict[str, tuple[str, list[Event]]] = {
    "low": (
        "No events in lookahead window",
        [],
    ),
    "medium-evening-game": (
        "Single evening home game (after arrival window)",
        [make_event("Twins vs Detroit Tigers", 19, 10, is_home_game=True)],
    ),
    "medium-late-concert": (
        "Late-night event (after setup window)",
        [make_event("Comedy Night at Target Field", 21, 0)],
    ),
    "high-noon-game": (
        "Noon home game — first pitch overlaps arrival window",
        [make_event("Twins vs Chicago White Sox", 12, 10, is_home_game=True)],
    ),
    "high-morning-game": (
        "11 AM first pitch — earliest HIGH boundary",
        [make_event("Twins vs Kansas City Royals", 11, 0, is_home_game=True)],
    ),
    "high-concert": (
        "Evening concert — setup crews in area during morning",
        [make_event("Taylor Swift: Eras Tour", 19, 30)],
    ),
    "high-double-event": (
        "Evening game + concert same day — both upgraded to HIGH",
        [
            make_event("Twins vs White Sox", 19, 10, is_home_game=True),
            make_event("Post Malone World Tour", 19, 0),
        ],
    ),
    "mixed": (
        "Multi-day: HIGH today, MEDIUM tomorrow, HIGH in 2 days",
        [
            make_event("Twins vs White Sox", 12, 10, day_offset=0, is_home_game=True),
            make_event("Twins vs Detroit Tigers", 19, 10, day_offset=1, is_home_game=True),
            make_event("Taylor Swift: Eras Tour", 19, 30, day_offset=2),
        ],
    ),
    "maximal": (
        "Worst case: game + concert today, games next two days",
        [
            make_event("Twins vs White Sox", 12, 10, day_offset=0, is_home_game=True),
            make_event("Taylor Swift: Eras Tour", 19, 30, day_offset=0),
            make_event("Twins vs Boston Red Sox", 13, 10, day_offset=1, is_home_game=True),
            make_event("Monster Jam", 14, 0, day_offset=2),
        ],
    ),
    "all-medium-upgraded": (
        "Two MEDIUM-only events same day — both upgraded to HIGH",
        [
            make_event("Twins vs Tigers", 19, 10, day_offset=0, is_home_game=True),
            make_event("Corporate Event", 10, 0, day_offset=0),
        ],
    ),
}


def scored_scenario(name: str) -> tuple[str, list[ScoredEvent]]:
    """Return (description, scored_events) for a named scenario."""
    description, events = SCENARIOS[name]
    return description, score_events(events)
