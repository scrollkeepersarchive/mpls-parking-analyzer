# Minneapolis Parking Analyzer

Implementation plan for a self-hosted tool that helps predict downtown Minneapolis parking pressure (especially near Ramp C / Target Field) before driving in.

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
TrueNAS host
└── Linux VM or container
    └── Daily scheduler (cron/systemd timer)
        └── Python app
            ├── Fetch Twins home games (MLB StatsAPI)
            ├── Fetch concerts/special events (Ticketmaster API and/or iCal feed)
            ├── Score parking impact by date/time proximity
            ├── Generate short digest
            └── Send notification (email/push)
```

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

## Runtime / Hosting on TrueNAS

You have three reasonable options:

1. **Linux VM (recommended for easiest dev loop)**
   - Ubuntu/Debian
   - Python + virtualenv
   - cron or systemd timer

2. **Container on TrueNAS SCALE**
   - Python slim image
   - bind-mount config and logs
   - scheduler inside container or external cron trigger

3. **Jail on TrueNAS CORE**
   - Install Python in jail
   - cron for daily execution

## Project Structure Proposal

```text
mpls-parking-analyzer/
├── README.md
├── docs/
│   └── implementation-plan.md
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

Use environment variables for secrets and runtime options:

- `TZ=America/Chicago`
- `LOOKAHEAD_DAYS=2`
- `ARRIVAL_WINDOW_START=10:30`
- `ARRIVAL_WINDOW_END=11:30`
- `TICKETMASTER_API_KEY=...`
- `SMTP_HOST=...`
- `SMTP_USER=...`
- `SMTP_PASS=...`
- `NOTIFY_EMAIL=...`
- `NTFY_TOPIC=...` (optional)

## Scheduling

### Cron example (daily at 7:30 AM local)

```cron
30 7 * * * /usr/bin/python3 /opt/mpls-parking-analyzer/src/main.py
```

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

- Log each run to file with timestamps
- Track source fetch success/failure
- If one source fails, continue with available sources
- Include "data freshness" line in summary
- Retry transient HTTP failures (backoff)

## Testing Strategy

- Unit tests for:
  - Event normalization
  - Timezone conversion
  - Impact scoring
  - Digest formatting
- Integration test with recorded sample payloads
- Dry-run mode to print summary without sending notifications

## Security / Ops Notes

- Keep API keys and SMTP credentials in `.env` (never commit secrets)
- Use least-privilege email credentials (app password/token)
- Rotate secrets periodically
- Consider simple health check (last successful run timestamp)

## Roadmap

### Phase 1 (MVP)
- MLB home-game fetch
- Ticketmaster event fetch
- Basic scoring
- Email digest via cron

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
1. Automated job runs daily on your TrueNAS-hosted runtime
2. It fetches at least one reliable event source + Twins schedule
3. It sends a clear summary before commute time
4. It correctly flags obvious high-impact event days

## Next Implementation Steps

1. Scaffold Python project and dependency list
2. Implement `sources/mlb.py` and validate home-game parsing
3. Implement `sources/ticketmaster.py` with API key
4. Implement scoring module and formatter
5. Add email notifier
6. Add cron/systemd timer
7. Run for one week and tune scoring thresholds
