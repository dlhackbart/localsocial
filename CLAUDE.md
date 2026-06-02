# Local Social — Developer Guide

> **⚡ REORIENTED 2026-06-02 — now a WEEKLY LIVE-MUSIC-FIRST reminder.**
> The product is no longer a daily all-categories "Social Plan." It is a weekly
> live-music lineup (Del Mar → Oceanside) scraped once a week and emailed + texted
> daily as a reminder. The old daily-plan code (`daily_social_plan.py`,
> `notify.py morning/gotime/log`) still exists but is **no longer scheduled** — see
> "Current Product" below. The mobile app sections further down are unchanged.

## What This Is

Local live-music + venue system for the San Diego North County coast. Two parts:
1. **Python pipeline (LIVE)** — scrapes live music once a week, caches it, and sends
   a music-first email + SMS reminder every late afternoon.
2. **React Native app (Expo 54)** — mobile UI with Tonight / Log / Profile tabs
   (predates the reorientation; still daily-plan-shaped).

## Current Product — weekly live-music reminder

**Cadence:** scrape ONCE on Monday → cache `data/weekly_music.json` → read & send
that cache daily. The lineup only changes weekly; the daily send is a reminder.

```bash
python scripts/scrape_music.py                 # Probe all music sources, print summary
python scripts/notify.py weekly                # Mon refresh → rebuild data/weekly_music.json
python scripts/notify.py --dry-run reminder    # Preview the email + SMS without sending
python scripts/notify.py reminder              # Send email + SMS of this week's live music
```

**Sourcing model — every event carries provenance + a confidence marker:**
- `✅` (tier 1) scraped straight from the venue — rely on it
- `~` (tier 2) secondary listing / aggregator — worth a glance
- `⚠` (tier 3) manual overlay / unverified — double-check

`data/music_manual.json` is the operator overlay for venues the auto-scrapers can't
reach (JS-only sites); entries show as `⚠` until confidence is raised. Template:
`data/music_manual.example.json`. **Never fabricate a lineup — omit a dry venue.**

### Legacy (kept, NOT scheduled)
```bash
python scripts/notify.py morning|gotime|log    # old daily Social Plan sends
python scripts/daily_social_plan.py [--week]    # old scoring engine (still imported for VENUES)
```

### Mobile App
```bash
npm install && npm start   # Expo Go
```

## Key Files

### Music pipeline (Python — `scripts/`) — CURRENT
| File | Purpose |
|------|---------|
| `scripts/scrape_music.py` | **Live-music scrapers** (Del Mar → Oceanside). One fn per source → normalized dicts with `tier`/`confidence`/`marker`. `scrape_all_music()` orchestrates with per-source try/except + dedupe. Loads `data/music_manual.json` overlay. |
| `scripts/weekly_music.py` | `build_weekly_music()` writes `data/weekly_music.json` (+ dated backups in `data/weekly_music_backups/`); `load_weekly_music()` with staleness flag; `build_reminders()` from `daily_social_plan.VENUES`. |
| `scripts/format_music_email.py` | `format_music_email()` (music-first → REMINDERS → legend) + `format_music_sms()` (condensed). |
| `scripts/notify.py` | Actions: **`weekly`** (refresh cache), **`reminder`** (daily email+SMS) — plus legacy `morning/gotime/log`. Email = Gmail SMTP; SMS = Verizon MMS gateway. |
| `scripts/notify_config.py` | SMTP credentials — imports from `spy_timing/config.py` |
| `scripts/run_notify_reminder.bat` / `run_weekly_music.bat` | Scheduled-task launchers for the new pipeline (weekly batch logs to its OWN `weekly_music.log`, NOT the legacy `scrape.log`). |

### Legacy pipeline (Python — `scripts/`) — kept, not scheduled
| File | Purpose |
|------|---------|
| `scripts/scrape_events.py` | Old daily multi-category scraper → `data/scraped_events.json`. (`NC_AREAS` now includes Oceanside/Cardiff/Leucadia.) |
| `scripts/daily_social_plan.py` | Old scoring engine + `VENUES`/`AREAS` (still imported by `weekly_music.py` for the reminders list). `AREAS` graph extended to Oceanside/Cardiff/Leucadia. |
| `scripts/discover_city.py` | Auto-discover event sources for any US city |

