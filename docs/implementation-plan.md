# Minneapolis Parking Analyzer

Implementation plan for an automated tool that helps predict downtown Minneapolis parking pressure (especially near Ramp C / Target Field) before driving in. Runs as a scheduled GitHub Actions workflow — no server required.

## Goal

Build a lightweight automation that runs each morning and sends a short summary of events likely to affect parking cost and availability near **Target Field / Ramp C** between roughly **10:30 AM–11:30 AM** arrival.

## Primary Use Case

- Work from home early morning
- Drive downtown mid-morning
- Avoid surprise event-day congestion and expensive parking
- Decide ahead of time whether to:
  - leave earlier/later,
  - choose alternative parking,
  - use transit/rideshare,
  - or work remote all day

## High-Level Architecture

```text
GitHub Actions (scheduled workflow)
└── Ubuntu runner (free)
    └── Python app
        ├── Fetch Twins home games (MLB StatsAPI)
        ├── Fetch concerts/special events (Ticketmaster API and/or iCal feed)
        ├── Score parking impact by date/time proximity
        ├── Generate short digest
        └── Send notification (email/push)
```

Secrets (`TICKETMASTER_API_KEY`, `SMTP_PASS`, etc.) are stored as **GitHub Actions encrypted secrets** — never in code.

## Data Sources

### 1) MLB StatsAPI (Twins home games)
- Public endpoint for MLB schedules
- Team ID for Minnesota Twins: `142`
- Filter to **home games** (Target Field)

Example pattern:

```text
https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=142&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
```

### 2) Ticketmaster Discovery API (concerts/events)
- Register for API key
- Query by Target Field venue ID and date range
- Useful for large concerts/special events that cause parking spikes

### 3) Optional iCal fallback/augmentation
- Venue/event calendar feeds (if available)
- Parse with Python `icalendar`
- Useful as backup if API coverage is incomplete

## MVP Scope (Phase 1)

Deliver a daily message with:
- Events **today + next 2 days**
- Event start time (local)
- Basic impact level (`Low`, `Medium`, `High`)
- Short recommendation

Example output:

```text
Downtown Parking Alert (Target Field area)
Date: 2026-09-03

HIGH: Twins vs White Sox at 12:10 PM (home)
HIGH: Major concert at 7:00 PM
MEDIUM: Nearby pregame event around noon

Recommendation: Expect high rates near Ramp C. Consider ABC Ramps, North Loop lot options, or earlier arrival.
```

## Impact Scoring Heuristic (Initial)

Start simple and improve over time:

- **High**
  - Twins home game with first pitch between 11:00 AM and 2:00 PM
  - Any major concert/event with start between 4:00 PM and 8:00 PM (daytime setup + early arrivals)
  - Multiple same-day events
- **Medium**
  - Home game later in afternoon/evening
  - Single moderate attendance event not overlapping arrival window
- **Low**
  - No known Target Field events in next 24h

## Runtime / Hosting

### Primary: GitHub Actions (recommended)
- Zero infrastructure — runs on GitHub's free Ubuntu runners
- Schedule via cron expression in the workflow file
- Secrets managed natively (no `.env` files to protect)
- Free for public repos; private repos have generous free minutes (2,000/month)
- Workflow file lives at `.github/workflows/daily-digest.yml`

### Alternative: TrueNAS (self-hosted, full control)
Use this if you prefer no external dependencies or want guaranteed daily execution independent of GitHub availability.

1. **Linux VM** — Ubuntu/Debian, Python + virtualenv, cron or systemd timer
2. **Container on TrueNAS SCALE** — Python slim image, external cron trigger
3. **Jail on TrueNAS CORE** — Python in jail, cron for daily execution

## Project Structure Proposal

```text
mpls-parking-analyzer/
├── README.md
├── docs/
│   └── implementation-plan.md
├── .github/
│   └── workflows/
│       └── daily-digest.yml
├── src/
│   ├── main.py
│   ├── config.py
│   ├── sources/
│   │   ├── mlb.py
│   │   ├── ticketmaster.py
│   │   └── ical.py
│   ├── scoring/
│   │   └── impact.py
│   ├── output/
│   │   └── formatter.py
│   └── notify/
│       ├── email.py
│       └── ntfy.py
├── tests/
│   ├── test_impact.py
│   └── test_formatter.py
├── .env.example
├── requirements.txt
└── Makefile
```

## Configuration

