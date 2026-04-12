# Local Social

**Where should I go tonight?**

A location-aware, goal-based venue and event recommendation engine for San Diego's North County coast. Local Social scores venues and community events against your social goals (dating, social, or both), vibe preference, and selected categories, then surfaces one top venue and one top event each night with a clear GO / MAYBE / SKIP decision.

Designed as a simple, non-predatory alternative to dating apps — it helps you find genuine social activities and connections in your area through a scoring engine that understands what you're optimizing for.

## Quick Start

```bash
npm install
npm start            # Expo dev server (scan QR with Expo Go)
npm run ios          # iOS simulator
npm run android      # Android emulator
npm run web          # Browser (iCal CORS limited)
```

### Environment (optional)

Supabase is optional. Without it, the app runs fully local with sample event data and AsyncStorage persistence.

```bash
cp .env.example .env
# Fill in EXPO_PUBLIC_SUPABASE_URL and EXPO_PUBLIC_SUPABASE_ANON_KEY
```

## Coverage Area

Currently seeded for four areas in San Diego County's North County coast:

| Area | Adjacent Zones |
|------|----------------|
| Del Mar | Solana Beach, Encinitas |
| Solana Beach | Del Mar, Encinitas |
| Encinitas | Solana Beach, Carlsbad |
| Carlsbad | Encinitas |

12 static venues and 25+ recurring sample events across these areas. Users set a home area and toggle which adjacent zones to include in recommendations.

## Architecture

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
│   ├── scoring.ts              # Recommendation engine (rule-based scoring)
│   ├── theme.ts                # Dark mode palette, spacing, border radius
│   ├── data/
│   │   ├── venues.ts           # 12 static venues with weekly event schedules
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
├── supabase/
│   ├── schema.sql              # Full Postgres schema (7 tables + RLS policies)
│   └── functions/
│       └── sources/index.ts    # Deno Edge Function (proxy, discover, add, list)
│
├── spec_input/                 # Original product spec and reference data
│   ├── PRODUCT_SPEC.md
│   ├── developer_brief.md
│   ├── areas.json
│   ├── venues.json
│   └── sample_output.json
│
└── scripts/
    └── seed_supabase.mjs       # DB seeding script (not used in MVP)
