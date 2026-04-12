# LOGGING_SPEC.md

## Purpose
Defines the nightly venue check-in behavior for the existing Local Social project.

## Suggested Reminder Time
- **9:30 PM local time**

## Prompt Wording
Ask the user:

**Did you go out tonight?**

If yes, ask:

1. Which venue did you go to?
   - Del Mar Plaza
   - Monarch
   - Belly Up
   - Cedros
   - community event
   - other

2. How was the crowd quality?
   - A
   - B
   - C

3. Would you go back soon?
   - yes
   - maybe
   - no

## Purpose of Log Data
This log should later support:
- venue rotation awareness
- stronger recommendations over time
- better prioritization of repeat-friendly venues
- better understanding of what actually works for the user

## Minimum Data Fields
Suggested stored fields:

- date
- wentOut (boolean)
- venue (string)
- crowdGrade (A/B/C)
- wouldReturnSoon (yes/maybe/no)

## UX Notes
Keep the nightly check-in very short.
It should feel easy enough to answer in under 10 seconds.
