"""
Local Social — LIVE MUSIC scraper (Del Mar -> Oceanside).

Dedicated music pipeline for the weekly "live music first" reminder. Separate from
the legacy daily scrape_events.py. Every event carries provenance + a confidence
tier so the email can tell the operator what to rely on vs. double-check.

Confirmed Tier-1 sources (server-rendered / JSON, scraped directly — June 2026):
  - Del Mar Plaza   (Tribe REST API)  -> Monarch Ocean Pub INSIDE music
                                          + Ocean View Deck (Seaside Sessions) PATIO music
  - Pour House      (Squarespace JSON) -> Oceanside live music
  - The Kraken      (Tribe REST API)   -> Cardiff live bands
  - Belly Up        (existing scraper) -> Solana Beach touring acts

Tier-3 manual overlay (data/music_manual.json) lets the operator embellish the
known gaps (The Sound, Coyote/Carlsbad bars, Roxy Encinitas, Oceanside Pier,
Brooks Theatre, Belching Beaver) — those show as "unverified" until confirmed.

Usage:
    python scrape_music.py            # scrape all, print summary
    python scrape_music.py --dry-run  # same (no file is written here anyway)
"""

import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
MANUAL_OVERLAY_FILE = DATA_DIR / "music_manual.json"

PT = ZoneInfo("America/Los_Angeles")
LOOKAHEAD_DAYS = 8  # the week ahead + 1 day cushion (the lineup is a weekly view)

# Browser UA — some sources 403 a generic agent.
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Confidence markers surfaced in the email legend.
MARKERS = {"high": "✅", "medium": "~", "low": "⚠"}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Titles that are not actually live music (filtered out of the music section).
_NON_MUSIC = re.compile(
    r"happy hour|free pool|water pong|darts|chill (mon|tues|wednes|thurs|fri|satur|sun)day"
    r"|closed|private event|\btbd\b|trivia|bingo|karaoke|quiz night"
    r"|community market|father'?s day|mother'?s day",
    re.IGNORECASE,
)


def _fetch(url: str, timeout: int = 20) -> str | None:
    """Fetch a URL with a browser UA. Returns text or None on failure."""
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept": "text/html,application/json,application/xhtml+xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001 — caller logs; one dead source must not kill the run
        print(f"[FETCH FAILED] {url}: {e}")
        return None


def _clean(text: str) -> str:
    return html.unescape(text or "").replace(" ", " ").strip()


def _within_window(d: date) -> bool:
    today = date.today()
    return today <= d <= today + timedelta(days=LOOKAHEAD_DAYS)


def _fmt_time(dt: datetime) -> str:
    """4:00 PM -> '4 PM', 5:30 PM -> '5:30 PM'."""
    h = dt.strftime("%I").lstrip("0") or "12"
    if dt.minute:
        return f"{h}:{dt.minute:02d} {dt.strftime('%p')}"
    return f"{h} {dt.strftime('%p')}"


def _event(**kw) -> dict:
    """Build a normalized event dict with confidence marker filled in."""
    kw.setdefault("confidence", "high")
    kw["marker"] = MARKERS.get(kw["confidence"], "~")
    kw.setdefault("stream", None)
    kw.setdefault("end", None)
    kw.setdefault("genre", "")
    kw.setdefault("description", "")
    return kw


# ─── Tribe REST helper (Del Mar Plaza, The Kraken) ───────────────────────────

def _tribe_events(base: str, per_page: int = 100) -> list[dict]:
    """Fetch raw Tribe 'The Events Calendar' REST events for a WordPress site."""
    url = f"{base.rstrip('/')}/wp-json/tribe/events/v1/events?per_page={per_page}"
    body = _fetch(url)
    if not body:
        return []
    try:
        return json.loads(body).get("events", [])
    except json.JSONDecodeError:
        return []


def _tribe_local_dt(raw_ev: dict) -> datetime | None:
    """Tribe `start_date` is venue-local time ('2026-06-03 16:00:00')."""
    s = raw_ev.get("start_date") or ""
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


# ─── Source 1: Del Mar Plaza -> Monarch INSIDE + Ocean View Deck PATIO ────────