### Mobile App (TypeScript — `src/` + `app/`)
| File | Purpose |
|------|---------|
| `src/scoring.ts` | App-side recommendation engine (separate from Python pipeline) |
| `src/types.ts` | All TypeScript interfaces |
| `src/data/venues.ts` | Static venue data (app uses full 12, Python pipeline uses 10) |
| `src/data/events.ts` | 25+ sample events (seeded, projected to current week) |
| `src/data/areas.ts` | Area adjacency graph (4 areas) |
| `src/events/ical.ts` | iCalendar parser (RFC5545 subset) |
| `src/events/resolver.ts` | 3-tier source resolution: local → Supabase → discovery |
| `src/events/store.ts` | Event fetch + 6hr cache + merge with samples |
| `src/store/preferences.tsx` | PreferencesContext (AsyncStorage + Supabase sync) |
| `src/store/subscription.tsx` | SubscriptionContext (free/paid reveal gating) |
| `src/store/logs.ts` | Visit log persistence (local + Supabase sync) |
| `supabase/schema.sql` | Full Postgres schema (7 tables) |
| `supabase/functions/sources/index.ts` | Edge Function (proxy, discover, add, list) |

## Scheduled Tasks (Windows) — CURRENT

| Task | When | Action |
|------|------|--------|
| `LocalSocial_WeeklyMusic_Mon0700` | Mon 7:00 AM | `notify.py weekly` → rebuild `data/weekly_music.json` |
| `LocalSocial_Reminder_1600` | Daily 4:00 PM | `notify.py reminder` → email + SMS this week's music |

Tasks run via `wscript.exe C:\Users\dlhac\bin\run_hidden.vbs <batch>` as the
interactive user (least-priv). **Disabled** (superseded): `LocalSocial_Scrape_7am`,
`LocalSocial_Morning_8am`, `LocalSocial_GoTime_4pm`. XML backups of the old tasks
live in `scripts/task_backups_*/` (gitignored).

## Music Sources (Del Mar → Oceanside)

Confirmed **Tier-1** (✅ scraped directly, server-rendered/JSON, verified June 2026):

| Source | City | Method | Notes |
|--------|------|--------|-------|
| **Del Mar Plaza** | Del Mar | Tribe REST `/wp-json/tribe/events/v1/events` | **Monarch split:** `venue="Monarch Ocean Pub"`+cat Music = INSIDE (Wed/Fri/Sun 4 PM); `venue="Ocean View Deck"` = PATIO / Seaside Sessions (Thu/Sat 5 PM). Filter cat `Music`. |
| **Belly Up** | Solana Beach | reuse `scrape_events.scrape_belly_up` (display-field) | Touring acts. **Times default to 8 PM (approximate).** |
| **Pour House** | Oceanside | Squarespace `?format=json` `upcoming[]` | `startDate` is ms-epoch **UTC** → convert to PT. |
| **The Kraken** | Cardiff | Tribe REST API | Whole calendar tagged `Music`; filter noise by title (`_NON_MUSIC`). |

**Tier-2/3 gaps (NOT auto-scraped — operator embellishes via `music_manual.json`):**
The Sound (JS + Ticketmaster), Coyote Bar & Grill Carlsbad (DNS/cert issues),
The Roxy Encinitas (JS), Oceanside Pier Amphitheatre / Del Mar Fairgrounds
(Ticketmaster — need API key), Belching Beaver (no event page). Carlsbad has no
scrapeable in-city touring room; the big acts come through Belly Up / The Sound.

## Scoring Quick Reference

**Venues:** `+5 event` `+3 energy(social)` `+3 convo(dating)` `+2 repeat` `+2 broad` `+1 vibeMatch` `-3 lowSocial` `-2 vibeMismatch` `-2 datingNoRepeat` `-2 datingNoConvo`

**Scraped events:** `+6 confirmed` `+4 bigEvent` `+2 liveMusic` `+1 food/market` `+1 featuredVenue`

**Grade:** `8+=A(GO)` `5-7=B(MAYBE)` `<5=C(SKIP)`

## Deduplication Rules

