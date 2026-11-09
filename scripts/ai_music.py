"""
Local Social — AI layer for the live-music reminder (Claude Code subscription only).

Two jobs, both driven by data/taste.json:

  pick_this_week(events)  -> the few local shows this week he'd most enjoy, each with
                             a one-line reason. Claude chooses BY INDEX from the
                             scraped list, so it can never invent a show.

  refresh_big_shows()     -> data/big_shows.json: bigger concerts up to ~4 months out,
                             so tickets can be bought early. Two sources:
                               1. Belly Up / The Sound / Fairgrounds, scraped directly
                                  with a long lookahead (✅, always kept for The Sound /
                                  Fairgrounds concerts — half a mile from home).
                               2. A Claude web-search scout of the big San Diego rooms.
                                  Every scouted show must give a URL whose page names
                                  the artist, or it is dropped (~ when kept).
                             Then Claude ranks the combined list for his taste.
                             `first_seen` per show lets the email lead with what was
                             just announced.

Every failure degrades to "no AI section" — the plain lineup always still sends.
"""

import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from claude_cli import ask_claude_json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TASTE_FILE = DATA_DIR / "taste.json"
BIG_SHOWS_FILE = DATA_DIR / "big_shows.json"

PT = ZoneInfo("America/Los_Angeles")
BIG_SHOWS_REFRESH_DAYS = 3   # announcements land mid-week; re-scout twice a week
NEW_FOR_DAYS = 7             # "just announced" = first seen within a week
WEEK_PICKS = 5
BIG_SHOW_LIMIT = 20


def _today() -> date:
    return datetime.now(PT).date()


def load_taste() -> dict:
    try:
        return json.loads(TASTE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"home": "Del Mar, CA", "likes": [], "big_show_venues": [], "big_show_days": 120}


def _likes(taste: dict) -> str:
    return "; ".join(taste.get("likes") or []) or "live music in general"


# ─── This week's picks ───────────────────────────────────────────────────────

def pick_this_week(events: list[dict]) -> list[dict]:
    """Return [{'event': ev, 'why': str}] — at most WEEK_PICKS, best first."""
    if not events:
        return []
    taste = load_taste()
    listing = "\n".join(
        f"{i}. {e['date']} ({e.get('day', '')[:3]}) {e.get('start', '')} — {e.get('artist', '')}"
        f" @ {e['venue']} ({e.get('city', '')}){' — ' + e['description'] if e.get('description') else ''}"
        for i, e in enumerate(events)
    )
    prompt = f"""You pick live music for one person who lives in {taste.get('home', 'Del Mar, CA')}.
He likes: {_likes(taste)}.

Below are this week's local shows, numbered. Choose up to {WEEK_PICKS} he would most enjoy.
Use what you know about the artists (a band name you recognize, a genre a tribute or
cover band plays). Prefer real draws over background bar sets. Skip non-music events.
If nothing fits, return [].

Return ONLY a JSON array, best first, of objects:
  {{"i": <number from the list>, "why": "<one short line, under 80 characters>"}}

--- SHOWS ---
{listing}
"""
    picked = ask_claude_json(prompt, timeout=240)
    if not picked:
        return []
    out, seen = [], set()
    for p in picked:
        if not isinstance(p, dict):
            continue
        i = p.get("i")
        if not isinstance(i, int) or not (0 <= i < len(events)) or i in seen:
            continue
        seen.add(i)
        out.append({"event": events[i], "why": str(p.get("why", "")).strip()[:100]})
        if len(out) >= WEEK_PICKS:
            break
    return out


# ─── Big shows, months ahead ─────────────────────────────────────────────────

def _key(artist: str, d: str) -> str:
    """Headliner + date. Belly Up writes "Houndmouth - The LORDY Tour w/ Dogpark" for the
    show The Sound calls "Houndmouth", so tour names and openers are cut first."""
    core = re.split(r"\s+-\s+|\s+w/|\s+with\s+|,|\s+\+\s+", artist.lower(), maxsplit=1)[0]
    return f"{re.sub(r'[^a-z0-9]', '', core)[:40]}|{d}"


# On a collision the more specific venue wins: The Sound is booked by Belly Up and
# often listed on Belly Up's calendar too, but it is its own room at the Fairgrounds.
_VENUE_PRIORITY = {"The Sound": 0}


