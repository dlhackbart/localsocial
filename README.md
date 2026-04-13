# Local Social

**Where should I go tonight?**

A location-aware, goal-based venue and event recommendation engine for San Diego's North County coast. Local Social scrapes real event data from local venues, scores everything against your social goals, and delivers a ranked 7-day Social Plan via SMS and email every morning.

Not a dating app publicly, but optimizes for connection (including dating) internally. Uses "Social Plan" terminology — concise, practical, adult.

## How It Works

Every day at 7 AM, the scraper pulls live event data from 6 North County sources. At 8 AM, you get a text and email with up to 5 ranked picks for tonight plus the next 6 days. At 4 PM, a go-time nudge. At 9:30 PM, a logging prompt.

```
7:00 AM  — Scrape all sources → data/scraped_events.json (94+ events)
8:00 AM  — SMS: tonight's top 3  |  Email: full 7-day Weekly Social Plan
4:00 PM  — SMS: "GO TIME" + tonight  |  Email: tonight's picks
9:30 PM  — SMS: "Did you go out tonight?"
```

The daily scrape re-validates all 30 days of event data. Each upcoming day gets more accurate as it approaches — a Thursday event has been checked Mon, Tue, Wed, and Thu morning before you see the 4 PM go-time nudge.

## Quick Start

### Mobile App (Expo)
```bash
npm install
npm start            # Expo dev server (scan QR with Expo Go)
npm run ios          # iOS simulator
npm run android      # Android emulator
```

### Notifications (Python — runs on your machine)
```bash
python scripts/scrape_events.py              # Scrape all sources now
python scripts/daily_social_plan.py --week   # Preview 7-day plan
python scripts/notify.py --dry-run morning   # Preview SMS + email without sending
python scripts/notify.py morning             # Send real SMS + email
```

### Environment
```bash
cp .env.example .env
# Fill in EXPO_PUBLIC_SUPABASE_URL and EXPO_PUBLIC_SUPABASE_ANON_KEY (optional)
```

Supabase is optional. Without it, the app runs fully local. Notifications use Gmail SMTP credentials from `spy_timing/config.py`.

## Coverage Area

Four areas in San Diego County's North County coast:

| Area | Adjacent Zones |
|------|----------------|
| Del Mar | Solana Beach, Encinitas |
| Solana Beach | Del Mar, Encinitas |
| Encinitas | Solana Beach, Carlsbad |
| Carlsbad | Encinitas |

**Key local knowledge:** Monarch Ocean Pub is inside Del Mar Plaza — same physical location. Treated as one venue in scoring and deduplication.

## Event Sources

6 sources scraped daily, producing 94+ events over a 30-day window:

| Source | URL | Area | What it provides |
|--------|-----|------|-----------------|
| **Belly Up Tavern** | bellyup.com/events | Solana Beach | Full lineup with artist names — parsed from JS `display` field. Big-show detection for headline acts (Matisyahu, Disco Biscuits, Cory Wong, Pat Metheny, etc.) |
| **Del Mar Plaza** | delmarplaza.com/events | Del Mar | Seaside Sessions performers by name + genre (Wed/Fri 5-7 PM), Monarch Ocean Pub performers (Lee Melton, Ben Benavente, Christian Taylor), special events (Book Crawl, Kentucky Derby Party) |
| **Seaside Sessions** | (from Del Mar Plaza scrape) | Del Mar | Named performer schedule with genres, extracted and formatted separately |
| **Encinitas 101** | encinitas101.com/events | Encinitas | Street fairs (Spring Street Fair Apr 25-26), Cruise Nights (monthly, 5:30-7:30 PM), Taste of Encinitas (Aug) |
| **North Coast Rep** | northcoastrep.org | Solana Beach | Theater productions — current show + upcoming season (Beau Jest, The Most Happy Fella) |
| **La Paloma Theatre** | lapalomatheatre.com/showtimes | Encinitas | Classic films, indie screenings, special events (Rocky Horror live shadow cast, SD Italian Film Festival). Veezi ticketing (JS-rendered) — schedule maintained as known data, refreshed periodically |

### Static Venues (10 venues with weekly schedules)

