from __future__ import annotations

import pytest

from src.scoring.impact import overall_impact, score_events
from tests.factories import BASE_DATE, make_event, SCENARIOS


# ── Single-event scoring ───────────────────────────────────────────────────────
# Columns: hour, minute, is_home_game, source, expected_impact

@pytest.mark.parametrize("hour,minute,is_home_game,source,expected", [
    # Home games — HIGH window: 11:00–14:00
    (11,  0, True,  "mlb",          "HIGH"),   # boundary: window open
    (12, 10, True,  "mlb",          "HIGH"),   # noon first pitch
    (13, 35, True,  "mlb",          "HIGH"),   # mid-window
    (14,  0, True,  "mlb",          "HIGH"),   # boundary: window close
    (10, 59, True,  "mlb",          "MEDIUM"), # one minute before window
    (14,  1, True,  "mlb",          "MEDIUM"), # one minute after window
    ( 7,  5, True,  "mlb",          "MEDIUM"), # early morning game
    (19, 10, True,  "mlb",          "MEDIUM"), # evening game
    # Non-MLB events — HIGH window: 16:00–20:00 (setup + early arrivals)
    (16,  0, False, "ticketmaster", "HIGH"),   # boundary: window open
    (18, 30, False, "ticketmaster", "HIGH"),   # mid-window
    (19, 30, False, "ticketmaster", "HIGH"),   # typical concert time
    (20,  0, False, "ticketmaster", "HIGH"),   # boundary: window close
    (15, 59, False, "ticketmaster", "MEDIUM"), # one minute before window
    (20,  1, False, "ticketmaster", "MEDIUM"), # one minute after window
    (12,  0, False, "ticketmaster", "MEDIUM"), # midday event
    (21,  0, False, "ical",         "MEDIUM"), # late-night, iCal source
])
def test_single_event_scoring(hour, minute, is_home_game, source, expected):
    event = make_event("Test Event", hour, minute, is_home_game=is_home_game, source=source)
    scored = score_events([event])
    assert len(scored) == 1
    assert scored[0].impact == expected, (
        f"Expected {expected} for {'home game' if is_home_game else 'event'} at {hour:02d}:{minute:02d}"
    )


# ── Multi-event same-day upgrade ───────────────────────────────────────────────

@pytest.mark.parametrize("hour_a,home_a,hour_b,home_b", [
    (19, True,  12, False),  # evening game + midday event → both HIGH
    (21, False, 10, False),  # two MEDIUM non-MLB events same day → both HIGH
    (19, True,  21, True),   # two evening games (doubleheader) → both HIGH
])
def test_two_events_same_day_both_upgraded(hour_a, home_a, hour_b, home_b):
    events = [
        make_event("Event A", hour_a, is_home_game=home_a, day_offset=0),
        make_event("Event B", hour_b, is_home_game=home_b, day_offset=0),
    ]
    scored = score_events(events)
    assert all(se.impact == "HIGH" for se in scored), (
        f"Expected all HIGH, got {[se.impact for se in scored]}"
    )


def test_high_plus_medium_same_day_medium_upgraded():
    """A HIGH event on the same day should pull any MEDIUM up to HIGH."""
    events = [
        make_event("Noon game", 12, is_home_game=True),   # HIGH on its own
        make_event("Late show", 21, is_home_game=False),  # MEDIUM on its own
    ]
    scored = score_events(events)
    assert all(se.impact == "HIGH" for se in scored)


def test_events_on_different_days_scored_independently():
    """MEDIUM events on separate days must not influence each other."""
    events = [
        make_event("Evening game", 19, is_home_game=True,  day_offset=0),
        make_event("Late concert", 21, is_home_game=False, day_offset=1),
    ]
    scored = score_events(events)
    assert all(se.impact == "MEDIUM" for se in scored)


def test_empty_input_returns_empty_list():
    assert score_events([]) == []


# ── overall_impact across named scenarios ─────────────────────────────────────

@pytest.mark.parametrize("scenario_name,expected_overall", [
    ("low",                 "LOW"),
    ("medium-evening-game", "MEDIUM"),
    ("medium-late-concert", "MEDIUM"),
    ("high-noon-game",      "HIGH"),
    ("high-morning-game",   "HIGH"),
    ("high-concert",        "HIGH"),
    ("high-double-event",   "HIGH"),
    ("mixed",               "HIGH"),
    ("maximal",             "HIGH"),
    ("all-medium-upgraded", "HIGH"),
])
def test_overall_impact_by_scenario(scenario_name, expected_overall):
    _, events = SCENARIOS[scenario_name]
    scored = score_events(events)
    assert overall_impact(scored) == expected_overall


def test_overall_impact_no_events_is_low():
    assert overall_impact([]) == "LOW"
