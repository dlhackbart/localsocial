"""
Local Social event scraper — fetches live event data from North County sources.

Sources:
  1. Belly Up Tavern (bellyup.com/events) — live music lineup
  2. Del Mar Plaza (delmarplaza.com/events) — Seaside Sessions + Monarch schedule
  3. Encinitas 101 (encinitas101.com/events) — street fairs, cruise nights, tastings
  4. North Coast Rep (northcoastrep.org) — theater shows
  5. Del Mar city calendar (delmar.ca.us) — community events (via iCal, already wired)
  6. Weekly venue schedules (per-venue homepages) — pulls recurring day/time
     patterns ("Trivia Tuesday 7 PM", "Live music every Friday") from the 8
     static venues with real websites. Falls back to hardcoded venue data in
     daily_social_plan.py when the scrape yields nothing.

Output:
  - data/scraped_events.json   — dated events (consumed by daily_social_plan.py)
  - data/venue_schedules.json  — scraped weekly patterns per venue (overlay)

Usage:
    python scrape_events.py              # Scrape all sources, save to JSON
    python scrape_events.py --dry-run    # Print without saving
"""

import json
import re
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = DATA_DIR / "scraped_events.json"
VENUE_SCHEDULES_FILE = DATA_DIR / "venue_schedules.json"

# How far ahead to look
LOOKAHEAD_DAYS = 30

# North County areas we care about (Del Mar -> Oceanside coast)
NC_AREAS = {"Del Mar", "Solana Beach", "Cardiff", "Encinitas", "Leucadia", "Carlsbad", "Oceanside"}