def _direct_big_shows(horizon: int) -> list[dict]:
    """Belly Up + The Sound + Fairgrounds, scraped directly with a long lookahead."""
    import scrape_events as se
    from scrape_music import _clean, _strip_section

    saved = se.LOOKAHEAD_DAYS
    se.LOOKAHEAD_DAYS = horizon
    shows: list[dict] = []
    try:
        try:
            for ev in se.scrape_belly_up():
                shows.append({"artist": _clean(ev.get("title", "")), "venue": "Belly Up",
                              "city": "Solana Beach", "date": ev.get("date", ""),
                              "time": ev.get("time", ""), "url": "https://www.bellyup.com/calendar/",
                              "marker": "✅", "always": False})
        except Exception as e:  # noqa: BLE001
            print(f"[BIG] Belly Up failed: {e}")
        try:
            for ev in se.scrape_fairgrounds():
                # The feed tags non-concerts (a holiday tree lot, expos) as music, so only
                # The Sound is kept unconditionally; the rest must earn a spot on taste.
                venue = _clean(ev.get("venue", "Del Mar Fairgrounds"))
                shows.append({"artist": _strip_section(_clean(ev.get("title", ""))), "venue": venue,
                              "city": "Del Mar", "date": ev.get("date", ""), "time": ev.get("time", ""),
                              "url": ev.get("source") or "https://www.delmarfairgrounds.com/events",
                              "marker": "✅", "always": venue == "The Sound"})
        except Exception as e:  # noqa: BLE001
            print(f"[BIG] Fairgrounds failed: {e}")
    finally:
        se.LOOKAHEAD_DAYS = saved
    return shows


def _artist_word(artist: str) -> str:
    words = sorted(re.findall(r"[a-z0-9']{4,}", artist.lower()), key=len, reverse=True)
    return words[0] if words else ""


def _confirm(url: str, artist: str) -> str | None:
    """How far a scouted show checks out: '~' its page names the artist; '⚠' the page
    blocks automated reads (ticket sites do) but the link itself names the artist;
    None = not confirmed, drop it."""
    from scrape_music import _fetch
    if not url.startswith("http"):
        return None
    word = _artist_word(artist)
    page = _fetch(url)
    if page:
        text = re.sub(r"\s+", " ", page).lower()
        return "~" if artist.lower() in text or (word and word in text) else None
    slug = re.sub(r"[^a-z0-9']", "", url.lower())
    return "⚠" if word and word in slug else None


def _scout_big_shows(taste: dict, horizon: int) -> list[dict]:
    """Claude searches the web for bigger shows that fit; each must check out on its page."""
    today = _today()
    until = today + timedelta(days=horizon)
    venues = "\n".join(f"  - {v}" for v in taste.get("big_show_venues") or [])
    prompt = f"""Find upcoming concerts in San Diego County between {today.isoformat()} and {until.isoformat()}
that a fan of {_likes(taste)} would want to buy tickets for early.

Search these venues' own calendars and ticket pages (use web search and fetch the pages):
{venues}

Rules:
  - Only shows you SAW on a page during this search. Never rely on memory.
  - Bigger acts worth planning around: touring headliners, well-known names, festivals.
  - Skip tribute nights at bars, comedy, sports, and anything already past.
  - "url" must be the page that lists the show (venue event page or ticket page).

Return ONLY a JSON array (max 25) of objects:
  {{"artist": "...", "venue": "...", "city": "...", "date": "YYYY-MM-DD",
    "on_sale": "date tickets go on sale if shown, else \\"\\"", "url": "https://...",
    "why": "<one short line on why he'd like it>"}}
"""
    found = ask_claude_json(prompt, timeout=1200, model="sonnet",
                            tools=["WebSearch", "WebFetch"])
    if not found:
        return []
    out = []
    for s in found:
        if not isinstance(s, dict):
            continue
        artist, d, url = str(s.get("artist", "")).strip(), str(s.get("date", "")), str(s.get("url", ""))
        try:
            dd = date.fromisoformat(d)
        except ValueError:
            continue
        if not artist or not (today <= dd <= until):
            continue
        marker = _confirm(url, artist)
        if not marker:
            print(f"[BIG] dropped (link doesn't confirm): {artist} @ {s.get('venue')} {d}")
            continue
        out.append({"artist": artist, "venue": str(s.get("venue", "")), "city": str(s.get("city", "")),
                    "date": d, "time": "", "url": url, "on_sale": str(s.get("on_sale", "")),
                    "why": str(s.get("why", ""))[:100], "marker": marker, "always": False})
    return out


