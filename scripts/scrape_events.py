"""
Local Social event scraper — fetches live event data from North County sources.

Sources:
  1. Belly Up Tavern (bellyup.com/events) — live music lineup
  2. Del Mar Plaza (delmarplaza.com/events) — Seaside Sessions + Monarch schedule
  3. Encinitas 101 (encinitas101.com/events) — street fairs, cruise nights, tastings
  4. North Coast Rep (northcoastrep.org) — theater shows
  5. Del Mar city calendar (delmar.ca.us) — community events (via iCal, already wired)

Output: data/scraped_events.json — consumed by daily_social_plan.py

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

# How far ahead to look
LOOKAHEAD_DAYS = 30

# North County areas we care about
NC_AREAS = {"Del Mar", "Solana Beach", "Encinitas", "Carlsbad"}


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

def scrape_fairgrounds() -> list[dict]:
    """Del Mar Fairgrounds: SD County Fair, Toyota Summer Concert Series, racing.

    Fairgrounds site uses dynamic JS loading — can't scrape via urllib.
    Known schedule maintained here, refreshed periodically.

    The Fairgrounds is HALF A MILE from the user's home — every event here
    is local and prominent. All events flagged big_event=True.
    """
    today = date.today()
    events = []

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
                    events.append({
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
            events.append({
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
        events.append({
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
                    events.append({
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

    # Dedupe by title + date
    seen = set()
    deduped = []
    for ev in all_events:
        key = f"{ev['title'].lower()}|{ev['date']}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ev)

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

    if dry_run:
        print(f"\n{'='*60}")
        print(f"SCRAPED EVENTS ({len(events)})")
        print(f"{'='*60}")
        for ev in events:
            big = " ***BIG***" if ev.get("big_event") else ""
            print(f"  {ev['date']}  {ev['venue']:<30}  {ev['title']}{big}")
            print(f"           {ev['time']}  [{ev['category']}]  src: {ev['source']}")
    else:
        save_events(events)