Non-secret settings are defined directly in the workflow file as `env:` variables. Secrets are stored in **GitHub repo Settings → Secrets and variables → Actions**.

### Workflow `env:` (non-sensitive)
- `TZ=America/Chicago`
- `LOOKAHEAD_DAYS=2`
- `ARRIVAL_WINDOW_START=10:30`
- `ARRIVAL_WINDOW_END=11:30`
- `NOTIFY_EMAIL=...`

### GitHub Actions secrets (sensitive)
- `TICKETMASTER_API_KEY`
- `SMTP_HOST`
- `SMTP_USER`
- `SMTP_PASS`
- `NTFY_TOPIC` (optional)

For local development, mirror these in a `.env` file (listed in `.gitignore`).

## Scheduling

The workflow is triggered by a `schedule` event using UTC time. 7:30 AM CT (CDT) = 12:30 PM UTC in summer; 7:30 AM CT (CST) = 13:30 PM UTC in winter. Use the CDT offset during the baseball/event season.

```yaml
# .github/workflows/daily-digest.yml
name: Daily Parking Digest

on:
  schedule:
    - cron: '30 12 * * *'  # 7:30 AM CDT (UTC-5 in summer)
  workflow_dispatch:        # allow manual runs

jobs:
  digest:
    runs-on: ubuntu-latest
    env:
      TZ: America/Chicago
      LOOKAHEAD_DAYS: 2
      ARRIVAL_WINDOW_START: "10:30"
      ARRIVAL_WINDOW_END: "11:30"
      NOTIFY_EMAIL: ${{ vars.NOTIFY_EMAIL }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python src/main.py
        env:
          TICKETMASTER_API_KEY: ${{ secrets.TICKETMASTER_API_KEY }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
          NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}
```

> **Note:** GitHub Actions schedules can be delayed by a few minutes during high-load periods. For a morning digest this is acceptable.

## Notification Options

1. **Email (SMTP)**
   - Works everywhere
   - Good for morning digest

2. **ntfy.sh**
   - Very quick push setup
   - Optional self-hosting

3. **Pushover/Telegram**
   - Nice mobile UX
   - Add later if needed

## Logging and Reliability

- Print timestamped log lines to stdout (GitHub Actions captures all stdout/stderr per run)
- Track source fetch success/failure
- If one source fails, continue with available sources
- Include "data freshness" line in summary
- Retry transient HTTP failures (backoff)
- GitHub Actions retains run logs for 90 days — use them to audit missed or failed runs
- Use `workflow_dispatch` trigger to manually re-run the digest at any time from the GitHub UI

## Testing Strategy

- Unit tests for:
  - Event normalization
  - Timezone conversion
  - Impact scoring
  - Digest formatting
- Integration test with recorded sample payloads
- Dry-run mode to print summary without sending notifications

## Security / Ops Notes

- **Never commit secrets** — use GitHub Actions secrets for all credentials
- Local `.env` file for development only; ensure it is in `.gitignore`
- Use least-privilege email credentials (app password/token, not your main account password)
- Rotate secrets periodically via GitHub repo Settings
- GitHub Actions secrets are masked in logs automatically
- Consider making the repo **private** if the workflow file itself contains any sensitive values

## Roadmap

### Phase 1 (MVP)
- MLB home-game fetch
- Ticketmaster event fetch
- Basic scoring
- Email digest via GitHub Actions scheduled workflow

### Phase 2
- iCal fallback source
- Better scoring with historical parking patterns (manual tuning)
- Push notifications
- Weekly trend summary

### Phase 3
- Small web dashboard (optional)
- ICS export of "high impact days"
- Add nearby venue signals (Target Center, US Bank Stadium, downtown conventions)

## Definition of Done (MVP)

MVP is complete when:
1. GitHub Actions workflow runs daily on schedule without manual intervention
2. It fetches at least one reliable event source + Twins schedule
3. It sends a clear summary before commute time
4. It correctly flags obvious high-impact event days

## Next Implementation Steps

1. Scaffold Python project and `requirements.txt`
2. Implement `sources/mlb.py` and validate home-game parsing
3. Implement `sources/ticketmaster.py` with API key
4. Implement scoring module and formatter
5. Add email notifier
6. Create `.github/workflows/daily-digest.yml` and add secrets to the GitHub repo
7. Trigger a manual run via `workflow_dispatch` to validate end-to-end
8. Run for one week and tune scoring thresholds
