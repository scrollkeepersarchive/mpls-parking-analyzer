# mpls-parking-analyzer

A scheduled GitHub Actions tool that runs each morning and sends a short digest of events likely to affect parking cost and availability near **Target Field / Ramp C** during a mid-morning arrival window (default: 10:30–11:30 AM CT).

Fetches Twins home games (MLB StatsAPI) and concerts/events (Ticketmaster), scores each by parking impact, and delivers results via email and/or [ntfy](https://ntfy.sh) push notification.

---

## How it works

```
GitHub Actions (daily cron, 7:30 AM CT)
└── Fetch MLB home games  →  mlb.py
└── Fetch Ticketmaster events  →  ticketmaster.py
└── Score by impact  →  scoring/impact.py
└── Format digest  →  output/formatter.py
└── Send email + ntfy push  →  notify/
```

**Impact scoring:**

| Level | Condition |
|-------|-----------|
| HIGH | Twins home game with first pitch 11 AM–2 PM |
| HIGH | Concert/event starting 4–8 PM (setup crews affect morning parking) |
| HIGH | Multiple events on the same day |
| MEDIUM | Home game at other times, or single off-window event |
| LOW | No events in the lookahead window |

**Example output:**
```
Downtown Parking Alert (Target Field area)
Date: 2026-09-03
Arrival window: 10:30–11:30 CT

--- TODAY (Thu Sep 3) ---
HIGH: Twins vs White Sox at 12:10 PM

--- TOMORROW (Fri Sep 4) ---
HIGH: Major Concert at 7:00 PM

Recommendation (HIGH): Expect elevated rates and limited availability near Ramp C.
Consider arriving before 10:30, using an alternate ramp (A, B, or Twins Garage),
a North Loop surface lot, or switching to transit/rideshare.
```

---

## Setup

### 1. Fork / clone this repo

### 2. Add GitHub Actions secrets

In your repo go to **Settings → Secrets and variables → Actions**:

| Name | Type | Description |
|------|------|-------------|
| `TICKETMASTER_API_KEY` | Secret | [Ticketmaster Discovery API](https://developer.ticketmaster.com/) key |
| `SMTP_HOST` | Secret | SMTP server hostname (e.g. `smtp.gmail.com`) |
| `SMTP_USER` | Secret | Sending email address |
| `SMTP_PASS` | Secret | App password (not your account password) |
| `NTFY_TOPIC` | Secret | ntfy topic name (optional) |
| `NOTIFY_EMAIL` | Variable | Recipient email address |
| `TARGET_FIELD_VENUE_ID` | Variable | Ticketmaster venue ID for Target Field (optional — see below) |

> **Gmail tip:** use an [App Password](https://support.google.com/accounts/answer/185833), not your account password.

> **Target Field venue ID:** find it by querying  
> `https://app.ticketmaster.com/discovery/v2/venues.json?apikey=YOUR_KEY&keyword=Target+Field&city=Minneapolis`

### 3. Enable the workflow

The workflow runs automatically at **7:30 AM CDT** (12:30 UTC). You can trigger it manually at any time from the **Actions** tab → *Daily Parking Digest* → **Run workflow**.

---

## Local development

```bash
# Copy and fill in credentials
cp .env.example .env

# Install dependencies (Python 3.12+)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Print digest without sending notifications
make dry-run

# Run tests
make test
```

---

## Configuration

All settings are controlled by environment variables. See [`.env.example`](.env.example) for the full list.

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | `America/Chicago` | Timezone for all time comparisons |
| `LOOKAHEAD_DAYS` | `2` | Days ahead to include (today + N) |
| `ARRIVAL_WINDOW_START` | `10:30` | Start of your arrival window (display only) |
| `ARRIVAL_WINDOW_END` | `11:30` | End of your arrival window (display only) |
| `DRY_RUN` | `0` | Set to `1` to print digest without sending |

---

## Project structure

```
src/
├── main.py               # Entrypoint — orchestrates fetch → score → notify
├── config.py             # Env var loading
├── models.py             # Event / ScoredEvent dataclasses
├── sources/
│   ├── mlb.py            # MLB StatsAPI (Twins home games)
│   ├── ticketmaster.py   # Ticketmaster Discovery API
│   └── ical.py           # Optional iCal feed parser
├── scoring/
│   └── impact.py         # HIGH / MEDIUM / LOW heuristics
├── output/
│   └── formatter.py      # Plain-text digest builder
└── notify/
    ├── email.py           # SMTP email
    └── ntfy.py            # ntfy.sh push notification
tests/
├── test_impact.py
└── test_formatter.py
.github/workflows/
└── daily-digest.yml       # Scheduled Actions workflow
```

---

## Roadmap

- **Phase 1 (MVP):** MLB + Ticketmaster fetch, scoring, email digest via GitHub Actions ✓
- **Phase 2:** iCal fallback, push notifications, improved scoring
- **Phase 3:** Web dashboard, ICS export, nearby venue signals (Target Center, US Bank Stadium)

