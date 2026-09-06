from __future__ import annotations

import pytest

from src.output.formatter import format_digest
from src.output.html import format_html
from src.scoring.impact import score_events
from tests.factories import SCENARIOS, make_event, BASE_DATE

_REPORT_DATE = BASE_DATE


# -- Header and structure ------------------------------------------------------

def test_header_contains_report_date():
    assert BASE_DATE.isoformat() in format_digest([], report_date=_REPORT_DATE)


def test_arrival_window_in_header():
    digest = format_digest([], report_date=_REPORT_DATE)
    assert "10:30" in digest
    assert "11:30" in digest


def test_no_events_shows_message():
    assert "No events" in format_digest([], report_date=_REPORT_DATE)


# -- Day labels ----------------------------------------------------------------

@pytest.mark.parametrize("day_offset,expected_label", [
    (0, "TODAY"),
    (1, "TOMORROW"),
    (2, "IN 2 DAYS"),
])
def test_day_labels(day_offset, expected_label):
    event = make_event("Test", 12, day_offset=day_offset, is_home_game=True)
    scored = score_events([event])
    digest = format_digest(scored, report_date=_REPORT_DATE)
    assert expected_label in digest


# -- Impact display ------------------------------------------------------------

@pytest.mark.parametrize("hour,is_home_game,expected_tag", [
    (12, True,  "HIGH"),    # noon game -> HIGH
    (19, True,  "MEDIUM"),  # evening game -> MEDIUM
    (18, False, "HIGH"),    # 6 PM concert -> HIGH
    (21, False, "MEDIUM"),  # late show -> MEDIUM
])
def test_impact_tag_in_plain_text(hour, is_home_game, expected_tag):
    event = make_event("Test Event", hour, is_home_game=is_home_game)
    scored = score_events([event])
    digest = format_digest(scored, report_date=_REPORT_DATE)
    assert expected_tag in digest


@pytest.mark.parametrize("hour,is_home_game,expected_badge", [
    (12, True,  "badge-HIGH"),
    (19, True,  "badge-MEDIUM"),
    (18, False, "badge-HIGH"),
    (21, False, "badge-MEDIUM"),
])
def test_impact_badge_in_html(hour, is_home_game, expected_badge):
    event = make_event("Test Event", hour, is_home_game=is_home_game)
    scored = score_events([event])
    html = format_html(scored, report_date=_REPORT_DATE)
    assert expected_badge in html


# -- Recommendation text -------------------------------------------------------

@pytest.mark.parametrize("scenario_name,expected_fragment", [
    ("low",                 "Normal parking expected"),
    ("medium-evening-game", "Arriving around"),
    ("high-noon-game",      "Ramp C"),
    ("high-concert",        "Ramp C"),
    ("maximal",             "Ramp C"),
])
def test_recommendation_by_scenario(scenario_name, expected_fragment):
    _, events = SCENARIOS[scenario_name]
    scored = score_events(events)
    digest = format_digest(scored, report_date=_REPORT_DATE)
    assert "Recommendation" in digest
    assert expected_fragment in digest


# -- Full scenario smoke tests (plain text + HTML) -----------------------------

@pytest.mark.parametrize("scenario_name", list(SCENARIOS))
def test_scenario_plain_text_is_valid(scenario_name):
    _, events = SCENARIOS[scenario_name]
    scored = score_events(events)
    digest = format_digest(scored, report_date=_REPORT_DATE)
    assert "Downtown Parking Alert" in digest
    assert "Recommendation" in digest


@pytest.mark.parametrize("scenario_name", list(SCENARIOS))
def test_scenario_html_is_valid(scenario_name):
    _, events = SCENARIOS[scenario_name]
    scored = score_events(events)
    html = format_html(scored, report_date=_REPORT_DATE)
    assert "<!DOCTYPE html>" in html
    assert "IMPACT" in html
    assert "Recommendation" in html
    assert "<html" in html
    assert "</html>" in html


# -- Event ordering ------------------------------------------------------------

def test_events_sorted_chronologically():
    events = [
        make_event("Late Event",  19, day_offset=0),
        make_event("Early Game",  12, day_offset=0, is_home_game=True),
    ]
    scored = score_events(events)
    digest = format_digest(scored, report_date=_REPORT_DATE)
    assert digest.index("Early Game") < digest.index("Late Event")


def test_multi_day_events_all_appear():
    events = [
        make_event("Game",    12, day_offset=0, is_home_game=True),
        make_event("Concert", 19, day_offset=1),
    ]
    scored = score_events(events)
    digest = format_digest(scored, report_date=_REPORT_DATE)
    assert "TODAY" in digest
    assert "TOMORROW" in digest
