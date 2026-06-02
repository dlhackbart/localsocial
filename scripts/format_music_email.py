"""
Local Social — format the weekly live-music reminder.

Layout (operator spec):
  1. LIVE MUSIC THIS WEEK  — music first, chronological by day, Del Mar -> Oceanside,
     each line tagged with a confidence marker (✅ / ~ / ⚠).
  2. REMINDERS             — the usual everyday spots, grouped by area.
  3. Source key            — what each marker means.

  format_music_email(week) -> full plain-text body (email; MMS gateway too).
  format_music_sms(week)   -> condensed music-only body for the daily text.
"""

from datetime import date, datetime

# South -> north, so the email reads down the coast.
AREA_ORDER = ["Del Mar", "Solana Beach", "Cardiff", "Encinitas", "Carlsbad", "Oceanside"]
RULE = "─" * 44
RULE2 = "═" * 44
ARTIST_MAX = 76


def _day_header(iso: str) -> str:
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.strftime('%a').upper()} {d.strftime('%b')} {d.day}"


def _trim(s: str, n: int = ARTIST_MAX) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _music_line(ev: dict) -> str:
    """'✅ 8 PM   Belly Up (Solana Beach) — Allah-Las'  (+ stream/genre when present)."""
    venue = ev["venue"]
    if ev.get("stream"):
        venue += f" · {ev['stream'].lower()}"
    artist = _trim(ev.get("artist", ""))
    if ev.get("genre"):
        artist += f" ({ev['genre']})"
    time = (ev.get("start") or "").rjust(7)
    return f"  {ev['marker']} {time}  {venue} ({ev['city']}) — {artist}"


def _group_by_day(events: list[dict]) -> dict[str, list[dict]]:
    days: dict[str, list[dict]] = {}
    for ev in sorted(events, key=lambda e: (e["date"], e.get("start", ""))):
        days.setdefault(ev["date"], []).append(ev)
    return days


def format_music_email(week: dict) -> str:
    events = week.get("events", [])
    lines: list[str] = []
    lines.append("🎵 LIVE MUSIC THIS WEEK — Del Mar → Oceanside")

    week_of = week.get("week_of", "")
    try:
        wo = datetime.strptime(week_of, "%Y-%m-%d")
        sub = f"Week of {wo.strftime('%b')} {wo.day}"
    except ValueError:
        sub = "This week"
    gen = week.get("generated_at", "")[:10]
    if gen:
        sub += f" · refreshed {gen}"
    lines.append(sub)
    lines.append(RULE2)

    if week.get("_stale"):
        lines.append(f"⚠ This lineup is {week.get('_age_days','?')} days old — "
                     f"the weekly refresh may not have run. Double-check before relying on it.")
        lines.append(RULE)

    if not events:
        lines.append("No live music found for the week. (Sources may be down — verify before relying.)")
    else:
        for iso, evs in _group_by_day(events).items():
            lines.append("")
            lines.append(_day_header(iso))
            lines.extend(_music_line(ev) for ev in evs)

    # ── Reminders ──
    reminders = week.get("reminders", [])
    if reminders:
        lines.append("")
        lines.append(RULE)
        lines.append("📍 REMINDERS — the usual spots")
        by_area: dict[str, list[dict]] = {}
        for r in reminders:
            by_area.setdefault(r["area"], []).append(r)
        ordered = [a for a in AREA_ORDER if a in by_area] + \
                  [a for a in by_area if a not in AREA_ORDER]
        for area in ordered:
            lines.append("")
            lines.append(area.upper())
            for r in by_area[area]:
                lines.append(f"  • {r['venue']} — {r['summary']}")

    # ── Legend ──
    lines.append("")
    lines.append(RULE)
    lines.append("Source key:")
    lines.append("  ✅ scraped straight from the venue — rely on it")
    lines.append("  ~  from a local listing/aggregator — worth a glance")
    lines.append("  ⚠  unverified — double-check before you go")
    lines.append("Reply with fixes anytime and I'll fold them in.")
    return "\n".join(lines)


def format_music_sms(week: dict) -> str:
    """Condensed music-only view for the daily text (no reminders/legend)."""
    events = week.get("events", [])
    lines = ["🎵 Live music this week (Del Mar→Oceanside):"]
    if week.get("_stale"):
        lines.append(f"⚠ lineup {week.get('_age_days','?')}d old — verify")
    if not events:
        lines.append("none found — sources may be down")
        return "\n".join(lines)
    for iso, evs in _group_by_day(events).items():
        d = datetime.strptime(iso, "%Y-%m-%d")
        picks = "; ".join(
            f"{_trim(e['artist'], 28)} @ {e['venue'].split(' · ')[0]} {e.get('start','')}"
            for e in evs[:3]
        )
        extra = f" +{len(evs) - 3} more" if len(evs) > 3 else ""
        lines.append(f"{d.strftime('%a')} {d.strftime('%b')}{d.day}: {picks}{extra}")
    return "\n".join(lines)