def fetch_url(url: str) -> str | None:
    """Fetch a URL, return text or None on failure."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={
            "User-Agent": "LocalSocial/0.1 (+https://localsocial.app)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[FETCH FAILED] {url}: {e}")
        return None


# ─── Belly Up ────────────────────────────────────────────────────────────────

def scrape_belly_up() -> list[dict]:
    """Scrape Belly Up Tavern event listings."""
    events = []
    html = fetch_url("https://www.bellyup.com/events")
    if not html:
        return events

    # Belly Up loads events via JS with a select2-style dropdown.
    # Event titles live in "display" fields: "Artist Name MM/DD"
    display_matches = re.findall(r'"display"\s*:\s*"([^"]+)"', html)

    today = date.today()
    year = today.year
    seen = set()

    for raw_title in display_matches:
        # Clean escaped chars
        title = raw_title.replace("\\'", "'").replace('\\"', '"')

        # Extract date suffix: "Artist Name MM/DD"
        m = re.search(r'\s+(\d{2})/(\d{2})\s*$', title)
        if not m:
            continue

        month, day = int(m.group(1)), int(m.group(2))
        artist = title[:m.start()].strip()

        if not artist or artist.lower() == "private event":
            continue

        try:
            event_date = date(year, month, day)
            if event_date < today:
                event_date = date(year + 1, month, day)
            if (event_date - today).days > LOOKAHEAD_DAYS:
                continue
        except ValueError:
            continue

        # Dedupe by artist + date
        key = f"{artist.lower()}|{event_date.isoformat()}"
        if key in seen:
            continue
        seen.add(key)

        events.append({
            "title": artist,
            "date": event_date.isoformat(),
            "time": "8:00 PM",
            "venue": "Belly Up Tavern",
            "area": "Solana Beach",
            "source": "bellyup.com",
            "category": "live_music_small",
            "big_event": _is_big_show(artist),
        })

    return events



def _is_big_show(title: str) -> bool:
    """Heuristic: is this a headline-worthy show?"""
    # Known big acts (add to this list over time)
    big_names = [
        "matisyahu", "disco biscuits", "los lobos", "breeders", "built to spill",
        "psychedelic furs", "pat metheny", "cory wong", "pharcyde", "wood brothers",
        "protoje", "iam tongi", "royel otis",
    ]
    lower = title.lower()
    return any(name in lower for name in big_names)


# ─── Del Mar Plaza ───────────────────────────────────────────────────────────

def scrape_del_mar_plaza() -> list[dict]:
    """Scrape Del Mar Plaza events (Seaside Sessions + specials)."""
    events = []
    html = fetch_url("https://www.delmarplaza.com/events")
    if not html:
        return events

    text = re.sub(r'<[^>]+>', '\n', html)
    text = re.sub(r'\n\s*\n', '\n', text)

    # Try JSON-LD first
    ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for ld in ld_matches:
        try:
            data = json.loads(ld)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Event":
                    ev = _parse_plaza_ld(item)
                    if ev:
                        events.append(ev)
        except json.JSONDecodeError:
            continue

    # Known recurring schedule (hardcoded from scraped data, refreshed periodically)
    # Seaside Sessions: Wed + Fri, 5-7 PM on the Ocean View Deck
    # Monarch: Wed-Sun, 4-7 PM
    # These are already in our venue data — only add SPECIAL events here
    today = date.today()

    # Special events from the scrape (manually maintained when scraper runs)
    specials = [
        {"title": "San Diego Book Crawl at Camino Books", "date": "2026-04-25",
         "time": "All day", "category": "community_civic"},
        {"title": "San Diego Book Crawl at Camino Books", "date": "2026-04-26",
         "time": "All day", "category": "community_civic"},
        {"title": "San Diego Book Crawl at Camino Books", "date": "2026-04-27",
         "time": "All day", "category": "community_civic"},
        {"title": "Monarch Kentucky Derby Party", "date": "2026-05-02",
         "time": "All day", "category": "food_drink", "big_event": True},
    ]

    for sp in specials:
        try:
            ed = date.fromisoformat(sp["date"])
            if ed < today or (ed - today).days > LOOKAHEAD_DAYS:
                continue
            events.append({
                **sp,
                "venue": "Del Mar Plaza",
                "area": "Del Mar",
                "source": "delmarplaza.com",
                "big_event": sp.get("big_event", False),
            })
        except ValueError:
            continue

    return events


def _clean_html_entities(text: str) -> str:
    """Clean HTML entities from scraped text."""
    import html
    return html.unescape(text).strip()


def _parse_plaza_ld(data: dict) -> dict | None:
    """Parse Del Mar Plaza JSON-LD event."""
    title = _clean_html_entities(data.get("name", ""))
    start = data.get("startDate", "")
    if not title or not start:
        return None

    # Skip private events
    if "private event" in title.lower():
        return None

    try:
        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        event_date = dt.date()
    except (ValueError, AttributeError):
        return None

    today = date.today()
    if event_date < today or (event_date - today).days > LOOKAHEAD_DAYS:
        return None

    return {
        "title": title,
        "date": event_date.isoformat(),
        "time": dt.strftime("%I:%M %p").lstrip("0") if dt.hour else "5:00 PM",
        "venue": "Del Mar Plaza",
        "area": "Del Mar",
        "source": "delmarplaza.com",
        "category": "live_music_small" if "session" in title.lower() or "music" in title.lower() else "community_civic",
        "big_event": False,
    }


# ─── Encinitas 101 ───────────────────────────────────────────────────────────

def scrape_encinitas101() -> list[dict]:
    """Scrape Encinitas 101 Main Street Association events."""
    events = []
    html = fetch_url("https://www.encinitas101.com/events")
    if not html:
        return events

    # Try JSON-LD
    ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for ld in ld_matches:
        try:
            data = json.loads(ld)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Event":
                    title = item.get("name", "")
                    start = item.get("startDate", "")
                    if not title or not start:
                        continue
                    try:
                        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                        event_date = dt.date()
                    except (ValueError, AttributeError):
                        continue

                    today = date.today()
                    if event_date < today or (event_date - today).days > LOOKAHEAD_DAYS:
                        continue

                    events.append({
                        "title": title,
                        "date": event_date.isoformat(),
                        "time": dt.strftime("%I:%M %p").lstrip("0") if dt.hour else "5:30 PM",
                        "venue": item.get("location", {}).get("name", "Downtown Encinitas"),
                        "area": "Encinitas",
                        "source": "encinitas101.com",
                        "category": _categorize_encinitas(title),
                        "big_event": _is_big_encinitas(title),
                    })
        except json.JSONDecodeError:
            continue

    # Known recurring events from scrape (refreshed periodically)
    today = date.today()
    known = [
        {"title": "Encinitas Spring Street Fair", "date": "2026-04-25",
         "time": "9:00 AM - 5:00 PM", "category": "markets", "big_event": True},
        {"title": "Encinitas Spring Street Fair", "date": "2026-04-26",
         "time": "9:00 AM - 5:00 PM", "category": "markets", "big_event": True},
        {"title": "Encinitas Cruise Night", "date": "2026-05-21",
         "time": "5:30 PM - 7:30 PM", "category": "meetups_clubs", "big_event": True},
        {"title": "Taste of Encinitas", "date": "2026-08-25",
         "time": "5:30 PM - 8:30 PM", "category": "food_drink", "big_event": True},
    ]

    seen_titles = {e["title"] for e in events}
    for k in known:
        if k["title"] in seen_titles:
            continue
        try:
            ed = date.fromisoformat(k["date"])
            if ed < today or (ed - today).days > LOOKAHEAD_DAYS:
                continue
            events.append({
                **k,
                "venue": "Downtown Encinitas (Hwy 101)",
                "area": "Encinitas",
                "source": "encinitas101.com",
            })
        except ValueError:
            continue

    return events


def _categorize_encinitas(title: str) -> str:
    lower = title.lower()
    if "cruise" in lower or "car" in lower:
        return "meetups_clubs"
    if "taste" in lower or "food" in lower:
        return "food_drink"
    if "fair" in lower or "market" in lower:
        return "markets"
    if "music" in lower or "concert" in lower:
        return "live_music_small"
    return "community_civic"


def _is_big_encinitas(title: str) -> bool:
    lower = title.lower()
    return any(kw in lower for kw in ["street fair", "taste of", "cruise night"])


# ─── North Coast Rep ─────────────────────────────────────────────────────────

def scrape_north_coast_rep() -> list[dict]:
    """Scrape North Coast Repertory Theatre shows."""
    events = []
    html = fetch_url("https://www.northcoastrep.org")
    if not html:
        return events

    # Try JSON-LD
    ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for ld in ld_matches:
        try:
            data = json.loads(ld)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") in ("Event", "TheaterEvent"):
                    title = item.get("name", "")
                    start = item.get("startDate", "")
                    end = item.get("endDate", "")
                    if not title:
                        continue
                    # Theater runs — just mark the opening
                    if start:
                        try:
                            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                            event_date = dt.date()
                        except (ValueError, AttributeError):
                            continue
                        today = date.today()
                        if event_date < today or (event_date - today).days > LOOKAHEAD_DAYS:
                            continue
                        events.append({
                            "title": f"{title} (North Coast Rep)",
                            "date": event_date.isoformat(),
                            "time": "7:30 PM",
                            "venue": "North Coast Repertory Theatre",
                            "area": "Solana Beach",
                            "source": "northcoastrep.org",
                            "category": "theater_small",
                            "big_event": False,
                        })
        except json.JSONDecodeError:
            continue

    # Known schedule from scrape
    today = date.today()
    known = [
        {"title": "Beau Jest (North Coast Rep)", "start": "2026-04-22", "end": "2026-05-17"},
        {"title": "The Most Happy Fella (North Coast Rep)", "start": "2026-06-03", "end": "2026-06-28"},
    ]

    seen = {e["title"] for e in events}
    for k in known:
        if k["title"] in seen:
            continue
        try:
            start_d = date.fromisoformat(k["start"])
            end_d = date.fromisoformat(k["end"])
            if end_d < today or (start_d - today).days > LOOKAHEAD_DAYS:
                continue
            # Add opening night
            show_date = max(start_d, today)
            events.append({
                "title": k["title"],
                "date": show_date.isoformat(),
                "time": "7:30 PM",
                "venue": "North Coast Repertory Theatre",
                "area": "Solana Beach",
                "source": "northcoastrep.org",
                "category": "theater_small",
                "big_event": False,
            })
        except ValueError:
            continue

    return events


# ─── Seaside Sessions schedule (from Del Mar Plaza scrape) ───────────────────

def get_seaside_sessions() -> list[dict]:
    """Return the known Seaside Sessions schedule with performer names."""
    sessions = [
        ("2026-04-16", "Ben Powell", "solo songwriter, guitar & vocals"),
        ("2026-04-18", "Albert Hurtado", "Jazz, Blues, Pop"),
        ("2026-04-23", "Dulaney & Company", "Blues, Folk, Americana"),
        ("2026-04-25", "Skyler Lutes", "Reggae & Surf Music"),
    ]

    today = date.today()
    events = []
    for date_str, artist, genre in sessions:
        try:
            ed = date.fromisoformat(date_str)
            if ed < today or (ed - today).days > LOOKAHEAD_DAYS:
                continue
            events.append({
                "title": f"Seaside Sessions: {artist} ({genre})",
                "date": date_str,
                "time": "5:00 PM - 7:00 PM",
                "venue": "Del Mar Plaza (Ocean View Deck)",
                "area": "Del Mar",
                "source": "delmarplaza.com",
                "category": "live_music_small",
                "big_event": False,
            })
        except ValueError:
            continue

    return events


# ─── La Paloma Theatre ────────────────────────────────────────────────────────

def scrape_la_paloma() -> list[dict]:
    """La Paloma Theatre showtimes (Encinitas).

    Veezi ticketing widget renders via JS — can't scrape with urllib.
    Known schedule maintained here, refreshed when WebFetch data is available.
    Schedule source: lapalomatheatre.com/showtimes (Veezi widget).
    """
    # Known schedule (scraped via WebFetch, updated periodically)
    # Format: (date, title, time, big_event)
    SCHEDULE = [
        ("2026-04-12", "The Godfather", "7:30 PM", False),
        ("2026-04-12", "Epic: Elvis Presley in Concert", "2:45 PM", False),
        ("2026-04-13", "Hamnet", "5:20 PM", False),
        ("2026-04-13", "Wuthering Heights", "8:00 PM", False),
        ("2026-04-14", "Hercules", "6:00 PM", False),
        ("2026-04-14", "No Other Choice", "8:10 PM", False),
        ("2026-04-15", "The Godfather", "8:00 PM", False),
        ("2026-04-15", "Nirvanna the Band the Show the Movie", "5:40 PM", False),
        ("2026-04-16", "SD Italian Film Festival: The Time It Takes", "7:00 PM", True),
        ("2026-04-16", "Epic: Elvis Presley in Concert", "4:00 PM", False),
        ("2026-04-18", "The Godfather Part II", "7:30 PM", False),
        ("2026-04-18", "Hercules", "12:30 PM", False),
        ("2026-04-19", "The Godfather Part II", "5:00 PM", False),
        ("2026-04-19", "Hercules", "3:00 PM", False),
        ("2026-04-20", "The Big Lebowski", "5:00 PM", False),
        ("2026-04-20", "The Big Lebowski", "8:00 PM", False),
        ("2026-04-21", "The Godfather Part II", "8:00 PM", False),
        ("2026-04-23", "Raising Arizona", "8:00 PM", False),
        ("2026-04-24", "The Rocky Horror Picture Show (Live Shadow Cast)", "10:30 PM", True),
        ("2026-04-25", "Raising Arizona", "6:00 PM", False),
        ("2026-04-26", "The Maltese Falcon", "5:00 PM", False),
        ("2026-04-28", "Raising Arizona", "8:00 PM", False),
        ("2026-04-29", "The Maltese Falcon", "6:00 PM", False),
    ]

    today = date.today()
    events = []
    seen = set()

    for date_str, title, time_str, big in SCHEDULE:
        try:
            event_date = date.fromisoformat(date_str)
        except ValueError:
            continue
        if event_date < today or (event_date - today).days > LOOKAHEAD_DAYS:
            continue

        # One entry per film per night (skip duplicate showtimes)
        key = f"{title.lower()}|{date_str}"
        if key in seen:
            continue
        seen.add(key)

        events.append({
            "title": title,
            "date": date_str,
            "time": time_str,
            "venue": "La Paloma Theatre",
            "area": "Encinitas",
            "source": "lapalomatheatre.com",
            "category": "movies_indie",
            "big_event": big,
        })

    return events


def _is_big_la_paloma(title: str) -> bool:
    """Flag special events at La Paloma (not regular screenings)."""
    lower = title.lower()
    return any(kw in lower for kw in [
        "rocky horror", "film festival", "live", "shadow cast",
        "premiere", "special engagement",
    ])


# ─── Del Mar Fairgrounds ──────────────────────────────────────────────────────

_FAIRGROUNDS_SKIP_PATTERNS = (
    "board meeting",      # 22nd DAA Board Meeting — internal governance, not public
    "daa meeting",
)


def _fairgrounds_category(name: str) -> str:
    """Classify a Fairgrounds event title into a scoring category."""
    n = name.lower()
    if any(k in n for k in ("racing", "race", "thoroughbred", "breeders", "championship", "tournament", "competition")):
        return "meetups_clubs"
    if "fair" in n and "bridal" not in n:  # "SD County Fair", not "Bridal Fair"
        return "markets"
    if any(k in n for k in ("expo", "show", "bazaar", "market", "festival", "sale")):
        return "markets"
    if any(k in n for k in ("exhibit", "art of", "gallery")):
        return "markets"
    # Default: artist/concert name
    return "live_music_small"


def _format_fairgrounds_time(start: int, end: int) -> str:
    """Convert integer times like 1000/1700 to '10:00 AM - 5:00 PM'."""
    def fmt(t: int) -> str | None:
        if t is None or t == 0:
            return None
        hh, mm = divmod(int(t), 100)
        if hh == 0:
            return f"12:{mm:02d} AM"
        if hh < 12:
            return f"{hh}:{mm:02d} AM"
        if hh == 12:
            return f"12:{mm:02d} PM"
        return f"{hh - 12}:{mm:02d} PM"
    s, e = fmt(start), fmt(end)
    if s and e and s != e:
        return f"{s} - {e}"
    return s or ""


def _fetch_fairgrounds_api(today: date) -> list[dict]:
    """Fetch live events from the Del Mar Fairgrounds JSON API."""
    raw = fetch_url("https://www.delmarfairgrounds.com/api/events")
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception as e:
        print(f"[FAIRGROUNDS API] JSON parse failed: {e}")
        return []
    if not isinstance(data, list):
        return []

    events = []
    seen: set[tuple[str, str]] = set()  # (date, name) — collapse parking/session duplicates
    for ev in data:
        name = (ev.get("Name") or "").strip()
        if not name:
            continue
        if any(pat in name.lower() for pat in _FAIRGROUNDS_SKIP_PATTERNS):
            continue
        url = ev.get("URL") or ""
        category = _fairgrounds_category(name)

        # "The Sound" is a concert venue at the Fairgrounds booked by Belly Up.
        # Same physical location but a distinct venue brand — keep it separate
        # in the feed so it deduplicates correctly against Belly Up's own listing.
        locations = [(l.get("Name") or "").strip() for l in (ev.get("Locations") or [])]
        at_the_sound = any("the sound" in loc.lower() for loc in locations)
        venue_name = "The Sound" if at_the_sound else "Del Mar Fairgrounds"

        # Prefer sessions with real times; fall back to time-less entries.
        items = ev.get("Items") or []
        items_sorted = sorted(items, key=lambda it: 0 if it.get("StartTime") else 1)
        for item in items_sorted:
            item_name = (item.get("Name") or "").lower()
            if "parking" in item_name:
                continue
            start = item.get("StartDate", "")[:10]
            if not start:
                continue
            try:
                ed = date.fromisoformat(start)
            except ValueError:
                continue
            if ed < today or (ed - today).days > LOOKAHEAD_DAYS:
                continue
            key = (ed.isoformat(), name.lower())
            if key in seen:
                continue
            seen.add(key)
            time_str = _format_fairgrounds_time(item.get("StartTime"), item.get("EndTime"))
            events.append({
                "title": name,
                "date": ed.isoformat(),
                "time": time_str,
                "venue": venue_name,
                "area": "Del Mar",
                "source": url or "delmarfairgrounds.com",
                "category": category,
                "big_event": True,
            })
    return events


def scrape_fairgrounds() -> list[dict]:
    """Del Mar Fairgrounds — live JSON API + hardcoded summer supplement.

    Primary: live fetch from https://www.delmarfairgrounds.com/api/events
    (every event within LOOKAHEAD_DAYS, with real times + category).

    Supplement: hardcoded Summer Concert Series, County Fair, and Thoroughbred
    racing schedule. The live feed surfaces these close to showtime; the
    hardcoded entries ensure they appear in the weekly plan months in advance
    and survive a live-API outage. Merged by (date, title) — live wins.

    The Fairgrounds is HALF A MILE from the user's home — every event here
    is local and prominent. All events flagged big_event=True.
    """
    today = date.today()
    events: list[dict] = []

    # ─── Live API (primary source) ────────────────────────────────────────
    live = _fetch_fairgrounds_api(today)
    if live:
        print(f"[FAIRGROUNDS API] Fetched {len(live)} sessions from live feed")
        events.extend(live)
    else:
        print("[FAIRGROUNDS API] Live feed empty/failed — using hardcoded fallback only")

    seen_keys = {(e["date"], e["title"].lower()) for e in events}

    def _add(ev: dict) -> None:
        key = (ev["date"], ev["title"].lower())
        if key in seen_keys:
            return
        seen_keys.add(key)
        events.append(ev)

    # ─── San Diego County Fair 2026 (June 10 - July 5) ────────────────────
    # Wednesday through Sunday only (closed Mon/Tue)
    fair_start = date(2026, 6, 10)
    fair_end = date(2026, 7, 5)
    current = fair_start
    while current <= fair_end:
        # Only Wed-Sun
        if current.weekday() < 5 or current.weekday() == 6:  # Mon=0..Sun=6; open Wed,Thu,Fri,Sat,Sun
            if current.weekday() in (2, 3, 4, 5, 6):
                if current >= today and (current - today).days <= LOOKAHEAD_DAYS:
                    _add({
                        "title": "San Diego County Fair",
                        "date": current.isoformat(),
                        "time": "11:00 AM - 11:00 PM",
                        "venue": "Del Mar Fairgrounds",
                        "area": "Del Mar",
                        "source": "sdfair.com",
                        "category": "markets",
                        "big_event": True,
                    })
        current = date.fromordinal(current.toordinal() + 1)

    # ─── Toyota Summer Concert Series 2026 ────────────────────────────────
    concerts = [
        ("2026-06-10", "Chicago (Grandstand)", "7:30 PM"),
        ("2026-06-12", "Koe Wetzel (Grandstand)", "7:30 PM"),
        ("2026-06-14", "Los Tucanes de Tijuana (Grandstand)", "7:30 PM"),
        ("2026-06-19", "Marshmello (Grandstand)", "7:30 PM"),
        ("2026-06-20", "Good Charlotte (Grandstand)", "7:30 PM"),
        ("2026-06-21", "Pancho Barraza & Banda Machos (Grandstand)", "7:30 PM"),
        ("2026-06-25", "Nelly (Grandstand)", "7:30 PM"),
        ("2026-06-26", "Maren Morris (Grandstand)", "7:30 PM"),
        ("2026-06-28", "El Coyote & Chuy Lizárraga (Grandstand)", "7:30 PM"),
        ("2026-07-01", "AJR (Grandstand)", "7:30 PM"),
        ("2026-07-05", "Conjunto Primavera (Grandstand)", "7:30 PM"),
    ]
    for d_str, artist, time_str in concerts:
        try:
            ed = date.fromisoformat(d_str)
            if ed < today or (ed - today).days > LOOKAHEAD_DAYS:
                continue
            _add({
                "title": artist,
                "date": d_str,
                "time": time_str,
                "venue": "Del Mar Fairgrounds",
                "area": "Del Mar",
                "source": "sdfair.com",
                "category": "live_music_small",
                "big_event": True,
            })
        except ValueError:
            continue

    # ─── Del Mar Thoroughbred Club Racing ─────────────────────────────────
    # 2026 Summer Meet: opens Friday July 17
    # Racing is typically Thu-Sun during the season
    racing_start = date(2026, 7, 17)
    racing_end = date(2026, 9, 6)  # Labor Day typical close

    if racing_start >= today and (racing_start - today).days <= LOOKAHEAD_DAYS:
        _add({
            "title": "Del Mar Racing — Opening Day",
            "date": racing_start.isoformat(),
            "time": "2:00 PM",
            "venue": "Del Mar Racetrack",
            "area": "Del Mar",
            "source": "dmtc.com",
            "category": "meetups_clubs",
            "big_event": True,
        })

    # Regular race days through the season (Thu-Sun)
    current = racing_start
    while current <= racing_end:
        if current.weekday() in (3, 4, 5, 6):  # Thu=3, Fri=4, Sat=5, Sun=6
            if current >= today and (current - today).days <= LOOKAHEAD_DAYS:
                if current != racing_start:  # Opening Day already added
                    _add({
                        "title": "Del Mar Racing",
                        "date": current.isoformat(),
                        "time": "2:00 PM" if current.weekday() == 4 else "2:00 PM",
                        "venue": "Del Mar Racetrack",
                        "area": "Del Mar",
                        "source": "dmtc.com",
                        "category": "meetups_clubs",
                        "big_event": True,
                    })
        current = date.fromordinal(current.toordinal() + 1)

    return events


# ─── Weekly venue schedule scraper ───────────────────────────────────────────
#
# For venues that don't have structured event feeds, fetch the site and pull
# recurring day-of-week patterns ("Trivia Tuesday 7 PM", "Happy Hour M-F 3-6").
# Writes to data/venue_schedules.json — daily_social_plan.py overlays these
# onto the hardcoded VENUES data when available.
#
# URLs come from data/venue_urls.json (managed by scripts/venue_registry.py).
# Each run also discovers new event-relevant subpages on known domains and
# adds them to the registry. Dead URLs get marked dormant after repeat fails.

import venue_registry

_DAY_ALIASES = {
    "mon": "Monday", "monday": "Monday",
    "tue": "Tuesday", "tues": "Tuesday", "tuesday": "Tuesday",
    "wed": "Wednesday", "weds": "Wednesday", "wednesday": "Wednesday",
    "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday", "thursday": "Thursday",
    "fri": "Friday", "friday": "Friday",
    "sat": "Saturday", "saturday": "Saturday",
    "sun": "Sunday", "sunday": "Sunday",
}
_DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DAY_PATTERN = r"(?:mon|tues?|wed(?:s|nes)?|thur?s?|fri|sat|sun)(?:day)?"
_TIME_PATTERN = r"\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)"
_TIME_RANGE = rf"{_TIME_PATTERN}\s*[-–—to ]+\s*{_TIME_PATTERN}"

# Keywords that signal this sentence describes a recurring event worth capturing
_EVENT_KEYWORDS = [
    "happy hour", "live music", "live band", "trivia", "karaoke",
    "brunch", "dj", "open mic", "bingo", "taco tuesday", "sunset",
    "acoustic", "happy-hour", "game night", "oyster", "burger night",
    "ladies night", "industry night", "patio", "social hour",
]


def _normalize_day(raw: str) -> str | None:
    return _DAY_ALIASES.get(raw.lower().strip().rstrip("."))


def _expand_day_range(start: str, end: str) -> list[str]:
    s = _normalize_day(start)
    e = _normalize_day(end)
    if not s or not e:
        return []
    si, ei = _DAY_ORDER.index(s), _DAY_ORDER.index(e)
    if si <= ei:
        return _DAY_ORDER[si:ei + 1]
    return _DAY_ORDER[si:] + _DAY_ORDER[:ei + 1]


def _clean_time(t: str) -> str:
    return re.sub(r"\s+", "", t.strip()).upper().replace("AM", " AM").replace("PM", " PM").strip()


def _clean_time_range(tr: str) -> str:
    parts = re.split(r"\s*[-–—]\s*|\s+to\s+", tr.strip(), maxsplit=1)
    if len(parts) == 2:
        return f"{_clean_time(parts[0])}-{_clean_time(parts[1])}"
    return _clean_time(tr)


def _guess_event_type(snippet: str) -> str:
    lower = snippet.lower()
    for kw in _EVENT_KEYWORDS:
        if kw in lower:
            return kw.replace("-", " ").title() if kw in {"happy-hour"} else kw
    # Fallback: collapse whitespace, trim to ~40 chars of the snippet
    cleaned = re.sub(r"\s+", " ", snippet).strip()
    return cleaned[:50].rstrip(",. ") if cleaned else "recurring event"


def _extract_schedule_from_text(text: str) -> list[dict]:
    """Pull (day, time, type) tuples from free-form text.

    Captures three shapes:
      1. DAY RANGE + TIME RANGE:  "Mon-Fri 3-6 PM"  (often happy hour)
      2. single DAY + TIME:        "Trivia Tuesday 7 PM"
      3. "every DAY" + optional TIME
    """
    events: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    text_lower = text.lower()

    # Pattern 1: day range + time range (happy-hour style)
    pat1 = re.compile(
        rf"({_DAY_PATTERN})\s*[-–—]\s*({_DAY_PATTERN})\s*(?:from\s+)?({_TIME_RANGE}|{_TIME_PATTERN})",
        re.IGNORECASE,
    )
    for m in pat1.finditer(text):
        days = _expand_day_range(m.group(1), m.group(2))
        if not days:
            continue
        time_str = _clean_time_range(m.group(3))
        snippet = text[max(0, m.start() - 40):m.end() + 10]
        ev_type = _guess_event_type(snippet)
        for d in days:
            key = (d, ev_type, time_str)
            if key in seen:
                continue
            seen.add(key)
            events.append({"day": d, "type": ev_type, "time": time_str, "broadAppeal": True})

    # Pattern 2: single day + time (e.g., "Trivia Tuesday 7 PM", "Live music Friday 9pm")
    pat2 = re.compile(
        rf"(?:(?P<pre>[A-Za-z][A-Za-z &'-]{{2,30}}?)\s+)?(?P<day>{_DAY_PATTERN})s?\s+(?:at\s+|from\s+)?(?P<time>{_TIME_RANGE}|{_TIME_PATTERN})",
        re.IGNORECASE,
    )
    for m in pat2.finditer(text):
        day = _normalize_day(m.group("day"))
        if not day:
            continue
        time_str = _clean_time_range(m.group("time"))
        pre = (m.group("pre") or "").strip()
        snippet_start = max(0, m.start() - 20)
        snippet = text[snippet_start:m.end() + 20]
        # Only keep if the surrounding text mentions an event keyword
        if not any(kw in snippet.lower() for kw in _EVENT_KEYWORDS):
            continue
        ev_type = _guess_event_type((pre + " " + snippet).strip())
        key = (day, ev_type, time_str)
        if key in seen:
            continue
        seen.add(key)
        events.append({"day": day, "type": ev_type, "time": time_str, "broadAppeal": True})

    # Pattern 3: "every DAY" (without a time — just confirms the day is active)
    pat3 = re.compile(rf"every\s+({_DAY_PATTERN})", re.IGNORECASE)
    for m in pat3.finditer(text):
        day = _normalize_day(m.group(1))
        if not day:
            continue
        snippet = text[max(0, m.start() - 40):m.end() + 60]
        if not any(kw in snippet.lower() for kw in _EVENT_KEYWORDS):
            continue
        time_match = re.search(_TIME_RANGE + "|" + _TIME_PATTERN, snippet)
        time_str = _clean_time_range(time_match.group(0)) if time_match else ""
        ev_type = _guess_event_type(snippet)
        key = (day, ev_type, time_str)
        if key in seen or not time_str:
            continue
        seen.add(key)
        events.append({"day": day, "type": ev_type, "time": time_str, "broadAppeal": True})

    return events


# ─── LLM-based schedule extraction ───────────────────────────────────────────
#
# Regex catches clean day-token patterns ("Monday 7 PM") but misses marketing
# prose ("every Friday night," "weeknights 3-6"). Claude Haiku handles the
# prose cases. If the API call fails (no key, network, parse error), we fall
# back to the regex extractor so the scraper never breaks.

_ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
_LLM_MODEL = "claude-haiku-4-5-20251001"
_LLM_TEXT_CAP = 8000  # chars of page text per call (keeps cost < $0.001/venue)


def _load_anthropic_key() -> str | None:
    """ANTHROPIC_API_KEY from env first, then spy_timing/config.py."""
    import os
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    config_path = PROJECT_ROOT.parent / "spy_timing" / "config.py"
    if config_path.exists():
        try:
            text = config_path.read_text()
            m = re.search(r"ANTHROPIC_API_KEY\s*=\s*['\"]([^'\"]+)['\"]", text)
            if m:
                return m.group(1)
        except Exception:
            pass
    return None


# Cache the key check so we don't re-read spy_timing/config.py on every URL
_anthropic_key_cache: str | None = None
_anthropic_key_loaded = False


def _anthropic_key() -> str | None:
    global _anthropic_key_cache, _anthropic_key_loaded
    if not _anthropic_key_loaded:
        _anthropic_key_cache = _load_anthropic_key()
        _anthropic_key_loaded = True
    return _anthropic_key_cache


_VALID_DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}

# A time range wider than this is almost certainly operating hours, not an event
_MAX_EVENT_DURATION_HOURS = 6


def _norm_time_token(t: str) -> str:
    """'4PM' / '4pm' / '4:00pm' / '4:00 PM' → '4:00 PM'. Unparseable → original trimmed."""
    s = t.strip().upper().replace(".", "")
    s = re.sub(r"\s+", "", s)
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?(AM|PM)?$", s)
    if not m:
        return t.strip()
    hour = int(m.group(1))
    mins = m.group(2) or "00"
    mer = m.group(3) or ""
    return f"{hour}:{mins} {mer}".strip()


def _normalize_time_str(t: str) -> str:
    """Canonical form: '4:00 PM - 5:00 PM' or '9:00 PM' for single times.

    Handles:
      - em/en dashes → hyphen
      - missing meridiem on range start ("3-5 PM" → "3:00 PM - 5:00 PM")
      - missing minutes ("4PM" → "4:00 PM")
    """
    if not t:
        return ""
    s = re.sub(r"[–—−]", "-", t.strip())
    s = re.sub(r"\s+to\s+", "-", s, flags=re.IGNORECASE)
    parts = [p.strip() for p in re.split(r"\s*-\s*", s) if p.strip()]
    if len(parts) == 2:
        start, end = parts
        end_mer_match = re.search(r"(AM|PM)", end, re.IGNORECASE)
        if end_mer_match and not re.search(r"(AM|PM)", start, re.IGNORECASE):
            start = f"{start} {end_mer_match.group(1).upper()}"
        return f"{_norm_time_token(start)} - {_norm_time_token(end)}"
    if len(parts) == 1:
        return _norm_time_token(parts[0])
    return t.strip()


def _parse_hour(token: str) -> float | None:
    """Return hour as float (e.g. '4:30 PM' → 16.5). None if unparseable."""
    s = token.strip().upper().replace(".", "")
    s = re.sub(r"\s+", "", s)
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?(AM|PM)?$", s)
    if not m:
        return None
    hour = int(m.group(1))
    mins = int(m.group(2) or "0")
    mer = m.group(3)
    if mer == "PM" and hour != 12:
        hour += 12
    elif mer == "AM" and hour == 12:
        hour = 0
    return hour + mins / 60.0


def _event_duration_hours(time_str: str) -> float | None:
    """Return duration of a time range in hours, or None if not a range/unparseable."""
    s = re.sub(r"[–—−]", "-", time_str)
    s = re.sub(r"\s+to\s+", "-", s, flags=re.IGNORECASE)
    parts = [p.strip() for p in re.split(r"\s*-\s*", s) if p.strip()]
    if len(parts) != 2:
        return None
    start_token, end_token = parts
    # If start lacks meridiem but end has one, inherit it — "4-5 PM" means
    # "4 PM to 5 PM", not "4 AM to 5 PM". Without this the duration filter
    # mis-reads short happy hours as 13-hour spans.
    if not re.search(r"(AM|PM)", start_token, re.IGNORECASE):
        end_mer = re.search(r"(AM|PM)", end_token, re.IGNORECASE)
        if end_mer:
            start_token = f"{start_token} {end_mer.group(1).upper()}"
    start_h = _parse_hour(start_token)
    end_h = _parse_hour(end_token)
    if start_h is None or end_h is None:
        return None
    # Handle wraparound past midnight (e.g. "9 PM - 1 AM")
    if end_h < start_h:
        end_h += 24
    return end_h - start_h


_MENU_ITEM_SIGNALS = [
    "mac and cheese", "mac & cheese", "burger special", "special menu",
    "menu special", "appetizer", "side dish", "sandwich", "taco special",
]


def _is_menu_item(type_str: str) -> bool:
    lower = type_str.lower()
    return any(sig in lower for sig in _MENU_ITEM_SIGNALS)


def _normalize_type_for_dedup(t: str) -> str:
    """Lowercase, collapse whitespace, strip parens — dedup key only."""
    s = re.sub(r"\s*\([^)]*\)", "", t.strip().lower())
    return re.sub(r"\s+", " ", s)


def _llm_extract_schedule(text: str, venue_name: str) -> list[dict] | None:
    """Ask Claude Haiku to extract recurring weekly events from page text.

    Returns a list of {day, type, time, broadAppeal} dicts, or None if the LLM
    call failed (network, bad JSON, missing key). Caller should fall back to
    regex extraction on None.
    """
    api_key = _anthropic_key()
    if not api_key or not text.strip():
        return None

    trimmed = text[:_LLM_TEXT_CAP]
    prompt = f"""You are extracting recurring weekly SOCIAL EVENTS from a venue website. The venue is "{venue_name}".