```

## Features

### Recommendation Engine (`src/scoring.ts`)

The engine scores venues and events independently, returning the top of each.

**Venue scoring** (for venues with an event tonight):

| Factor | Points | Condition |
|--------|--------|-----------|
| Event exists tonight | +5 | Always (venue must have a matching day-of-week event) |
| High social energy | +3 | Goal is `social` or `both` AND venue energy is `high` |
| Conversation-friendly | +3 | Goal is `dating` or `both` AND venue is conversation-friendly |
| Repeat-friendly | +2 | Venue has familiar crowd |
| Broad appeal event | +2 | Event flagged as broadly appealing |
| Balanced vibe match | +1 | User vibe is `balanced` AND venue energy is `medium` |
| Low social value | -3 | Venue flagged as low social value |
| Vibe mismatch | -2 | Quiet user + high energy venue, or high energy user + low energy venue |
| Dating penalty (no repeat) | -2 | Goal is `dating` AND venue is NOT repeat-friendly |
| Dating penalty (no conversation) | -2 | Goal is `dating` AND venue is NOT conversation-friendly |

**Event scoring** (for community events from iCal feeds + samples):

| Factor | Points | Condition |
|--------|--------|-----------|
| Event exists | +5 | Always |
| Intimate gathering | +2 | Small group setting |
| Conversation-friendly | +3 | Goal is `dating` or `both` |
| Repeat/recurring | +2 | Same crowd returns weekly |
| Broad appeal | +1 | Widely interesting |
| Dating penalty (no repeat) | -1 | Goal is `dating` AND event is not recurring |
| Quiet penalty (not intimate) | -1 | Vibe is `quiet` AND event is not intimate |

**Grading:**

| Score | Grade | Decision |
|-------|-------|----------|
| 8+ | A | GO |
| 5-7 | B | MAYBE |
| <5 | C | SKIP |

**Filtering:**
- Only venues/events in user's home area + enabled zones
- Only events in user's selected categories
- Only today's events (by day-of-week for venues, by ISO date for events)
- 60-minute grace window — an event that started at 6:55 PM is still shown at 7:05 PM

### Venues (`src/data/venues.ts`)

12 real venues across the four coverage areas:

| Venue | Area | Energy | Repeat | Conversation | Events |
|-------|------|--------|--------|--------------|--------|
| Monarch Ocean Pub | Del Mar | Medium | Yes | Yes | Wed-Sun acoustic 4-7 PM |
| Del Mar Plaza | Del Mar | Medium | Yes | Yes | Thu/Sat Seaside Sessions 5-7 PM |
| Jake's Del Mar | Del Mar | Medium | Yes | Yes | Fri happy hour, Sat sunset, Sun brunch |
| Belly Up Tavern | Solana Beach | High | No | No | Thu-Sun headliners 7-8 PM |
| Cedros District | Solana Beach | Medium | Yes | Yes | Wed-Fri walkable district 6-9 PM |
| Pizza Port Solana | Solana Beach | High | Yes | No | Fri/Sat brewery crowd 6-10 PM |
| Union Kitchen & Tap | Encinitas | Medium | Yes | Yes | Wed/Thu happy hour, Fri DJ 9 PM |
| The Saloon | Encinitas | High | Yes | No | Fri/Sat live band 9 PM |
| Moonlight Beach Bar | Encinitas | High | No | No | Sat DJ night 9 PM |
| 1st Street Bar | Encinitas | Medium | Yes | Yes | Tue/Thu neighborhood night, Sun locals |
| Campfire | Carlsbad | Medium | Yes | Yes | Fri/Sat patio scene 6-9 PM |
| Park 101 | Carlsbad | High | No | No | Fri/Sat outdoor DJ 8 PM |

### Sample Events (`src/data/events.ts`)

25+ seeded recurring events spanning all 12 categories:
- Hiking & Outdoor (Torrey Pines Sunrise Hike, Elfin Forest Hike, Cardiff Beach Walk)
- Classes & Workshops (Intro to Watercolor, Spanish Conversation Circle, Beginner Pottery)
- Community & Civic (Del Mar Community Mixer, Neighborhood Cleanup)
- Live Music (Acoustic Singer-Songwriter Night, Jazz Trio on the Patio)
- Art & Galleries (Cedros Art Walk, Gallery Opening)
- Food & Drink (Wine Tasting Flight Night, Chef's Counter Tasting)
- Book Clubs (Non-Fiction Book Club, Mystery Readers Circle)
- Markets (Del Mar Farmers Market, Leucadia Farmers Market)
- Community Theater (North Coast Rep Preview Night)
- Indie & Outdoor Film (Sunset Cinema on the Lawn, Indie Film Discussion)
- Meetups & Clubs (Classic Car Meetup, Photography Walk)
- Wellness (Sunset Beach Yoga, Sunrise Meditation & Tea)

Events are projected onto the current week using their seed day-of-week, so the app always has content even without live iCal feeds.

### Live iCal Integration

Three-tier source resolution chain (`src/events/resolver.ts`):

1. **Local sources** (`src/events/sources.ts`) — hardcoded feeds shipped with the app. Currently: Del Mar Community Calendar (CivicPlus).
2. **Supabase `sources` table** — crowdsourced and previously discovered feeds, stored server-side.
3. **Edge function auto-discovery** (`supabase/functions/sources/index.ts`) — runs once per area, then caches results:
   - **Rule-based probe**: Generates ~50 URL candidates from common municipal CMS patterns (CivicPlus, WordPress Tribe Events, LibCal, generic `/calendar.ics`). Validates each by fetching and checking for `BEGIN:VCALENDAR`.
   - **LLM discovery**: Calls Claude Haiku to suggest likely iCal URLs for the given town. Results are validated the same way.

**iCal parser** (`src/events/ical.ts`): Handles RFC5545 line unfolding, VEVENT extraction, DTSTART/DTEND parsing (both UTC `Z` and local time), SUMMARY/DESCRIPTION/LOCATION/CATEGORIES/UID fields, and escaped text decoding. Does not expand RRULE or resolve VTIMEZONE (city feeds mostly publish flat instances).

**Caching**: Events are cached in AsyncStorage with a 6-hour TTL per area. Sample events are always merged and deduped with live events (by title + date).

**CORS**: On web, most municipal sites block cross-origin requests. The Supabase Edge Function provides a proxy endpoint. On native (Expo Go / builds), direct fetch works. The app gracefully falls back to sample events if no live data is available.

### Subscription & Reveal Gating (`src/store/subscription.tsx`)

| Plan | Reveals | Reset |
|------|---------|-------|
| Free | 1 per ISO week | Monday |
| Paid ($12.99/mo) | 1 per day | Midnight |

Recommendations are shown in a "locked" state (venue name hidden, details obscured, grade/decision hidden) until the user spends a reveal. The unlock button shows remaining reveals and next reset date.

**Implementation**: Mock only — the plan toggle is a local state change with an Alert confirmation. No real payment processing. Reveal history is stored as ISO date strings in AsyncStorage (last 60 entries retained).

### Venue Visit Logging (`app/(tabs)/log.tsx` + `src/store/logs.ts`)

Users log venue visits with:
- **Went out?** — Yes / No
- **Venue** — Free text input
- **Crowd grade** — A / B / C
- **Would go again?** — Yes / Maybe / No

Logs are stored locally in AsyncStorage (last 200 entries) and synced to Supabase if configured. History is displayed as a scrollable list below the form.

### Preferences (`app/preferences.tsx` + `src/store/preferences.tsx`)

| Setting | Options | Default |
|---------|---------|---------|
| Home area | Del Mar, Solana Beach, Encinitas, Carlsbad | Del Mar |
| Nearby zones | Adjacent areas (auto-suggested from area graph) | All adjacent |
| Goal | Dating, Social, Both | Both |
| Vibe | Quiet, Balanced, High energy | Balanced |
| Categories | 12 event categories with All on / All off | All on |

Preferences persist to AsyncStorage and sync to Supabase. Changing the home area auto-selects all adjacent zones.

### User-Contributed Feeds (`app/add-source.tsx`)

Users can submit public iCal (.ics) URLs for their area. The form collects:
- Feed name (e.g., "Encinitas Library Events")
- iCal URL
- Default category
- Area (auto-set from home area)

On submit, the Supabase Edge Function validates the URL returns real iCal data before storing it. Valid feeds become available to all users in that area.

## Supabase Backend

### Schema (`supabase/schema.sql`)

| Table | Purpose | Key |
|-------|---------|-----|
| `users` | Device registry | `device_id` (text PK) |
| `preferences` | User preferences | `device_id` FK → users |
| `logs` | Venue visit history | `id` (text PK), `device_id` FK |
| `venues` | Venue catalog | `(name, area)` unique |
| `events` | Venue events | `venue_id` FK → venues |
| `sources` | iCal source registry | `(area_slug, url)` unique |
| `area_discovery` | Discovery tracking | `area_slug` PK |

**RLS**: Permissive for MVP (all reads/writes allowed). The `sources` and `area_discovery` tables restrict writes to Edge Functions using the service role key.

### Edge Function (`supabase/functions/sources/index.ts`)

Single Deno function with four actions (POST body `{ action: "..." }`):

| Action | Purpose | Input |
|--------|---------|-------|
| `proxy` | CORS-bypass .ics fetch | `{ url }` |
| `discover` | Rule-based probe + LLM discovery | `{ area_label }` |
| `add` | User-submitted feed (validates before saving) | `{ area_label, name, url, default_category, contributed_by }` |
| `list` | Read verified sources for an area | `{ area_label }` |

**Deploy:**
```bash
supabase functions deploy sources
supabase secrets set ANTHROPIC_API_KEY=sk-ant-...
```

## UI & Theme

Dark mode throughout. Color palette (`src/theme.ts`):

| Token | Hex | Usage |
|-------|-----|-------|
| `bg` | `#0e1116` | Screen background |
| `card` | `#171c24` | Card surfaces |
| `cardAlt` | `#1f2530` | Secondary surfaces, locked badges |
| `border` | `#2a313d` | Card borders |
| `text` | `#f4f6fa` | Primary text |
| `textDim` | `#9aa3b2` | Secondary text, labels |
| `accent` | `#4f8cff` | Buttons, links, active chips |
| `go` | `#30c67c` | GO decision badge (green) |
| `maybe` | `#f0b541` | MAYBE decision badge (yellow) |
| `skip` | `#ef5b5b` | SKIP decision badge (red) |

