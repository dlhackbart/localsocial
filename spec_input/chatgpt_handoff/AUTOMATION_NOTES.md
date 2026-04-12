# AUTOMATION_NOTES.md

## Why this add-on exists
The original Claude package did not include the user's active reminder / notification workflow.

This add-on corrects that.

## Missing behaviors now captured
This add-on adds specification for:

1. Morning Social Plan reminder (8:00 AM)
2. Afternoon go-time reminder (4:00 PM)
3. "No events today." logic
4. Nightly venue logging prompt
5. Updated terminology:
   - use **Social Plan**
   - do not use **Dating Plan** in reminder output

## Implementation Guidance
Claude should integrate this into the existing Local Social project without replacing the current architecture.

These behaviors may be implemented as:
- local scheduled notifications inside the app
- a server-driven daily plan generator
- or internal app reminder logic

## Important product nuance
Even though the app may support dating-oriented goals internally, reminder copy should remain broadly framed as:
- social
- local
- practical
- decision support

## Merge Guidance for Claude
Claude should:
- read these add-on files
- preserve the existing app foundation
- integrate the schedule behavior cleanly
- keep the wording consistent with the broader Local Social positioning