| Venue | Area | Energy | Events |
|-------|------|--------|--------|
| Monarch Ocean Pub | Del Mar | Medium | Wed-Sun, performers from scrape |
| Del Mar Plaza | Del Mar | Medium | Thu/Sat Seaside Sessions 5-7 PM |
| Jake's Del Mar | Del Mar | Medium | Fri happy hour, Sat sunset, Sun brunch |
| Belly Up Tavern | Solana Beach | High | Thu-Sun headliners (from scrape) |
| Union Kitchen & Tap | Encinitas | Medium | Wed/Thu happy hour, Fri DJ 9 PM |
| The Saloon | Encinitas | High | Fri/Sat live band 9 PM |
| Moonlight Beach Bar | Encinitas | High | Sat DJ night 9 PM |
| 1st Street Bar | Encinitas | Medium | Tue/Thu neighborhood night, Sun locals |
| Campfire | Carlsbad | Medium | Fri/Sat patio scene 6-9 PM |
| Park 101 | Carlsbad | High | Fri/Sat outdoor DJ 8 PM |

**Enrichment:** Static venues show generic placeholders ("acoustic", "live band"). The scraper replaces these with real performer names when available — Monarch shows "Lee Melton" instead of "acoustic" on nights the Plaza calendar has the actual act.

## Scoring Engine

Two scoring paths: static venues and scraped events.

### Venue Scoring (`scripts/daily_social_plan.py`)

| Factor | Points | Condition |
|--------|--------|-----------|
| Event exists tonight | +5 | Venue has a matching day-of-week event |
| High social energy | +3 | Goal is `social` or `both` AND venue energy is `high` |
| Conversation-friendly | +3 | Goal is `dating` or `both` AND venue is conversation-friendly |
| Repeat-friendly | +2 | Familiar crowd returns |
| Broad appeal | +2 | Event flagged as broadly appealing |
| Balanced vibe match | +1 | User vibe is `balanced` AND venue energy is `medium` |
| Low social value | -3 | Venue flagged as low social value |
| Vibe mismatch | -2 | Quiet + high energy, or high energy + low energy |
| Dating penalty (no repeat) | -2 | Dating goal AND not repeat-friendly |
| Dating penalty (no convo) | -2 | Dating goal AND not conversation-friendly |

### Scraped Event Scoring

