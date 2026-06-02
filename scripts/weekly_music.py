"""
Local Social — weekly music cache.

The lineup only changes once a week, so we scrape ONCE (Monday) into
data/weekly_music.json and the daily late-afternoon reminder just reads that
file. Keeps a dated backup so a bad scrape can't destroy a good week's data.

  build_weekly_music()  -> scrape, write weekly_music.json (+ backup), return dict
  load_weekly_music()   -> read weekly_music.json (with staleness flag)
  build_reminders()     -> the "usual spots" list, from daily_social_plan.VENUES
"""

import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrape_music import scrape_all_music  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
WEEKLY_FILE = DATA_DIR / "weekly_music.json"
BACKUP_DIR = DATA_DIR / "weekly_music_backups"

PT = ZoneInfo("America/Los_Angeles")
STALE_AFTER_DAYS = 8  # a weekly file older than this is flagged loudly in the email

_DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DAY_ABBR = {d: d[:3] for d in _DAY_ORDER}


# ─── Reminders ("the usual spots") ──────────────────────────────────────────

def _abbrev_days(days: list[str]) -> str:
    """['Monday'..'Friday'] -> 'Mon–Fri'; non-contiguous -> 'Tue/Thu/Sat'."""
    idx = sorted({_DAY_ORDER.index(d) for d in days if d in _DAY_ORDER})
    if not idx:
        return ""
    runs, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i == prev + 1:
            prev = i
            continue
        runs.append((start, prev))
        start = prev = i
    runs.append((start, prev))
    parts = []
    for a, b in runs:
        if a == b:
            parts.append(_DAY_ABBR[_DAY_ORDER[a]])
        elif b == a + 1:
            parts.append(f"{_DAY_ABBR[_DAY_ORDER[a]]}/{_DAY_ABBR[_DAY_ORDER[b]]}")
        else:
            parts.append(f"{_DAY_ABBR[_DAY_ORDER[a]]}–{_DAY_ABBR[_DAY_ORDER[b]]}")
    return "/".join(parts) if all(a == b for a, b in runs) else " ".join(parts)


def _short_time(t: str) -> str:
    """'3:00 PM' -> '3', '4:30 PM' -> '4:30' (drop :00 and the meridiem for ranges)."""
    return (t or "").replace(":00", "").replace(" PM", "").replace(" AM", "").strip()


def build_reminders() -> list[dict]:
    """The everyday 'usual places', summarized one line each, grouped-ready by area."""
    from daily_social_plan import VENUES  # local import; stdlib-only module, safe

    reminders = []
    for v in VENUES:
        bits = []
        hh = v.get("happyHour")
        if hh and hh.get("days"):
            days = _abbrev_days(hh["days"])
            bits.append(f"HH {days} {_short_time(hh['start'])}–{_short_time(hh['end'])}")
        # Highlight a couple of recurring events (music/standing nights first).
        evs = v.get("events", [])
        highlights = []
        for ev in evs:
            t = ev.get("type", "")
            highlights.append(f"{t} {_DAY_ABBR.get(ev.get('day',''), ev.get('day',''))}")
        if highlights:
            bits.append("; ".join(highlights[:3]))
        reminders.append({
            "venue": v["name"],
            "area": v["area"],
            "summary": " · ".join(bits) if bits else "neighborhood spot",
        })
    return reminders


# ─── Build / load the weekly cache ──────────────────────────────────────────

def _week_of() -> str:
    """Monday of the current PT week, ISO date."""
    today = datetime.now(PT).date()
    return (today.fromordinal(today.toordinal() - today.weekday())).isoformat()


def build_weekly_music(verbose: bool = True) -> dict:
    """Scrape all sources, assemble the weekly payload, write JSON + dated backup."""
    events, report = scrape_all_music(verbose=verbose)
    payload = {
        "week_of": _week_of(),
        "generated_at": datetime.now(PT).isoformat(timespec="seconds"),
        "source_report": report,
        "events": events,
        "reminders": build_reminders(),
    }

    # Back up the previous good file before overwriting (never destroy a good week).
    if WEEKLY_FILE.exists():
        BACKUP_DIR.mkdir(exist_ok=True)
        try:
            prev = json.loads(WEEKLY_FILE.read_text(encoding="utf-8"))
            stamp = prev.get("generated_at", "unknown").replace(":", "").replace("-", "")
        except (json.JSONDecodeError, OSError):
            stamp = "corrupt"
        shutil.copy2(WEEKLY_FILE, BACKUP_DIR / f"weekly_music_{stamp}.json")

    WEEKLY_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"\n[WEEKLY] wrote {WEEKLY_FILE.relative_to(PROJECT_ROOT)} — "
              f"{len(events)} events, week of {payload['week_of']}")
    return payload


def load_weekly_music() -> dict | None:
    """Read the weekly cache. Adds `_stale` (bool) + `_age_days` for the email banner."""
    if not WEEKLY_FILE.exists():
        return None
    try:
        data = json.loads(WEEKLY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WEEKLY] unreadable: {e}")
        return None
    try:
        gen = datetime.fromisoformat(data.get("generated_at", "")).date()
        age = (datetime.now(PT).date() - gen).days
    except ValueError:
        age = 999
    data["_age_days"] = age
    data["_stale"] = age >= STALE_AFTER_DAYS
    return data


def main():
    build_weekly_music(verbose=True)


if __name__ == "__main__":
    main()
