from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.models import Event, ScoredEvent
from src.output.formatter import format_digest

TZ = ZoneInfo("America/Chicago")


def _scored(name: str, hour: int, impact: str, is_home_game: bool = False, day: int = 3) -> ScoredEvent:
    dt = datetime(2026, 9, day, hour, 10, tzinfo=TZ)
    event = Event(name=name, start_dt=dt, venue="Target Field", source="mlb", is_home_game=is_home_game)
    return ScoredEvent(event=event, impact=impact, reason="test")


_REPORT_DATE = date(2026, 9, 3)


class TestFormatDigest:
    def test_header_contains_date(self):
        assert "2026-09-03" in format_digest([], report_date=_REPORT_DATE)

    def test_arrival_window_in_header(self):
        digest = format_digest([], report_date=_REPORT_DATE)
        assert "10:30" in digest
        assert "11:30" in digest

    def test_no_events_shows_message(self):
        assert "No events" in format_digest([], report_date=_REPORT_DATE)

    def test_low_impact_recommendation_for_no_events(self):
        assert "Normal parking expected" in format_digest([], report_date=_REPORT_DATE)

    def test_high_event_appears_with_label(self):
        scored = [_scored("Twins vs White Sox", 12, "HIGH", is_home_game=True)]
        digest = format_digest(scored, report_date=_REPORT_DATE)
        assert "HIGH" in digest
        assert "Twins vs White Sox" in digest

    def test_time_formatted_without_leading_zero(self):
        scored = [_scored("Twins vs White Sox", 12, "HIGH", is_home_game=True)]
        digest = format_digest(scored, report_date=_REPORT_DATE)
        assert "12:10 PM" in digest

    def test_recommendation_present(self):
        scored = [_scored("Twins vs White Sox", 12, "HIGH", is_home_game=True)]
        assert "Recommendation" in format_digest(scored, report_date=_REPORT_DATE)

    def test_high_recommendation_mentions_ramp_c(self):
        scored = [_scored("Twins vs White Sox", 12, "HIGH", is_home_game=True)]
        assert "Ramp C" in format_digest(scored, report_date=_REPORT_DATE)

    def test_today_label_for_same_day_event(self):
        scored = [_scored("Twins vs White Sox", 12, "HIGH", day=3)]
        digest = format_digest(scored, report_date=_REPORT_DATE)
        assert "TODAY" in digest

    def test_tomorrow_label_for_next_day_event(self):
        scored = [_scored("Concert", 18, "HIGH", day=4)]
        digest = format_digest(scored, report_date=_REPORT_DATE)
        assert "TOMORROW" in digest

    def test_in_n_days_label_for_later_event(self):
        scored = [_scored("Concert", 18, "HIGH", day=5)]
        digest = format_digest(scored, report_date=_REPORT_DATE)
        assert "IN 2 DAYS" in digest

    def test_events_sorted_chronologically(self):
        scored = [
            _scored("Late Event", 19, "MEDIUM", day=3),
            _scored("Early Game", 12, "HIGH", day=3),
        ]
        digest = format_digest(scored, report_date=_REPORT_DATE)
        early_pos = digest.index("Early Game")
        late_pos = digest.index("Late Event")
        assert early_pos < late_pos

    def test_multiple_days_both_appear(self):
        scored = [
            _scored("Game", 12, "HIGH", day=3),
            _scored("Concert", 19, "HIGH", day=4),
        ]
        digest = format_digest(scored, report_date=_REPORT_DATE)
        assert "TODAY" in digest
        assert "TOMORROW" in digest