1. **Monarch Ocean Pub = Del Mar Plaza** — same physical location (Monarch is inside the Plaza). Mapped via `SAME_LOCATION` dict. Never shown as two separate picks.
2. **Scraped venue cross-listings** — Plaza calendar lists "Monarch Ocean Pub – Lee Melton". Title containing a static venue name → extracted as performer enrichment, not a separate event.
3. **Same-artist dedup** — multiple Belly Up listings for the same headliner → keep first.
4. **Per-location dedup in picks** — only one pick per physical location, highest score wins.

## Performer Enrichment

Static venues have generic event types ("acoustic", "live band"). The scraper extracts real performer names:
- **Monarch**: "Live Music – Monarch Ocean Pub – Lee Melton" → Monarch shows "Lee Melton" instead of "acoustic"
- **Seaside Sessions**: "Seaside Sessions – Ben Powell" → shows "Seaside Sessions: Ben Powell (solo songwriter, guitar & vocals)"
- **Belly Up**: Always real artist names from the lineup scrape

Enrichment happens per-date — if the scrape doesn't have a performer for a specific night, the static placeholder remains.

## Local Knowledge (Important)

- **Monarch has TWO live-music streams, accurate from the Del Mar Plaza calendar:**
  - **INSIDE** — `venue="Monarch Ocean Pub"`, "Live Music – Monarch Ocean Pub – <artist>", Wed/Fri/Sun ~4–7 PM (Ben Benavente, Christian Taylor, Lee Melton).
  - **PATIO / Ocean View Deck** — `venue="Ocean View Deck"`, "Seaside Sessions – <artist>", Thu/Sat ~5–7 PM (Dulaney & Co., Tower 7). Different hours + performers.
- **Monarch Ocean Pub is inside Del Mar Plaza** — same building, same location
- **Seaside Sessions** happen on the Ocean View Deck at Del Mar Plaza (Wed + Fri, 5-7 PM)
- **Belly Up** is only worth calling out when the show materially improves the night
- **La Paloma** is Encinitas' historic theater (since 1928) — films + occasional live events
- **Thursday and Saturday** are the strongest recurring nights (Seaside Sessions)
- **Monday and Tuesday** are usually quiet — "No events today" is the correct output
- Pizza Port and Cedros District were removed from venue list (not relevant social venues)

## City Discovery (Expansion)

```bash
python scripts/discover_city.py "Bend, OR"        # Probe 67 URL patterns + LLM
python scripts/discover_city.py --list             # List all discovered cities
```

Probes: CivicPlus, WordPress, LibCal, visitor bureaus, downtown associations, Eventbrite, + Claude Haiku for city-specific venues/theaters/newspapers. Validated sources saved to `data/city_sources/{slug}.json`.

## Data Flow — CURRENT

```
MON 7:00 AM: notify.py weekly → weekly_music.build_weekly_music()
  → scrape_music.scrape_all_music()
      → Del Mar Plaza Tribe API   → Monarch INSIDE + Ocean View Deck PATIO
      → Pour House (Squarespace)  → Oceanside live music
      → The Kraken (Tribe API)    → Cardiff bands
      → Belly Up (legacy scraper) → Solana Beach touring acts
      → data/music_manual.json    → operator overlay (⚠ until verified)
      → dedupe + sort by (date, time)
  → back up previous weekly_music.json → weekly_music_backups/
  → write data/weekly_music.json {week_of, generated_at, events, reminders, source_report}

DAILY 4:00 PM: notify.py reminder
  → load_weekly_music() (flags _stale if ≥8 days old)
  → format_music_email():  🎵 music by day (Del Mar→Oceanside, ✅/~/⚠)
                           → 📍 REMINDERS (usual spots by area)
                           → source-key legend
  → format_music_sms():    condensed music-only week view
  → send email (Gmail SMTP) + SMS (Verizon MMS gateway)
```

(Legacy daily flow — `scrape_events.py` 7 AM, `notify.py morning/gotime/log` —
remains in the tree but its scheduled tasks are disabled.)

## Conventions

- **"Social Plan"** — never "Dating Plan"
- **No weak recs** — say "No events today." when nothing is strong
- **Concise, practical, adult tone** — readable in 15 seconds
- SMS ≤ 160 chars (tonight only), email gets full 7-day plan
- TypeScript strict in mobile app, Python 3.10+ for scripts
- Supabase calls null-safe (`if (!supabase) return`)
- Dark theme: `bg=#0e1116`, `accent=#4f8cff`, `go=#30c67c`