Spacing: `xs=4, sm=8, md=16, lg=24, xl=32`. Border radius: `md=12, lg=16`.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | React Native 0.81 + Expo 54 |
| Router | Expo Router 6 (file-based) |
| Language | TypeScript 5.9 |
| State | React Context + AsyncStorage |
| Backend | Supabase (Postgres + Edge Functions on Deno) |
| Styling | React Native StyleSheet (no external UI library) |

## Not in MVP

These are explicitly out of scope for the current version:

- **Authentication** — device-ID based identity only, no sign-up/login
- **Real payments** — plan toggle is a mock; no Stripe/RevenueCat
- **Chat / messaging** — no user-to-user communication
- **User matching** — no dating algorithm or profile matching
- **Maps integration** — no map view or directions
- **Web scraping** — iCal feeds only, no HTML parsing
- **Push notifications** — no alerts for new events
- **Analytics** — no usage tracking or dashboards
- **Multi-city expansion** — hardcoded to North County SD

## Roadmap

1. **Authentication** — Supabase Auth (email/magic link) to replace device-ID
2. **Payment processing** — Stripe or RevenueCat for paid plan subscription
3. **Deploy Edge Function** — set `ANTHROPIC_API_KEY` for LLM-based source discovery
4. **Venue data expansion** — crowd-source venues via user logs, expand beyond SD
5. **App store submission** — Apple App Store + Google Play
6. **Push notifications** — daily "Tonight's pick" notification
7. **Scoring refinements** — incorporate visit log feedback (crowd grade, would-go-again) into future scores
