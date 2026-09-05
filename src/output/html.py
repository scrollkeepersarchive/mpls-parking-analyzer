from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.config import ARRIVAL_WINDOW_END, ARRIVAL_WINDOW_START, LOOKAHEAD_DAYS, TZ
from src.models import ScoredEvent
from src.scoring.impact import overall_impact

# ── CSS ───────────────────────────────────────────────────────────────────────
_CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f8fafc;
    color: #1e293b;
    line-height: 1.5;
    padding: 1.5rem 1rem;
  }
  header, main, footer { max-width: 600px; margin: 0 auto; }
  header { margin-bottom: 1.5rem; }
  h1 { font-size: 1.35rem; font-weight: 700; }
  .subtitle { color: #64748b; font-size: 0.875rem; margin-top: 0.2rem; }
  .overall-badge {
    display: inline-block;
    margin-top: 0.75rem;
    padding: 0.3rem 0.85rem;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.8rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .badge-HIGH   { background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5; }
  .badge-MEDIUM { background: #fffbeb; color: #d97706; border: 1px solid #fcd34d; }
  .badge-LOW    { background: #f0fdf4; color: #16a34a; border: 1px solid #86efac; }
  .card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.875rem;
  }
  .card-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin-bottom: 0.6rem;
  }
  .event-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.4rem 0;
    border-top: 1px solid #f1f5f9;
  }
  .event-row:first-of-type { border-top: none; }
  .impact-tag {
    font-size: 0.68rem;
    font-weight: 700;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    text-transform: uppercase;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .tag-HIGH   { background: #fef2f2; color: #dc2626; }
  .tag-MEDIUM { background: #fffbeb; color: #d97706; }
  .tag-LOW    { background: #f0fdf4; color: #16a34a; }
  .event-name { font-size: 0.9rem; flex: 1; }
  .event-time { font-size: 0.85rem; color: #64748b; white-space: nowrap; }
  .no-events  { text-align: center; color: #94a3b8; font-size: 0.9rem; }
  .rec-text   { font-size: 0.9rem; color: #334155; }
  footer {
    margin-top: 1rem;
    font-size: 0.78rem;
    color: #94a3b8;
    text-align: center;
  }
"""

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


def _esc(text: str) -> str:
    """Minimal HTML escaping for untrusted content (event names, venues)."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def _date_label(d: date, today: date) -> str:
    delta = (d - today).days
    if delta == 0:
        return "TODAY"
    if delta == 1:
        return "TOMORROW"
    return f"IN {delta} DAYS"


def format_html(
    scored_events: list[ScoredEvent],
    report_date: date | None = None,
) -> str:
    """Return a standalone HTML page with the parking digest."""
    tz = ZoneInfo(TZ)
    if report_date is None:
        report_date = datetime.now(tz).date()

    impact = overall_impact(scored_events)
    updated_at = datetime.now(tz).strftime("%Y-%m-%d %-I:%M %p")

    # ── events section ────────────────────────────────────────────────────────
    events_html_parts: list[str] = []

    if not scored_events:
        events_html_parts.append(
            '<div class="card"><p class="no-events">No events found in the lookahead window.</p></div>'
        )
    else:
        by_date: dict[date, list[ScoredEvent]] = {}
        for se in sorted(scored_events, key=lambda x: x.event.start_dt):
            d = se.event.start_dt.date()
            by_date.setdefault(d, []).append(se)

        for d, day_events in sorted(by_date.items()):
            label = _date_label(d, report_date)
            date_str = d.strftime("%a %b %-d")
            rows = []
            for se in day_events:
                time_str = se.event.start_dt.strftime("%-I:%M %p")
                rows.append(
                    f'<div class="event-row">'
                    f'<span class="impact-tag tag-{se.impact}">{se.impact}</span>'
                    f'<span class="event-name">{_esc(se.event.name)}</span>'
                    f'<span class="event-time">{time_str}</span>'
                    f"</div>"
                )
            events_html_parts.append(
                f'<div class="card">'
                f'<div class="card-label">{label} &mdash; {date_str}</div>'
                + "".join(rows)
                + "</div>"
            )

    # ── recommendation ────────────────────────────────────────────────────────
    rec_text = _RECOMMENDATIONS[impact].format(arrival_start=ARRIVAL_WINDOW_START)
    rec_html = (
        f'<div class="card">'
        f'<div class="card-label">Recommendation</div>'
        f'<p class="rec-text">{_esc(rec_text)}</p>'
        f"</div>"
    )

    # ── assemble ──────────────────────────────────────────────────────────────
    return "\n".join([
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "<title>Minneapolis Parking Alert</title>",
        f"<style>{_CSS}</style>",
        "</head>",
        "<body>",
        "<header>",
        "  <h1>Minneapolis Parking Alert</h1>",
        f'  <p class="subtitle">Target Field / Ramp C &mdash; Arrival {ARRIVAL_WINDOW_START}&ndash;{ARRIVAL_WINDOW_END} CT</p>',
        f'  <span class="overall-badge badge-{impact}">{impact} IMPACT</span>',
        "</header>",
        "<main>",
        "".join(events_html_parts),
        rec_html,
        "</main>",
        "<footer>",
        f"  Last updated: {updated_at} CT &bull; {LOOKAHEAD_DAYS}-day lookahead",
        "</footer>",
        "</body>",
        "</html>",
    ])
