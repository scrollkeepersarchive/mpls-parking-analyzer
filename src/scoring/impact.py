from __future__ import annotations

from collections import defaultdict
from datetime import time

from src.models import Event, ScoredEvent

# First-pitch window that directly overlaps the 10:30–11:30 arrival (or causes
# pre-game congestion before it)
_HIGH_GAME_START = time(11, 0)
_HIGH_GAME_END = time(14, 0)

# Non-MLB events that start in this window bring setup crews and early arrivals
# into the area during the morning commute
_HIGH_EVENT_SETUP_START = time(16, 0)  # 4 PM
_HIGH_EVENT_SETUP_END = time(20, 0)    # 8 PM


def _score_single(event: Event) -> tuple[str, str]:
    """Return (impact, reason) for a single event."""
    t = event.start_dt.time()
    time_str = event.start_dt.strftime("%-I:%M %p")

    if event.is_home_game:
        if _HIGH_GAME_START <= t <= _HIGH_GAME_END:
            return (
                "HIGH",
                f"Home game first pitch at {time_str} — overlaps or precedes arrival window",
            )
        return "MEDIUM", f"Home game at {time_str} — same-day parking pressure"

    # Non-MLB event
    if _HIGH_EVENT_SETUP_START <= t <= _HIGH_EVENT_SETUP_END:
        return (
            "HIGH",
            f"Event at {time_str} — setup crews and early arrivals affect morning parking",
        )
    return "MEDIUM", f"Event at {time_str} — monitor for additional parking impact"


def score_events(events: list[Event]) -> list[ScoredEvent]:
    """Score each event and upgrade days with multiple events to HIGH."""
    scored = [
        ScoredEvent(event=e, impact=impact, reason=reason)
        for e in events
        for impact, reason in [_score_single(e)]
    ]

    # Multiple events on the same day → elevate any remaining MEDIUM scores to HIGH
    by_date: dict = defaultdict(list)
    for se in scored:
        by_date[se.event.start_dt.date()].append(se)

    for day_events in by_date.values():
        if len(day_events) >= 2:
            for se in day_events:
                if se.impact == "MEDIUM":
                    se.impact = "HIGH"
                    se.reason += " (multiple events same day)"

    return scored


def overall_impact(scored: list[ScoredEvent]) -> str:
    """Return the highest impact level across all scored events, or LOW if none."""
    if not scored:
        return "LOW"
    _rank = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
    return max(scored, key=lambda se: _rank.get(se.impact, 0)).impact
