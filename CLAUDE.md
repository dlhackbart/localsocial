# Local Social — Developer Guide

## What This Is

Local venue/event recommendation system for San Diego North County. Two parts:
1. **Python notification pipeline** — scrapes events daily, scores them, sends SMS + email with a 7-day Social Plan
2. **React Native app (Expo 54)** — mobile UI with Tonight / Log / Profile tabs, subscription gating

## Run

### Notifications (the part that's live and running)
```bash
python scripts/scrape_events.py              # Scrape 6 sources → data/scraped_events.json
python scripts/daily_social_plan.py          # Tonight's plan
python scripts/daily_social_plan.py --week   # Full 7-day plan
python scripts/notify.py --dry-run morning   # Preview without sending
python scripts/notify.py morning             # Send SMS + email (weekly plan)
python scripts/notify.py gotime             # Send go-time (tonight only)
python scripts/notify.py log                # Send logging prompt
```

### Mobile App
```bash
npm install && npm start   # Expo Go
```

## Key Files

### Notification Pipeline (Python — `scripts/`)
| File | Purpose |
|------|---------|
| `scripts/scrape_events.py` | Scrapes 6 North County sources (Belly Up, Del Mar Plaza, Seaside Sessions, Encinitas 101, North Coast Rep, La Paloma Theatre) |
| `scripts/daily_social_plan.py` | Python scoring engine with 10 venues + scraped events. Generates 7-day plan with up to 5 ranked picks per day |
| `scripts/notify.py` | Sends SMS (Verizon gateway) + email (Gmail SMTP with dark HTML) |
| `scripts/notify_config.py` | SMTP credentials — imports from `spy_timing/config.py` |
| `scripts/discover_city.py` | Auto-discover event sources for any US city (67 URL patterns + Claude Haiku LLM) |
| `scripts/run_*.bat` | Windows scheduled task launchers |

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

## Scheduled Tasks (Windows)

| Task | Time | Action |
|------|------|--------|
| `LocalSocial_Scrape_7am` | 7:00 AM | Scrape all 6 sources |
| `LocalSocial_Morning_8am` | 8:00 AM | SMS (tonight top 3) + email (7-day weekly plan) |
| `LocalSocial_GoTime_4pm` | 4:00 PM | SMS ("GO TIME" + tonight) + email (tonight only) |
| `LocalSocial_LogPrompt_930pm` | 9:30 PM | SMS only ("Did you go out?") |

## Event Sources (6 active)

| Source | Method | Data quality |
|--------|--------|-------------|
| Belly Up Tavern | JS `display` field extraction | Artist names, dates. Big-show detection. |
| Del Mar Plaza | JSON-LD structured data | Seaside Sessions + Monarch performers by name |
| Seaside Sessions | Extracted from Plaza scrape | Named artist + genre per date |
| Encinitas 101 | JSON-LD + known schedule | Street fairs, cruise nights, Taste of Encinitas |
| North Coast Rep | JSON-LD + known schedule | Theater runs with opening dates |
| La Paloma Theatre | Known schedule (Veezi JS widget, can't scrape via urllib) | Film titles, times, special events. Refresh manually. |

### Sources investigated but not viable
| Source | Why not |
|--------|---------|
| Mr. Peabody's (Encinitas) | Domain for sale — closed |
| Salty Bear (Encinitas) | Domain not found |
| Encinitas city gov | 403 blocked |
| Lux Art Institute | JS-heavy, timeout |
| SD Union-Tribune / Del Mar Times | Redirects to SDUT, blocked by bot protection |
| Visit Carlsbad | JS-rendered, no content without browser |

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

## Data Flow

```
7:00 AM: scrape_events.py
  → fetch Belly Up (JS display fields)
  → fetch Del Mar Plaza (JSON-LD)
  → known Seaside Sessions schedule
  → fetch Encinitas 101 (JSON-LD)
  → fetch North Coast Rep (JSON-LD)
  → known La Paloma schedule
  → dedupe → save data/scraped_events.json (94+ events, 30 days)

8:00 AM: notify.py morning
  → generate_weekly_plan() (7 days)
    → for each day:
      → score static venues (10 venues × day-of-week match)
      → extract Monarch/Seaside performers from scraped data
      → enrich static venues with real performer names
      → score scraped events (+6 base, +4 big, +2 music)
      → merge + sort by score
      → dedupe by physical location (Monarch=Plaza)
      → top 5 picks
  → format SMS (tonight top 3, 160 chars)
  → format email (tonight full detail + 6 upcoming days compact)
  → send via Gmail SMTP → phone@vtext.com + email

4:00 PM: notify.py gotime
  → generate tonight only → SMS + email

9:30 PM: notify.py log
  → SMS: "Did you go out tonight?"
```

## Conventions

- **"Social Plan"** — never "Dating Plan"
- **No weak recs** — say "No events today." when nothing is strong
- **Concise, practical, adult tone** — readable in 15 seconds
- SMS ≤ 160 chars (tonight only), email gets full 7-day plan
- TypeScript strict in mobile app, Python 3.10+ for scripts
- Supabase calls null-safe (`if (!supabase) return`)
- Dark theme: `bg=#0e1116`, `accent=#4f8cff`, `go=#30c67c`