Below is the text content of a page from their site. Extract ONLY events people gather for at a specific day and time: happy hour, trivia, live music, karaoke, brunch, DJ sets, themed nights, tastings, open mic, bingo, etc.

For each event, return:
  - "days": a list of day names from Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday. Expand ranges ("Mon-Fri" -> all 5). Interpret "weeknights" as Mon-Thu, "weekends" as Sat-Sun, "daily" as all 7.
  - "time": the time range as written (e.g. "3-6 PM", "9:00 PM", "8 AM-12 PM")
  - "type": a short label like "happy hour", "live music", "trivia", "brunch", "DJ", "karaoke"

Rules — READ CAREFULLY:
  1. Only extract events LITERALLY mentioned in the text. Do not infer or invent.
  2. DO NOT extract menu items, food specials, or dishes that are always available (e.g. "Mac and Cheese Special", "our famous burger"). Those are menu items, not events. Only extract a food special if it's a named recurring EVENT where people show up at a specific time (e.g. "Taco Tuesday 5-8 PM" is OK; "$5 burgers all day" is NOT).
  3. DO NOT extract time ranges that equal the venue's operating hours (e.g. "11 AM - 12 AM", "4 PM - close"). Those are business hours, not events. Event time ranges are typically 1-4 hours long.
  4. Skip one-off dated events (e.g. "April 22 show" — handled elsewhere).
  5. Skip items without both a specific day AND a specific time.
  6. Return a raw JSON array. No markdown, no prose. Return [] if nothing matches.

