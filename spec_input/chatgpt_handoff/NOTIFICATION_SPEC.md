# NOTIFICATION_SPEC.md

## Purpose
This add-on defines the reminder and notification behavior for the existing Local Social app/project.

This is an add-on only. It is meant to be merged into an existing Claude Code Local Social project.

## Terminology
Use **Social Plan**, not **Dating Plan**.

## Notification Schedule
The system should support:

### 1. Morning planning notification
- Time: **8:00 AM local time**
- Purpose: early awareness so the user can factor the plan into the day

### 2. Afternoon go-time notification
- Time: **4:00 PM local time**
- Purpose: final nudge / decision support

### 3. Optional nightly logging reminder
- Suggested time: **9:30 PM local time**
- Purpose: ask the user whether they went out and capture quick feedback

## Daily Social Plan Logic
Each day, the system should generate a brief **Social Plan** for that date.

If there are no worthwhile events or venue options for the day, it must clearly say:

**No events today.**

Do not force weak recommendations just to fill space.

## Required Morning / Afternoon Output Structure
When an event day is worthwhile, the generated Social Plan should include:

1. Best event option for tonight with exact time
2. Backup option with time
3. Live music lineup for each recommended venue tonight, especially:
   - Belly Up
   - Monarch
   - Del Mar Plaza
   when applicable
4. A simple:
   - GO
   - MAYBE
   - SKIP
5. Crowd-quality grade:
   - A
   - B
   - C
6. Whether tonight is a:
   - High-priority night
   - Medium-priority night
   - Low-priority night
7. Short weather / turnout note if useful

## Weekly Base Structure
Use this as the base weekly rhythm:

- Thursday:
  - Del Mar Plaza Seaside Sessions 5–7 PM
  - top priority recurring night

- Saturday:
  - Del Mar Plaza Seaside Sessions 5–7 PM
  - strong repeat option

- Wednesday / Friday / Sunday:
  - Monarch roughly 3–7 PM
  - rotation / repeat-friendly option

- Sunday:
  - Cedros can be used as an optional social add

- Belly Up:
  - special-value venue
  - depends on lineup
  - should be used when the show materially improves the night

- Community / wine / art walk / concert events:
  - special-value nights when relevant

## Day-Accuracy Requirement
The system must always use the actual calendar day being evaluated.

Example:
- If today is Monday and nothing strong is scheduled, output:
  **No events today.**

Do not accidentally reuse Sunday logic on Monday.

## Wording and Tone
Keep output:
- concise
- practical
- action-oriented
- calm
- adult

Avoid language that makes the product feel like a swipe-based dating app.
