from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.config import ARRIVAL_WINDOW_END, ARRIVAL_WINDOW_START, TZ
from src.models import ScoredEvent
from src.scoring.impact import overall_impact

_RECOMMENDATIONS: dict[str, str] = {
    "HIGH": (
        "Expect elevated rates and limited availability near Ramp C. "
        "Consider arriving before {arrival_start}, using an alternate ramp (A, B, or Twins Garage), "
        "a North Loop surface lot, or switching to transit/rideshare."
    ),
    "MEDIUM": (
        "Parking near Target Field may be busier than usual. "
        "Arriving around {arrival_start} should still be manageable; "
        "check Ramp C rates before leaving."
    ),
    "LOW": "No known Target Field events. Normal parking expected near Ramp C.",
}


def format_digest(
    scored_events: list[ScoredEvent],
    report_date: date | None = None,
) -> str:
    """Return a plain-text parking digest string."""
    tz = ZoneInfo(TZ)
    if report_date is None:
        report_date = datetime.now(tz).date()

    lines: list[str] = [
        "Downtown Parking Alert (Target Field area)",
        f"Date: {report_date.strftime('%Y-%m-%d')}",
        f"Arrival window: {ARRIVAL_WINDOW_START}–{ARRIVAL_WINDOW_END} CT",
        "",
    ]

    if not scored_events:
        lines.append("No events found in the lookahead window.")
        lines.append("")
    else:
        # Group by date, sorted chronologically
        by_date: dict[date, list[ScoredEvent]] = {}
        for se in sorted(scored_events, key=lambda x: x.event.start_dt):
            d = se.event.start_dt.date()
            by_date.setdefault(d, []).append(se)

        for d, day_events in sorted(by_date.items()):
            label = _date_label(d, report_date)
            lines.append(f"--- {label} ({d.strftime('%a %b %-d')}) ---")
            for se in day_events:
                time_str = se.event.start_dt.strftime("%-I:%M %p")
                lines.append(f"{se.impact}: {se.event.name} at {time_str}")
            lines.append("")

    impact = overall_impact(scored_events)
    rec = _RECOMMENDATIONS[impact].format(arrival_start=ARRIVAL_WINDOW_START)
    lines.append(f"Recommendation ({impact}): {rec}")

    return "\n".join(lines)


def _date_label(d: date, today: date) -> str:
    delta = (d - today).days
    if delta == 0:
        return "TODAY"
    if delta == 1:
        return "TOMORROW"
    return f"IN {delta} DAYS"
