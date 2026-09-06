from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.sources import mlb, ticketmaster

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_response(fixture_name: str) -> MagicMock:
    """Return a mock requests.Response backed by a fixture JSON file."""
    data = json.loads((FIXTURES / fixture_name).read_text())
    mock = MagicMock()
    mock.json.return_value = data
    mock.raise_for_status.return_value = None
    return mock


# ── MLB source ─────────────────────────────────────────────────────────────────

class TestMLBSource:
    _START = date(2026, 9, 6)
    _END = date(2026, 9, 8)

    def test_returns_only_home_games(self):
        with patch("requests.get", return_value=_mock_response("mlb_home_games.json")):
            events = mlb.fetch_home_games(self._START, self._END)
        assert all(e.is_home_game for e in events)

    def test_away_game_excluded(self):
        """Fixture contains one away game at Minute Maid Park — must be filtered out."""
        with patch("requests.get", return_value=_mock_response("mlb_home_games.json")):
            events = mlb.fetch_home_games(self._START, self._END)
        venues = [e.venue for e in events]
        assert "Minute Maid Park" not in venues

    def test_final_game_excluded(self):
        """Fixture contains one game with detailedState=Final — must be filtered out."""
        with patch("requests.get", return_value=_mock_response("mlb_home_games.json")):
            events = mlb.fetch_home_games(self._START, self._END)
        # Fixture has 3 home entries: Sep 6 (Scheduled), Sep 7 (Scheduled), Sep 8 (Final)
        assert len(events) == 2

    def test_game_times_converted_to_local(self):
        """gameDate is UTC — parser must convert to America/Chicago."""
        with patch("requests.get", return_value=_mock_response("mlb_home_games.json")):
            events = mlb.fetch_home_games(self._START, self._END)
        # Sep 6 game: 17:10 UTC = 12:10 PM CDT
        sep6_game = next(e for e in events if e.start_dt.date() == date(2026, 9, 6))
        assert sep6_game.start_dt.hour == 12
        assert sep6_game.start_dt.minute == 10

    def test_event_names_include_opponent(self):
        with patch("requests.get", return_value=_mock_response("mlb_home_games.json")):
            events = mlb.fetch_home_games(self._START, self._END)
        assert all("Twins vs" in e.name for e in events)

    def test_source_field_is_mlb(self):
        with patch("requests.get", return_value=_mock_response("mlb_home_games.json")):
            events = mlb.fetch_home_games(self._START, self._END)
        assert all(e.source == "mlb" for e in events)

    def test_empty_response_returns_empty_list(self):
        with patch("requests.get", return_value=_mock_response("mlb_no_games.json")):
            events = mlb.fetch_home_games(self._START, self._END)
        assert events == []

    def test_request_error_returns_empty_list(self):
        import requests as req
        with patch("requests.get", side_effect=req.RequestException("timeout")):
            events = mlb.fetch_home_games(self._START, self._END)
        assert events == []


# ── Ticketmaster source ────────────────────────────────────────────────────────

class TestTicketmasterSource:
    _START = date(2026, 9, 6)
    _END = date(2026, 9, 8)

    @pytest.fixture(autouse=True)
    def _set_api_key(self, monkeypatch):
        monkeypatch.setenv("TICKETMASTER_API_KEY", "test-key")
        # Reload config so the module picks up the patched env var
        import importlib
        import src.config as cfg
        importlib.reload(cfg)
        import src.sources.ticketmaster as tm_mod
        importlib.reload(tm_mod)

    def test_returns_correct_count(self):
        with patch("requests.get", return_value=_mock_response("ticketmaster_events.json")):
            from src.sources import ticketmaster as tm
            events = tm.fetch_events(self._START, self._END)
        assert len(events) == 3

    def test_event_names_parsed(self):
        with patch("requests.get", return_value=_mock_response("ticketmaster_events.json")):
            from src.sources import ticketmaster as tm
            events = tm.fetch_events(self._START, self._END)
        names = [e.name for e in events]
        assert "Taylor Swift: Eras Tour" in names
        assert "Post Malone World Tour" in names

    def test_local_times_parsed(self):
        with patch("requests.get", return_value=_mock_response("ticketmaster_events.json")):
            from src.sources import ticketmaster as tm
            events = tm.fetch_events(self._START, self._END)
        taylor = next(e for e in events if "Taylor Swift" in e.name)
        assert taylor.start_dt.hour == 19
        assert taylor.start_dt.minute == 30

    def test_missing_local_time_defaults_to_midnight(self):
        """Fixture has 'All-Day Festival' with no localTime field."""
        with patch("requests.get", return_value=_mock_response("ticketmaster_events.json")):
            from src.sources import ticketmaster as tm
            events = tm.fetch_events(self._START, self._END)
        festival = next(e for e in events if "Festival" in e.name)
        assert festival.start_dt.hour == 0
        assert festival.start_dt.minute == 0

    def test_source_field_is_ticketmaster(self):
        with patch("requests.get", return_value=_mock_response("ticketmaster_events.json")):
            from src.sources import ticketmaster as tm
            events = tm.fetch_events(self._START, self._END)
        assert all(e.source == "ticketmaster" for e in events)

    def test_empty_response_returns_empty_list(self):
        with patch("requests.get", return_value=_mock_response("ticketmaster_empty.json")):
            from src.sources import ticketmaster as tm
            events = tm.fetch_events(self._START, self._END)
        assert events == []

    def test_missing_api_key_returns_empty_list(self, monkeypatch):
        monkeypatch.delenv("TICKETMASTER_API_KEY", raising=False)
        import importlib
        import src.config as cfg
        importlib.reload(cfg)
        import src.sources.ticketmaster as tm_mod
        importlib.reload(tm_mod)
        from src.sources import ticketmaster as tm
        events = tm.fetch_events(self._START, self._END)
        assert events == []

    def test_request_error_returns_empty_list(self, monkeypatch):
        import requests as req
        with patch("requests.get", side_effect=req.RequestException("timeout")):
            from src.sources import ticketmaster as tm
            events = tm.fetch_events(self._START, self._END)
        assert events == []
