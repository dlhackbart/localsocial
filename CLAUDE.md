# Local Social — Developer Guide

## What This Is

React Native (Expo 54) MVP for a local venue/event recommendation app targeting San Diego North County. Answers "Where should I go tonight?" with scored, goal-aware recommendations.

## Run

```bash
npm install
npm start          # Expo Go
npm run ios        # iOS sim
npm run web        # Browser (limited — iCal CORS)
```

## Key Files

| File | Purpose |
|------|---------|
| `src/scoring.ts` | Recommendation engine — all scoring logic lives here |
| `src/types.ts` | Every TypeScript interface and type union |
| `src/data/venues.ts` | 12 static venues with weekly events |
| `src/data/events.ts` | 25+ sample events (seeded, projected to current week) |
| `src/data/areas.ts` | Area adjacency graph (4 areas) |
| `src/events/ical.ts` | iCalendar parser (RFC5545 subset) |
| `src/events/resolver.ts` | 3-tier source resolution: local → Supabase → discovery |
| `src/events/store.ts` | Event fetch + 6hr cache + merge with samples |
| `src/events/sources.ts` | Hardcoded iCal source list |
| `src/store/preferences.tsx` | PreferencesContext (AsyncStorage + Supabase sync) |
| `src/store/subscription.tsx` | SubscriptionContext (free/paid reveal gating) |
| `src/store/logs.ts` | Visit log persistence (local + Supabase) |
| `src/supabase/client.ts` | Supabase client init + device ID |
| `src/theme.ts` | Dark mode colors, spacing, radius |
| `supabase/schema.sql` | Full Postgres schema (7 tables) |
| `supabase/functions/sources/index.ts` | Edge Function (proxy, discover, add, list) |

## Screens (Expo Router)

| Route | File | Description |
|-------|------|-------------|
| `/` (Tonight tab) | `app/(tabs)/index.tsx` | Main screen — top event + top venue cards, reveal gate |
| `/log` | `app/(tabs)/log.tsx` | Venue visit logging form + history |
| `/profile` | `app/(tabs)/profile.tsx` | Settings summary, plan toggle, links |
| `/preferences` (modal) | `app/preferences.tsx` | Area, zones, goal, vibe, category selection |
| `/add-source` (modal) | `app/add-source.tsx` | User iCal feed submission |

## Scoring Quick Reference

Venue: `+5 event` `+3 energy(social)` `+3 convo(dating)` `+2 repeat` `+2 broad` `-3 lowSocial` `-2 vibeMismatch` `-2 datingNoRepeat` `-2 datingNoConvo`

Event: `+5 exists` `+2 intimate` `+3 convo(dating)` `+2 repeat` `+1 broad` `-1 datingNoRepeat` `-1 quietNotIntimate`

Grade: `8+=A(GO)` `5-7=B(MAYBE)` `<5=C(SKIP)`

## Data Flow

```
User opens Tonight tab
  → loadEvents(homeArea)
    → check AsyncStorage cache (6hr TTL)
    → if miss: resolveSourcesForArea(area)
      → local sources (hardcoded)
      → Supabase sources table
      → Edge Function discover (probe + LLM) [first time only]
    → fetch each source (.ics via proxy or direct)
    → parseICal() → LocalEvent[]
    → merge + dedupe with getSampleEvents()
    → cache to AsyncStorage
  → getRecommendations(prefs, events)
    → filter by area, day, time, categories
    → score each venue event + each local event
    → sort by score, return top of each
  → render locked/unlocked cards based on subscription state
```

## Supabase (Optional)

Without `.env` vars, the app runs fully local (AsyncStorage only, sample events only). With Supabase:

- Preferences and logs sync to server
- iCal sources are discovered and shared across users
- Edge Function provides CORS proxy for .ics fetches

**Edge Function actions** (POST to `sources`):
- `proxy` — fetch .ics URL server-side (CORS bypass)
- `discover` — rule-based probe (~50 URL patterns) + Claude Haiku LLM
- `add` — user-submitted feed (validates .ics before saving)
- `list` — return verified sources for an area

## State Management

All state uses React Context + AsyncStorage. No Redux, no Zustand.

| Context | Provider | Storage Key |
|---------|----------|-------------|
| Preferences | `PreferencesProvider` | `localsocial:prefs:v2` |
| Subscription | `SubscriptionProvider` | `localsocial:sub:v1` |
| Logs | (direct functions) | `localsocial:logs:v1` |
| Events cache | (direct functions) | `localsocial:events:v2` |
| Device ID | (direct function) | `localsocial:device_id:v1` |

## Categories

12 event categories: `hiking_outdoor`, `classes_workshops`, `community_civic`, `live_music_small`, `art_galleries`, `food_drink`, `book_clubs`, `markets`, `theater_small`, `movies_indie`, `meetups_clubs`, `wellness`

## Daily Social Plan & Notifications

Three-touch daily cadence (previously run as ChatGPT scheduled tasks, needs native implementation):

| Time | Purpose | Status |
|------|---------|--------|
| 8:00 AM | Morning Social Plan (tonight's picks) | NOT BUILT |
| 4:00 PM | Go-Time reminder (final nudge) | NOT BUILT |
| 9:30 PM | Nightly log prompt | UI DONE (Log tab), notification NOT BUILT |

**Terminology:** Always "Social Plan", never "Dating Plan"
**Empty days:** Say "No events today." — don't force weak recs
**Format:** Primary + Backup option, venue notes, Call (GO/MAYBE/SKIP), Crowd Grade (A/B/C), Priority Level (High/Medium/Low)
**Full specs:** `spec_input/chatgpt_handoff/` (NOTIFICATION_SPEC.md, DAILY_PLAN_TEMPLATE.md, LOGGING_SPEC.md, AUTOMATION_NOTES.md)

## Current Status

**MVP complete.** All screens functional, scoring engine working, iCal pipeline wired, subscription gating in place (mock payments).

**Not implemented:** Daily Social Plan notifications (was running in ChatGPT), real auth, real payments, push notifications, maps, chat, matching, multi-city.

## Conventions

- TypeScript strict throughout
- No external UI library — React Native StyleSheet only
- Dark theme colors from `src/theme.ts`
- Supabase calls are always null-safe (`if (!supabase) return`)
- All async errors are caught silently in non-critical paths (sync, cache)
- Expo Router file-based routing with typed routes enabled