def scrape_del_mar_plaza_music() -> list[dict]:
    """Monarch Ocean Pub live music (inside) + Ocean View Deck Seaside Sessions (patio).

    The Del Mar Plaza Tribe calendar labels each event with a `venue`:
      venue == 'Monarch Ocean Pub'  + cat Music  -> the pub's INSIDE live music
      venue == 'Ocean View Deck'    + cat Music  -> Seaside Sessions on the PATIO deck
    Different hours and performers — this is the operator's inside/patio split,
    straight from the source.
    """
    out: list[dict] = []
    for raw in _tribe_events("https://www.delmarplaza.com"):
        cats = [c.get("name", "") for c in raw.get("categories", []) if isinstance(c, dict)]
        if "Music" not in cats:
            continue
        dt = _tribe_local_dt(raw)
        if not dt or not _within_window(dt.date()):
            continue
        end_dt = None
        try:
            end_dt = datetime.strptime(raw.get("end_date", ""), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

        venue_obj = raw.get("venue") or {}
        vname = _clean(venue_obj.get("venue", "")) if isinstance(venue_obj, dict) else ""
        title = _clean(raw.get("title", ""))

        # Split "X – Y – Artist" / "Seaside Sessions – Artist" on en/em dashes & hyphens.
        parts = [p.strip() for p in re.split(r"\s[–—-]\s", title) if p.strip()]
        artist = parts[-1] if len(parts) > 1 else title

        if vname == "Ocean View Deck" or title.lower().startswith("seaside sessions"):
            stream, venue, series = "Patio", "Monarch — Ocean View Deck", "Seaside Sessions"
        else:
            stream, venue, series = "Inside", "Monarch Ocean Pub", "Live Music"

        out.append(_event(
            venue=venue, stream=stream, city="Del Mar", area="Del Mar",
            date=dt.date().isoformat(), day=dt.strftime("%A"),
            start=_fmt_time(dt), end=_fmt_time(end_dt) if end_dt else None,
            artist=artist, genre="", description=series,
            source="delmarplaza.com", source_url=raw.get("url", "https://www.delmarplaza.com/events"),
            tier=1, confidence="high",
        ))
    return out


# ─── Source 2: Pour House Oceanside (Squarespace JSON) ────────────────────────

def scrape_pour_house() -> list[dict]:
    """Oceanside's marquee music room. Squarespace `upcoming[]`, startDate = ms epoch UTC."""
    out: list[dict] = []
    body = _fetch("https://www.pourhouseoceanside.com/events?format=json")
    if not body:
        return out
    try:
        upcoming = json.loads(body).get("upcoming", [])
    except json.JSONDecodeError:
        return out
    for it in upcoming:
        title = _clean(it.get("title", ""))
        if not title or _NON_MUSIC.search(title):
            continue
        start_ms = it.get("startDate")
        if not isinstance(start_ms, (int, float)):
            continue
        dt = datetime.fromtimestamp(start_ms / 1000, tz=ZoneInfo("UTC")).astimezone(PT)
        if not _within_window(dt.date()):
            continue
        # Pull a parenthetical genre/desc out of the title if present.
        genre = ""
        m = re.search(r"\(([^)]+)\)", title)
        if m:
            genre = m.group(1).strip()
            title = re.sub(r"\s*\([^)]+\)", "", title).strip(" ,")
        title = title.rstrip(", ").removesuffix(", Free").strip()
        path = it.get("fullUrl", "")
        out.append(_event(
            venue="Pour House", stream=None, city="Oceanside", area="Oceanside",
            date=dt.date().isoformat(), day=dt.strftime("%A"), start=_fmt_time(dt),
            artist=title, genre=genre, description="",
            source="pourhouseoceanside.com",
            source_url=f"https://www.pourhouseoceanside.com{path}" if path else "https://www.pourhouseoceanside.com/events",
            tier=1, confidence="high",
        ))
    return out


# ─── Source 3: The Kraken, Cardiff (Tribe REST API) ──────────────────────────

def scrape_kraken() -> list[dict]:
    """Cardiff dive-bar live bands. Whole calendar is tagged 'Music'; filter noise by title."""
    out: list[dict] = []
    for raw in _tribe_events("https://krakencardiff.com", per_page=60):
        title = _clean(raw.get("title", ""))
        if not title or _NON_MUSIC.search(title):
            continue
        dt = _tribe_local_dt(raw)
        if not dt or not _within_window(dt.date()):
            continue
        out.append(_event(
            venue="The Kraken", stream=None, city="Cardiff", area="Cardiff",
            date=dt.date().isoformat(), day=dt.strftime("%A"), start=_fmt_time(dt),
            artist=title, genre="", description="",
            source="krakencardiff.com", source_url=raw.get("url", "https://krakencardiff.com"),
            tier=1, confidence="high",
        ))
    return out


# ─── Source 4: Belly Up, Solana Beach (reuse legacy scraper) ─────────────────

def scrape_belly_up_music() -> list[dict]:
    """Marquee touring venue. Reuse the working display-field scraper in scrape_events.py."""
    out: list[dict] = []
    try:
        from scrape_events import scrape_belly_up
    except Exception as e:  # noqa: BLE001
        print(f"[BELLY UP] import failed: {e}")
        return out
    for ev in scrape_belly_up():
        d = ev.get("date", "")
        try:
            day = date.fromisoformat(d).strftime("%A")
        except ValueError:
            continue
        if not _within_window(date.fromisoformat(d)):
            continue
        out.append(_event(
            venue="Belly Up", stream=None, city="Solana Beach", area="Solana Beach",
            date=d, day=day, start=ev.get("time", "8 PM"),
            artist=_clean(ev.get("title", "")), genre="",
            description="Headliner show" if ev.get("big_event") else "",
            source="bellyup.com", source_url="https://www.bellyup.com/calendar/",
            tier=1, confidence="high",
        ))
    return out


# ─── Source 5: Del Mar Fairgrounds + The Sound (reuse legacy API scraper) ─────

# Del Mar Fairgrounds category -> how the music-first email should describe it.
# "The Sound" is its own concert brand (always music); the Fairgrounds proper
# also runs concerts plus non-music slates (County Fair, expos, racing). The
# operator is half a mile away and wants EVERY Fairgrounds event visible weekly
# (esp. weekends) — see memory "Del Mar Fairgrounds + The Sound visibility" — so
# we surface them all, tagging non-music ones with a clear descriptor.
_FAIRGROUNDS_CATEGORY_DESC = {
    "live_music_small": "Concert",
    "markets": "Fair / Expo / Market",
    "meetups_clubs": "Racing / Competition",
}


# A trailing "(Grandstand)" / "(Infield)" etc. is a seating SECTION, not a different
# show — the Fairgrounds API lists the same concert once per section. Strip it so the
# duplicates collapse to one clean listing ("Chicago (Grandstand)" -> "Chicago").
_FG_SECTION_SUFFIX = re.compile(
    r"\s*\((?:grandstand|infield|clubhouse|paddock|surfside race place|"
    r"arena|pavilion|lawn|seating|stage|ga|vip)[^)]*\)\s*$",
    re.IGNORECASE,
)


def _strip_section(name: str) -> str:
    return _FG_SECTION_SUFFIX.sub("", name).strip()


def _range_start(time_str: str) -> str:
    """'8:00 PM - 11:00 PM' -> '8 PM'; '' -> ''. Normalizes via _fmt_time when parseable."""
    head = (time_str or "").split(" - ")[0].strip()
    if not head:
        return ""
    try:
        return _fmt_time(datetime.strptime(head, "%I:%M %p"))
    except ValueError:
        return head


def scrape_fairgrounds_music() -> list[dict]:
    """Del Mar Fairgrounds + The Sound — reuse the live-API scraper in scrape_events.py.

    The Sound is a Belly-Up-booked concert room AT the Fairgrounds; it is kept as a
    distinct venue (never collapsed into the Fairgrounds bucket). Concerts surface as
    live music; the Fairgrounds' non-music slate (County Fair, expos, racing) still
    surfaces per the operator's standing "always show the Fairgrounds" directive, with
    its category spelled out in the description.

    CRITICAL source: a weekly run that returns zero here warns rather than passing
    silently (see CRITICAL_SOURCES) — the Fairgrounds is half a mile away.
    """
    try:
        from scrape_events import scrape_fairgrounds
    except Exception as e:  # noqa: BLE001
        print(f"[FAIRGROUNDS] import failed: {e}")
        return []

    # Dedupe same-show section re-listings within the source, preferring an entry
    # that carries a real start time over a time-less one.
    best: dict[tuple, dict] = {}
    for ev in scrape_fairgrounds():
        d = ev.get("date", "")
        try:
            dd = date.fromisoformat(d)
        except ValueError:
            continue
        if not _within_window(dd):
            continue
        venue = _clean(ev.get("venue", "Del Mar Fairgrounds"))
        artist = _strip_section(_clean(ev.get("title", "")))
        desc = "Concert" if venue == "The Sound" else _FAIRGROUNDS_CATEGORY_DESC.get(
            ev.get("category", ""), "Event")
        start = _range_start(ev.get("time", ""))
        normalized = _event(
            venue=venue, stream=None, city="Del Mar", area="Del Mar",
            date=d, day=dd.strftime("%A"), start=start,
            artist=artist, genre="", description=desc,
            source="delmarfairgrounds.com",
            source_url=ev.get("source") or "https://www.delmarfairgrounds.com/events",
            tier=1, confidence="high",
        )
        key = (venue, d, artist.lower())
        cur = best.get(key)
        if cur is None or (not cur.get("start") and start):
            best[key] = normalized
    return list(best.values())


# ─── Tier-3: manual overlay (operator embellishment) ─────────────────────────

def load_manual_overlay() -> list[dict]:
    """Operator-curated events for gap venues (The Sound, Coyote, Roxy, Oceanside Pier...).

    Schema (data/music_manual.json): list of objects with at least
      {venue, city, date 'YYYY-MM-DD', start, artist}; optional area/genre/description/end.
    Everything here is surfaced as low-confidence (⚠) until the operator removes the flag.
    """
    if not MANUAL_OVERLAY_FILE.exists():
        return []
    try:
        items = json.loads(MANUAL_OVERLAY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[MANUAL OVERLAY] unreadable: {e}")
        return []
    out: list[dict] = []
    for it in items if isinstance(items, list) else []:
        try:
            d = date.fromisoformat(it["date"])
        except (KeyError, ValueError):
            continue
        if not _within_window(d):
            continue
        out.append(_event(
            venue=_clean(it.get("venue", "?")), stream=it.get("stream"),
            city=it.get("city", ""), area=it.get("area", it.get("city", "")),
            date=d.isoformat(), day=d.strftime("%A"),
            start=it.get("start", ""), end=it.get("end"),
            artist=_clean(it.get("artist", "")), genre=it.get("genre", ""),
            description=it.get("description", ""),
            source=it.get("source", "manual"), source_url=it.get("source_url", ""),
            tier=3, confidence=it.get("confidence", "low"),
        ))
    return out


# ─── Orchestration ───────────────────────────────────────────────────────────

SOURCES = [
    ("Del Mar Plaza / Monarch", scrape_del_mar_plaza_music),
    ("Pour House (Oceanside)", scrape_pour_house),
    ("The Kraken (Cardiff)", scrape_kraken),
    ("Belly Up (Solana Beach)", scrape_belly_up_music),
    ("Del Mar Fairgrounds / The Sound", scrape_fairgrounds_music),
    ("Manual overlay", load_manual_overlay),
]

# Sources whose silence is suspicious, not normal: a weekly run that scrapes ZERO
# events (or errors) from one of these raises a loud warning rather than passing
# quietly. The Fairgrounds is half a mile from home and runs something most weeks,
# so an empty result almost always means the feed broke — not a quiet week.
CRITICAL_SOURCES = {"Del Mar Fairgrounds / The Sound"}


def _dedupe(events: list[dict]) -> list[dict]:
    """Collapse exact dupes (same venue+date+artist). Direct sources win over manual."""
    best: dict[tuple, dict] = {}
    for ev in events:
        key = (ev["venue"], ev["date"], ev["artist"].lower())
        cur = best.get(key)
        if cur is None or ev.get("tier", 9) < cur.get("tier", 9):
            best[key] = ev
    return list(best.values())


def scrape_all_music(verbose: bool = True) -> tuple[list[dict], dict]:
    """Run every source. Returns (events, report). One dead source never blocks the rest."""
    all_events: list[dict] = []
    report: dict[str, int | str] = {}
    for label, fn in SOURCES:
        try:
            evs = fn()
            report[label] = len(evs)
            all_events.extend(evs)
            if verbose:
                tag = "DRY" if not evs else "ok"
                print(f"  [{tag:>3}] {label}: {len(evs)} events")
        except Exception as e:  # noqa: BLE001 — isolate per-source failure
            report[label] = f"ERROR: {e}"
            if verbose:
                print(f"  [ERR] {label}: {e}")

    # Critical sources: zero events or an error means the feed likely broke. Surface
    # it loudly so a silent failure can't masquerade as "quiet week" (report["_warnings"]).
    warnings = []
    for label in CRITICAL_SOURCES:
        val = report.get(label)
        if val == 0:
            warnings.append(f"CRITICAL source '{label}' returned 0 events — feed may be down.")
        elif isinstance(val, str) and val.startswith("ERROR"):
            warnings.append(f"CRITICAL source '{label}' errored: {val}")
    if warnings:
        report["_warnings"] = warnings

    deduped = _dedupe(all_events)
    deduped.sort(key=lambda e: (e["date"], e.get("start", "")))
    if verbose:
        dry = [k for k, v in report.items() if v == 0]
        print(f"  -> {len(deduped)} unique events ({len(all_events)} before dedupe)")
        if dry:
            print(f"  -> DRY sources (0 events): {', '.join(dry)}")
        for w in warnings:
            print(f"  [WARN] {w}")
    return deduped, report


def main():
    print("Scraping live music sources (Del Mar -> Oceanside)...")
    events, _ = scrape_all_music(verbose=True)
    from collections import Counter
    by_city = Counter(e["city"] for e in events)
    print(f"\nBy city: {dict(by_city)}")
    print("\nFirst 12 events:")
    for e in events[:12]:
        loc = f" [{e['stream']}]" if e.get("stream") else ""
        print(f"  {e['marker']} {e['date']} {e['day'][:3]} {e['start']:>8}  "
              f"{e['venue']}{loc} ({e['city']}) — {e['artist']}")


if __name__ == "__main__":
    main()
