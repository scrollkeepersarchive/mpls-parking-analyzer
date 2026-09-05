from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.models import Event
from src.scoring.impact import overall_impact, score_events

TZ = ZoneInfo("America/Chicago")


def _event(name: str, hour: int, minute: int = 0, is_home_game: bool = False, day: int = 3) -> Event:
    dt = datetime(2026, 9, day, hour, minute, tzinfo=TZ)
    source = "mlb" if is_home_game else "ticketmaster"
    return Event(name=name, start_dt=dt, venue="Target Field", source=source, is_home_game=is_home_game)


class TestSingleEventScoring:
    def test_home_game_at_noon_is_high(self):
        scored = score_events([_event("Twins vs White Sox", 12, 10, is_home_game=True)])
        assert scored[0].impact == "HIGH"

    def test_home_game_at_11am_is_high(self):
        scored = score_events([_event("Twins vs Sox", 11, 0, is_home_game=True)])
        assert scored[0].impact == "HIGH"

    def test_home_game_at_2pm_boundary_is_high(self):
        scored = score_events([_event("Twins vs Sox", 14, 0, is_home_game=True)])
        assert scored[0].impact == "HIGH"

    def test_home_game_at_7pm_is_medium(self):
        scored = score_events([_event("Twins vs Sox", 19, 0, is_home_game=True)])
        assert scored[0].impact == "MEDIUM"

    def test_home_game_at_10am_is_medium(self):
        scored = score_events([_event("Twins vs Sox", 10, 0, is_home_game=True)])
        assert scored[0].impact == "MEDIUM"

    def test_concert_at_6pm_is_high(self):
        scored = score_events([_event("Concert", 18, 0)])
        assert scored[0].impact == "HIGH"

    def test_concert_at_4pm_boundary_is_high(self):
        scored = score_events([_event("Concert", 16, 0)])
        assert scored[0].impact == "HIGH"

    def test_concert_at_8pm_boundary_is_high(self):
        scored = score_events([_event("Concert", 20, 0)])
        assert scored[0].impact == "HIGH"

    def test_event_at_noon_is_medium(self):
        scored = score_events([_event("Small Event", 12, 0)])
        assert scored[0].impact == "MEDIUM"

    def test_event_at_9pm_is_medium(self):
        scored = score_events([_event("Late Show", 21, 0)])
        assert scored[0].impact == "MEDIUM"


class TestMultipleEventScoring:
    def test_two_medium_events_same_day_both_upgraded_to_high(self):
        events = [
            _event("Twins vs Sox", 19, 0, is_home_game=True),   # MEDIUM alone
            _event("Concert", 12, 0),                            # MEDIUM alone
        ]
        scored = score_events(events)
        assert all(se.impact == "HIGH" for se in scored)

    def test_high_and_medium_same_day_medium_upgraded(self):
        events = [
            _event("Twins vs Sox", 12, 0, is_home_game=True),  # HIGH
            _event("Concert", 21, 0),                           # MEDIUM alone
        ]
        scored = score_events(events)
        assert all(se.impact == "HIGH" for se in scored)

    def test_events_on_different_days_not_cross_upgraded(self):
        events = [
            _event("Twins vs Sox", 19, 0, is_home_game=True, day=3),  # MEDIUM
            _event("Concert", 12, 0, day=4),                           # MEDIUM
        ]
        scored = score_events(events)
        # Each day has only one event, so neither gets upgraded
        assert all(se.impact == "MEDIUM" for se in scored)

    def test_empty_events_returns_empty_list(self):
        assert score_events([]) == []


class TestOverallImpact:
    def test_no_events_returns_low(self):
        assert overall_impact([]) == "LOW"

    def test_high_event_returns_high(self):
        scored = score_events([_event("Twins vs Sox", 12, 10, is_home_game=True)])
        assert overall_impact(scored) == "HIGH"

    def test_medium_event_returns_medium(self):
        scored = score_events([_event("Twins vs Sox", 19, 0, is_home_game=True)])
        assert overall_impact(scored) == "MEDIUM"

    def test_mixed_impacts_returns_highest(self):
        from src.models import ScoredEvent
        events = [
            _event("A", 12, 0, is_home_game=True),
            _event("B", 19, 0, is_home_game=True),
        ]
        scored = score_events(events)
        assert overall_impact(scored) == "HIGH"