| Factor | Points | Condition |
|--------|--------|-----------|
| Real confirmed event | +6 | Base score (higher than static +5 — it's real, dated data) |
| Big event | +4 | Headline act, festival, or special event |
| Live music | +2 | Category is `live_music_small` |
| Food/market | +1 | Category is `markets` or `food_drink` |
| Featured venue | +1 | Belly Up or Del Mar Plaza |

### Grading

| Score | Grade | Decision |
|-------|-------|----------|
| 8+ | A | GO |
| 5-7 | B | MAYBE |
| <5 | C | SKIP |

### Deduplication

1. **Monarch/Plaza merge** — same physical location, never shown as separate picks
2. **Scraped venue cross-listings** — Del Mar Plaza listing "Monarch Ocean Pub – Lee Melton" is extracted as Monarch's performer, not a separate event
3. **Same-artist dedup** — two Belly Up listings for the same headliner collapse to one
4. **Physical location dedup** — picks are deduped by location key, keeping highest score

## Notification System

### Architecture

```
scripts/
├── scrape_events.py        # Scrapes 6 sources → data/scraped_events.json
├── daily_social_plan.py    # Python scoring engine → generates 7-day plan
├── notify.py               # Sends SMS (Verizon gateway) + email (Gmail SMTP)
├── notify_config.py        # SMTP credentials (imports from spy_timing/config.py)
├── discover_city.py        # Auto-discover event sources for any US city
├── run_scrape_events.bat   # Scheduled task launcher (7 AM)
├── run_notify_morning.bat  # Scheduled task launcher (8 AM)
├── run_notify_gotime.bat   # Scheduled task launcher (4 PM)
└── run_notify_log.bat      # Scheduled task launcher (9:30 PM)
```

### Windows Scheduled Tasks

| Task | Time | What it does |
|------|------|-------------|
| `LocalSocial_Scrape_7am` | 7:00 AM daily | Scrapes all 6 sources, saves `data/scraped_events.json` |
| `LocalSocial_Morning_8am` | 8:00 AM daily | SMS: tonight top 3. Email: full 7-day Weekly Social Plan |
| `LocalSocial_GoTime_4pm` | 4:00 PM daily | SMS: "GO TIME" + tonight. Email: tonight's picks only |
| `LocalSocial_LogPrompt_930pm` | 9:30 PM daily | SMS only: "Did you go out tonight?" |

### SMS Format (160 chars, tonight only)
```
Sun: 1)Monarch 3-6 PM 2)Jake's Del Mar 11 AM-3 PM 3)1st Street Bar 3-7 PM | GO, Medium
```

### Email Format (full 7-day Weekly Social Plan)
```
WEEKLY SOCIAL PLAN — Del Mar / Solana Beach / Encinitas
Generated 2026-04-12
==================================================

TONIGHT: Sunday
----------------------------------------
#1 Top Pick: Monarch Ocean Pub — 3-6 PM
  Lee Melton
  Crowd: conversational, repeat-friendly, relaxed vibe  |  Grade A  |  GO
  Strong for conversation

#2: Jake's Del Mar — 11 AM-3 PM
  brunch into afternoon
  ...

==================================================
COMING UP
==================================================

MONDAY 04-13  [High priority]
  1. Belly Up Tavern — 8:00 PM ***
     Matisyahu
     high energy  |  Grade A  |  GO

TUESDAY 04-14
  1. 1st Street Bar — 7-10 PM
     neighborhood night
     ...
```

### Delivery
- **SMS**: Gmail SMTP → `phone@vtext.com` (Verizon email-to-SMS gateway)
- **Email**: Gmail SMTP with dark-theme HTML formatting
- **Credentials**: Reused from `spy_timing/config.py` (`SMTP_USER`, `SMTP_PASSWORD`, `ALERT_SMS_TO`, `ALERT_EMAIL_TO`)

### Priority Levels

| Level | When |
|-------|------|
| **High** | Thu/Sat (Seaside Sessions), Fri (multiple options), any day with a big event |
| **Medium** | Wed/Sun (Monarch rotation) |
| **Low** | Mon/Tue (usually quiet) |

Big events (headline Belly Up shows, Encinitas Street Fair, Italian Film Festival, Rocky Horror) auto-bump any day to High priority.

## City Auto-Discovery

For expanding to other cities. Replicates the manual discovery process used for North County.

```bash
python scripts/discover_city.py "Bend, OR"           # Discover sources
python scripts/discover_city.py "Austin, TX" --dry-run # Probe without saving
python scripts/discover_city.py --list                 # List discovered cities
```

### What It Probes (67 URL patterns per city)

| Pattern | Examples |
|---------|----------|
| **City government** | CivicPlus calendars, WordPress Tribe Events, `.gov/events` |
| **Visitor/tourism bureau** | `visit{city}.com/events`, `explore{city}.com/events` |
| **Downtown association** | `downtown{city}.org/events`, `{city}101.com/events` |
| **Library (LibCal)** | `{city}library.libcal.com/ical_subscribe/all` |
| **Eventbrite** | `eventbrite.com/d/{state}--{city}/events/` |
| **LLM discovery** | Claude Haiku suggests city-specific music venues, theaters, newspapers, libraries |

Each URL is validated for real event content (iCal format or HTML with event signals/structured data). Results saved to `data/city_sources/{slug}.json`.

**Tested:** Bend, OR → found 5 verified sources (Visit Bend, Downtown Bend, Eventbrite, Deschutes Library, Bend Bulletin) in under 60 seconds.

## Mobile App Architecture

```
SocialLocal_app/
├── app/                        # Expo Router screens
│   ├── _layout.tsx             # Root layout (PreferencesProvider + SubscriptionProvider)
│   ├── (tabs)/
│   │   ├── _layout.tsx         # Tab bar (Tonight / Log / Profile)
│   │   ├── index.tsx           # Tonight screen — recommendations + reveal gate
│   │   ├── log.tsx             # Log screen — venue visit history form
│   │   └── profile.tsx         # Profile screen — settings summary + plan toggle
│   ├── preferences.tsx         # Modal — area, zones, goal, vibe, categories
│   └── add-source.tsx          # Modal — user-contributed iCal feed submission
│
├── src/
│   ├── types.ts                # All TypeScript interfaces and type unions
│   ├── scoring.ts              # App-side recommendation engine (rule-based)
│   ├── theme.ts                # Dark mode palette, spacing, border radius
│   ├── data/
│   │   ├── venues.ts           # 10 static venues with weekly event schedules
│   │   ├── events.ts           # 25+ sample events (projected to current week)
│   │   └── areas.ts            # Area adjacency graph + default home area
│   ├── events/
│   │   ├── sources.ts          # ICalSource interface + hardcoded source list
│   │   ├── resolver.ts         # 3-tier source resolution chain
│   │   ├── store.ts            # Event cache (6hr TTL) + fetch/merge logic
│   │   └── ical.ts             # Minimal RFC5545 iCalendar parser
│   ├── store/
│   │   ├── preferences.tsx     # PreferencesContext + AsyncStorage + Supabase sync
│   │   ├── subscription.tsx    # SubscriptionContext — free/paid reveal gating
│   │   └── logs.ts             # Visit log storage (local + Supabase sync)
│   └── supabase/
│       └── client.ts           # Supabase client init + device ID helper
│
├── scripts/                    # Notification + scraping pipeline (Python)
│   ├── scrape_events.py        # 6-source event scraper
│   ├── daily_social_plan.py    # Scoring engine + 7-day plan formatter
│   ├── notify.py               # SMS + email sender
│   ├── notify_config.py        # SMTP credentials
│   ├── discover_city.py        # Multi-city source discovery
│   └── run_*.bat               # Windows scheduled task launchers
│
├── supabase/
│   ├── schema.sql              # Full Postgres schema (7 tables + RLS policies)
│   └── functions/sources/      # Deno Edge Function (proxy, discover, add, list)
│
├── spec_input/                 # Original product spec + ChatGPT handoff docs
│   ├── PRODUCT_SPEC.md
│   ├── developer_brief.md
│   └── chatgpt_handoff/        # Notification specs from ChatGPT automation
│
└── data/                       # Runtime data (gitignored)
    ├── scraped_events.json     # Daily scrape output (94+ events)
    └── city_sources/           # Discovered sources per city
```

## Supabase Backend (Optional)

| Table | Purpose |
|-------|---------|
| `users` | Device registry (`device_id` PK) |
| `preferences` | User preferences (home area, goal, vibe) |
| `logs` | Venue visit history |
| `venues` / `events` | Venue catalog + event schedules |
| `sources` | Crowdsourced iCal source registry |
| `area_discovery` | Tracks which areas have been probed |

Edge Function (`supabase/functions/sources/index.ts`): `proxy`, `discover`, `add`, `list` actions.

## UI & Theme

Dark mode. `bg=#0e1116`, `card=#171c24`, `accent=#4f8cff`, `go=#30c67c`, `maybe=#f0b541`, `skip=#ef5b5b`.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Mobile | React Native 0.81 + Expo 54 + Expo Router 6 |
| Notifications | Python 3 + Gmail SMTP + Verizon email-to-SMS |
| Scraping | Python `urllib` + regex (no Selenium/Playwright) |
| Backend | Supabase (optional) — Postgres + Edge Functions on Deno |
| Scheduling | Windows Task Scheduler (4 daily tasks) |

## What's Done vs What's Next

### Done
- 10-venue static data with real attributes (energy, conversation, repeat)
- 6-source event scraper with performer name enrichment
- Rule-based scoring engine (venues + scraped events)
- 7-day Weekly Social Plan with up to 5 ranked picks per day
- SMS + email notifications at 8 AM / 4 PM / 9:30 PM
- Venue deduplication (Monarch/Plaza merge, cross-listings, same-artist)
- Big event detection and priority auto-bump
- City auto-discovery for expansion to other US cities
- Mobile app with Tonight / Log / Profile tabs
- Subscription gating (mock — free: 1/week, paid: 1/day)
- Visit logging with crowd grade and would-go-again tracking
- iCal feed integration + user-contributed source submission

### Not Yet Built
- **Real authentication** — device-ID only, no sign-up/login
- **Real payments** — Stripe/RevenueCat for paid plan
- **Weather/turnout notes** — in notification output
- **Scoring from log data** — use crowd grades to improve future picks
- **Push notifications** — currently SMS/email only
- **Multi-city deployment** — discovery tool built, scraper needs per-city config
- **App store submission** — Apple + Google Play