def _rank_for_taste(shows: list[dict], taste: dict) -> dict[int, str]:
    """Claude picks which shows he'd want tickets for. Returns {index: why}."""
    if not shows:
        return {}
    listing = "\n".join(f"{i}. {s['date']} — {s['artist']} @ {s['venue']} ({s['city']})"
                        for i, s in enumerate(shows))
    prompt = f"""One person in {taste.get('home', 'Del Mar, CA')} likes: {_likes(taste)}.
From these upcoming concerts, choose up to {BIG_SHOW_LIMIT} he'd most want to buy tickets
for early. Use what you know about each act. Return ONLY a JSON array, best first:
  {{"i": <number>, "why": "<one short line, under 80 characters>"}}

{listing}
"""
    ranked = ask_claude_json(prompt, timeout=300)
    out: dict[int, str] = {}
    for r in ranked or []:
        if isinstance(r, dict) and isinstance(r.get("i"), int) and 0 <= r["i"] < len(shows):
            out.setdefault(r["i"], str(r.get("why", ""))[:100])
    return out


def load_big_shows() -> dict | None:
    try:
        return json.loads(BIG_SHOWS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def refresh_big_shows(force: bool = False, verbose: bool = True) -> dict | None:
    """Rebuild data/big_shows.json if it is older than BIG_SHOWS_REFRESH_DAYS (or forced)."""
    prev = load_big_shows()
    today = _today()
    if prev and not force:
        try:
            age = (today - date.fromisoformat(prev.get("generated_at", "")[:10])).days
        except ValueError:
            age = 999
        if age < BIG_SHOWS_REFRESH_DAYS:
            return prev

    taste = load_taste()
    horizon = int(taste.get("big_show_days") or 120)
    week_end = today + timedelta(days=7)  # this week's shows are in the weekly lineup already

    direct = _direct_big_shows(horizon)
    scouted = _scout_big_shows(taste, horizon)
    if verbose:
        print(f"[BIG] direct {len(direct)} · scouted+verified {len(scouted)}")

    merged: dict[str, dict] = {}
    for s in direct + scouted:   # direct first, so ✅ wins a collision
        try:
            dd = date.fromisoformat(s["date"])
        except ValueError:
            continue
        if dd <= week_end:
            continue
        k = _key(s["artist"], s["date"])
        cur = merged.get(k)
        if cur is None or _VENUE_PRIORITY.get(s["venue"], 9) < _VENUE_PRIORITY.get(cur["venue"], 9):
            merged[k] = s
    # A run of the same title at one venue (a month-long tree lot, a residency) is one
    # entry, at its first date.
    shows, seen_runs = [], set()
    for s in sorted(merged.values(), key=lambda s: s["date"]):
        run = (s["venue"], re.sub(r"[^a-z0-9]", "", s["artist"].lower()))
        if run in seen_runs:
            continue
        seen_runs.add(run)
        shows.append(s)

    ranked = _rank_for_taste(shows, taste)
    if not ranked and not scouted:
        # Claude was unreachable: keep the last good list rather than show nothing.
        if prev:
            print("[BIG] AI unavailable — keeping the previous list")
            return prev
    keep = []
    for i, s in enumerate(shows):
        if i in ranked:
            s["why"] = ranked[i] or s.get("why", "")
            s["rank"] = list(ranked).index(i)
            keep.append(s)
        elif s.get("always"):
            s["rank"] = 999
            keep.append(s)

    # The very first run has nothing to compare against, so nothing is "just announced".
    first_seen = (prev or {}).get("first_seen", {})
    stamp = today.isoformat() if prev else ""
    for s in keep:
        s["first_seen"] = first_seen.setdefault(_key(s["artist"], s["date"]), stamp)
    # forget shows that have passed
    first_seen = {k: v for k, v in first_seen.items() if k.split("|")[-1] >= today.isoformat()}

    payload = {
        "generated_at": datetime.now(PT).isoformat(timespec="seconds"),
        "horizon_days": horizon,
        "shows": sorted(keep, key=lambda s: s["date"]),
        "first_seen": first_seen,
    }
    BIG_SHOWS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"[BIG] wrote {BIG_SHOWS_FILE.name} — {len(keep)} shows")
    return payload


def is_new(show: dict) -> bool:
    try:
        return (_today() - date.fromisoformat(show.get("first_seen", ""))).days < NEW_FOR_DAYS
    except ValueError:
        return False


if __name__ == "__main__":
    refresh_big_shows(force="--force" in sys.argv)
