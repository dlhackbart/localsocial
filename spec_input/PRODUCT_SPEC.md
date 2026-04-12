# Local Social — FULL PRODUCT SPEC

## Core
Local Social is a local social decision app that answers:
"Where should I go tonight?"

Not a dating app publicly, but optimizes for connection (including dating) internally.

## Inputs
- Location (ZIP/address → city)
- Nearby social zones (curated, not radius)
- Goal: Dating / Social / Both
- Vibe: Quiet / Balanced / High Energy

## Output
- Primary venue
- Backup venue
- Time + lineup
- Grade: A/B/C
- Decision: GO / MAYBE / SKIP
- Reason

If nothing:
→ "No events today."

## Scoring (rules-based)
score = 0
+5 event tonight
+3 high energy (if social)
+3 conversation-friendly (if dating)
+2 repeat-friendly
+2 broad appeal
-3 low social value

Grades:
8+ A
5–7 B
<5 C

## Goals
Dating:
- repeat venues
- conversation
- local crowd

Social:
- energy
- events
- density

Both:
- blend

## Venues (examples)
- Belly Up: event-driven, high energy
- Monarch: repeat, conversational
- Del Mar Plaza: anchor hybrid
- Cedros: walkable, conversational

## MVP RULES
- Keep simple
- Use static data first
- No scraping initially
- No chat, no matching

## Pricing
Free: 1/week
Paid: $12.99/month daily