--- PAGE TEXT ---
{trimmed}
--- END ---"""

    try:
        body = json.dumps({
            "model": _LLM_MODEL,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            _ANTHROPIC_ENDPOINT,
            data=body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
        text_out = result.get("content", [{}])[0].get("text", "")
        match = re.search(r"\[[\s\S]*\]", text_out)
        if not match:
            return []
        raw = json.loads(match.group(0))
    except Exception as e:
        print(f"    [LLM] call failed: {e}")
        return None

    # Flatten day lists, validate, normalize time, drop menu items / all-day specials
    events: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        days = item.get("days") or []
        if isinstance(days, str):
            days = [days]
        time_str = (item.get("time") or "").strip()
        type_str = (item.get("type") or "").strip()
        if not time_str or not type_str:
            continue
        if _is_menu_item(type_str):
            continue
        dur = _event_duration_hours(time_str)
        if dur is not None and dur > _MAX_EVENT_DURATION_HOURS:
            continue
        normalized_time = _normalize_time_str(time_str)
        for d in days:
            if not isinstance(d, str):
                continue
            d_norm = d.strip().title()
            if d_norm not in _VALID_DAYS:
                continue
            events.append({
                "day": d_norm,
                "type": type_str,
                "time": normalized_time,
                "broadAppeal": True,
            })
    return events


# Needed for the Anthropic HTTP call above (urllib imported lazily inside fetch_url)
import urllib.request


def _html_to_text(html: str) -> str:
    """Strip HTML to plain text, preserving token spacing."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def scrape_venue_schedule(reg: dict, name: str) -> dict:
    """Scrape every known URL for one venue, discovering new subpages as we go.

    Mutates the registry (success/failure counts, newly discovered URLs). Returns
    a dict with merged events across all URLs that yielded at least one pattern.
    """
    urls_to_try = venue_registry.live_urls_for(reg, name)
    if not urls_to_try:
        return {"venue": name, "urls": [], "events": [], "error": "no_live_urls"}

    merged_events: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()
    urls_fetched: list[str] = []
    newly_discovered: list[str] = []

    # Fetch queue: known URLs first. Subpage discovery only runs on URLs that
    # actually returned HTML — we don't want to fan out from dead pages.
    queue = list(urls_to_try)
    processed: set[str] = set()

    while queue:
        url = queue.pop(0)
        if url in processed:
            continue
        processed.add(url)

        html = fetch_url(url)
        if not html:
            venue_registry.mark_failure(reg, name, url)
            continue

        venue_registry.mark_success(reg, name, url)
        urls_fetched.append(url)

        # Extract weekly patterns from this page — LLM first, regex fallback
        text = _html_to_text(html)
        extracted = _llm_extract_schedule(text, name)
        source_tag = "llm"
        if extracted is None:
            extracted = _extract_schedule_from_text(text)
            source_tag = "regex"
        for ev in extracted:
            # Dedup on normalized values so "4-5PM" and "4:00 PM - 5:00 PM"
            # collapse. Display value keeps whichever variant arrived first.
            key = (
                ev["day"],
                _normalize_type_for_dedup(ev["type"]),
                _normalize_time_str(ev["time"]),
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            ev["_extracted_by"] = source_tag
            merged_events.append(ev)

        # Discover new event-relevant subpages (only from pages we haven't
        # already crawled — avoid infinite loops)
        for sub in venue_registry.discover_subpage_urls(html, url):
            if sub in processed:
                continue
            if venue_registry.add_url(reg, name, sub, source="discovered"):
                newly_discovered.append(sub)
                queue.append(sub)

    return {
        "venue": name,
        "urls": urls_fetched,
        "newly_discovered": newly_discovered,
        "scraped_at": datetime.now().isoformat(),
        "events": merged_events,
    }


def scrape_all_venue_schedules(persist_registry: bool = True) -> dict:
    """Scrape weekly patterns for every venue in the registry.

    Also discovers new event-relevant subpages on known domains and updates the
    registry so future runs hit them directly. Pass persist_registry=False to
    skip writing the updated registry to disk (used by --dry-run).
    """
    reg = venue_registry.load()
    result: dict[str, dict] = {}

    for name in venue_registry.venues(reg):
        print(f"[VENUE SCHEDULE] {name}...")
        sched = scrape_venue_schedule(reg, name)
        evs = sched.get("events", [])
        new_urls = sched.get("newly_discovered", [])
        if sched.get("error") == "no_live_urls":
            print(f"  [WARN] all known URLs dormant — hardcoded schedule will be used")
        else:
            print(f"  fetched {len(sched['urls'])} URL(s), found {len(evs)} pattern(s)", end="")
            if new_urls:
                print(f", discovered {len(new_urls)} new subpage(s)")
                for u in new_urls:
                    print(f"    + {u}")
            else:
                print()
        result[name] = sched

    if persist_registry:
        venue_registry.save(reg)
    return result


def save_venue_schedules(schedules: dict):
    payload = {
        "scraped_at": datetime.now().isoformat(),
        "venue_count": len(schedules),
        "schedules": schedules,
    }
    VENUE_SCHEDULES_FILE.write_text(json.dumps(payload, indent=2))
    total_events = sum(len(s.get("events", [])) for s in schedules.values())
    print(f"[SAVED] {VENUE_SCHEDULES_FILE} ({len(schedules)} venues, {total_events} weekly patterns)")


# ─── Main ────────────────────────────────────────────────────────────────────

def scrape_all() -> list[dict]:
    """Run all scrapers, return combined event list."""
    all_events = []

    print("[SCRAPE] Belly Up Tavern...")
    all_events.extend(scrape_belly_up())

    print("[SCRAPE] Del Mar Plaza...")
    all_events.extend(scrape_del_mar_plaza())

    print("[SCRAPE] Seaside Sessions schedule...")
    all_events.extend(get_seaside_sessions())

    print("[SCRAPE] Encinitas 101...")
    all_events.extend(scrape_encinitas101())

    print("[SCRAPE] North Coast Rep...")
    all_events.extend(scrape_north_coast_rep())

    print("[SCRAPE] La Paloma Theatre...")
    all_events.extend(scrape_la_paloma())

    print("[SCRAPE] Del Mar Fairgrounds...")
    all_events.extend(scrape_fairgrounds())

    # Dedupe by normalized-artist + date. Scrapers produce different title
    # forms for the same concert ("Vandelux" from the Fairgrounds API vs
    # "Vandelux - California Tour" from Belly Up). We key on the leading
    # artist name so both land on the same slot, then prefer the more
    # specific venue — "The Sound" (a Belly-Up-managed room at the
    # Fairgrounds) should win over Belly Up's generic listing of the same
    # concert.
    _VENUE_PRIORITY = {"the sound": 3, "del mar fairgrounds": 2, "del mar racetrack": 2}

    def _priority(ev: dict) -> int:
        return _VENUE_PRIORITY.get(ev.get("venue", "").lower(), 1)

    def _artist_key(title: str) -> str:
        t = title.lower()
        # Cut at the first separator that typically introduces a tour name,
        # supporting act, or subtitle.
        for sep in (" - ", " – ", " — ", ": ", " featuring ", " feat. ", " feat ", " w/ ", " with "):
            idx = t.find(sep)
            if idx > 0:
                t = t[:idx]
        return t.strip()

    by_key: dict[tuple[str, str], dict] = {}
    for ev in all_events:
        key = (_artist_key(ev["title"]), ev["date"])
        existing = by_key.get(key)
        if existing is None or _priority(ev) > _priority(existing):
            by_key[key] = ev
    deduped = list(by_key.values())

    # Sort by date
    deduped.sort(key=lambda e: e["date"])

    print(f"[SCRAPE] Total: {len(deduped)} events from {len(all_events)} raw")
    return deduped


def save_events(events: list[dict]):
    """Save scraped events to JSON."""
    output = {
        "scraped_at": datetime.now().isoformat(),
        "event_count": len(events),
        "events": events,
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))
    print(f"[SAVED] {OUTPUT_FILE} ({len(events)} events)")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    events = scrape_all()

    print("\n[SCRAPE] Weekly venue schedules...")
    schedules = scrape_all_venue_schedules(persist_registry=not dry_run)

    if dry_run:
        print(f"\n{'='*60}")
        print(f"SCRAPED EVENTS ({len(events)})")
        print(f"{'='*60}")
        for ev in events:
            big = " ***BIG***" if ev.get("big_event") else ""
            print(f"  {ev['date']}  {ev['venue']:<30}  {ev['title']}{big}")
            print(f"           {ev['time']}  [{ev['category']}]  src: {ev['source']}")

        print(f"\n{'='*60}")
        print(f"VENUE WEEKLY SCHEDULES ({len(schedules)} venues)")
        print(f"{'='*60}")
        for name, sched in schedules.items():
            err = sched.get("error")
            evs = sched.get("events", [])
            urls = sched.get("urls", [])
            if err == "no_live_urls":
                print(f"  {name}: [all URLs dormant] — hardcoded fallback")
                continue
            if not evs:
                print(f"  {name}: no weekly patterns matched ({len(urls)} URL(s) scanned) — hardcoded fallback")
                continue
            print(f"  {name}: {len(evs)} patterns from {len(urls)} URL(s)")
            for e in evs:
                print(f"    {e['day']:<10} {e['time']:<18} {e['type']}")
    else:
        save_events(events)
        save_venue_schedules(schedules)
