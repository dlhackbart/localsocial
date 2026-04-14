"""
Daily Social Plan Generator for Local Social.

Generates the formatted Social Plan for today based on venue schedules,
sample events, and the weekly rhythm. Outputs plain text suitable for
SMS (short) and email (full).

Usage:
    python daily_social_plan.py              # Print full plan
    python daily_social_plan.py --json       # JSON output
"""

import json
import re
import sys
from datetime import datetime, date
from pathlib import Path

# Add src/ to path so we can import the scoring engine
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

# We can't import TypeScript directly, so we replicate the core logic in Python.
# This stays in sync with the TS scoring engine but runs standalone for notifications.

# ─── Area data ───────────────────────────────────────────────────────────────

AREAS = {
    "Del Mar": ["Solana Beach", "Encinitas"],
    "Solana Beach": ["Del Mar", "Encinitas"],
    "Encinitas": ["Solana Beach", "Carlsbad"],
    "Carlsbad": ["Encinitas"],
}

DEFAULT_HOME_AREA = "Del Mar"
DEFAULT_ZONES = AREAS[DEFAULT_HOME_AREA]

DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# ─── Venue data (mirrors src/data/venues.ts) ────────────────────────────────

VENUES = [
    {
        "name": "Torrey Pines Gliderport", "area": "Del Mar",
        "repeatFriendly": True, "conversationFriendly": True, "energy": "medium",
        "happyHour": {"days": ["Monday","Tuesday","Wednesday","Thursday"], "start": "4:00 PM", "end": "5:00 PM"},
        "events": [
            {"day": "Friday", "type": "Cliffhanger sunset", "time": "5-8 PM", "broadAppeal": True},
            {"day": "Saturday", "type": "Cliffhanger sunset", "time": "5-8 PM", "broadAppeal": True},
        ],
    },
    {
        "name": "Monarch Ocean Pub", "area": "Del Mar",
        "repeatFriendly": True, "conversationFriendly": True, "energy": "medium",
        "happyHour": {"days": ["Tuesday","Wednesday","Thursday","Friday"], "start": "4:00 PM", "end": "6:00 PM"},
        "events": [
            {"day": "Wednesday", "type": "acoustic", "time": "4-7 PM", "broadAppeal": True},
            {"day": "Thursday", "type": "acoustic", "time": "4-7 PM", "broadAppeal": True},
            {"day": "Friday", "type": "acoustic", "time": "4-7 PM", "broadAppeal": True},
            {"day": "Saturday", "type": "acoustic", "time": "4-7 PM", "broadAppeal": True},
            {"day": "Sunday", "type": "acoustic", "time": "3-6 PM", "broadAppeal": True},
        ],
    },
    {
        "name": "Del Mar Plaza", "area": "Del Mar",
        "repeatFriendly": True, "conversationFriendly": True, "energy": "medium",
        "events": [
            {"day": "Thursday", "type": "Seaside Sessions", "time": "5-7 PM", "broadAppeal": True},
            {"day": "Saturday", "type": "Seaside Sessions", "time": "5-7 PM", "broadAppeal": True},
        ],
    },
    {
        "name": "Jake's Del Mar", "area": "Del Mar",
        "repeatFriendly": True, "conversationFriendly": True, "energy": "medium",
        "happyHour": {"days": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "start": "3:00 PM", "end": "6:00 PM"},
        "events": [
            {"day": "Friday", "type": "happy hour", "time": "4-6 PM", "broadAppeal": True},
            {"day": "Saturday", "type": "sunset crowd", "time": "5-8 PM", "broadAppeal": True},
            {"day": "Sunday", "type": "brunch into afternoon", "time": "11 AM-3 PM", "broadAppeal": True},
        ],
    },
    {
        "name": "Belly Up Tavern", "area": "Solana Beach",
        "repeatFriendly": False, "conversationFriendly": False, "energy": "high",
        "events": [
            {"day": "Thursday", "type": "rock headliner", "time": "8:00 PM", "broadAppeal": False},
            {"day": "Friday", "type": "80s dance night", "time": "8:00 PM", "broadAppeal": True},
            {"day": "Saturday", "type": "tribute band", "time": "8:00 PM", "broadAppeal": True},
            {"day": "Sunday", "type": "Sunday residency", "time": "7:00 PM", "broadAppeal": False},
        ],
    },
    {
        "name": "Union Kitchen & Tap", "area": "Encinitas",
        "repeatFriendly": True, "conversationFriendly": True, "energy": "medium",
        "happyHour": {"days": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "start": "3:00 PM", "end": "5:00 PM"},
        "events": [
            {"day": "Wednesday", "type": "happy hour", "time": "5-7 PM", "broadAppeal": True},
            {"day": "Thursday", "type": "happy hour", "time": "5-7 PM", "broadAppeal": True},
            {"day": "Friday", "type": "DJ late set", "time": "9 PM-close", "broadAppeal": True},
        ],
    },
    {
        "name": "The Saloon", "area": "Encinitas",
        "repeatFriendly": True, "conversationFriendly": False, "energy": "high",
        "events": [
            {"day": "Friday", "type": "live band", "time": "9:00 PM", "broadAppeal": True},
            {"day": "Saturday", "type": "live band", "time": "9:00 PM", "broadAppeal": True},
        ],
    },
    {
        "name": "Moonlight Beach Bar", "area": "Encinitas",
        "repeatFriendly": False, "conversationFriendly": False, "energy": "high",
        "events": [
            {"day": "Saturday", "type": "DJ night", "time": "9:00 PM", "broadAppeal": False},
        ],
    },
    {
        "name": "1st Street Bar", "area": "Encinitas",
        "repeatFriendly": True, "conversationFriendly": True, "energy": "medium",
        "happyHour": {"days": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "start": "3:00 PM", "end": "6:00 PM"},
        "events": [
            {"day": "Tuesday", "type": "neighborhood night", "time": "7-10 PM", "broadAppeal": True},
            {"day": "Thursday", "type": "neighborhood night", "time": "7-10 PM", "broadAppeal": True},
            {"day": "Sunday", "type": "locals day", "time": "3-7 PM", "broadAppeal": True},
        ],
    },
    {
        "name": "Campfire", "area": "Carlsbad",
        "repeatFriendly": True, "conversationFriendly": True, "energy": "medium",
        "happyHour": {"days": ["Tuesday","Wednesday","Thursday","Friday"], "start": "4:00 PM", "end": "6:00 PM"},
        "events": [
            {"day": "Friday", "type": "patio scene", "time": "6-9 PM", "broadAppeal": True},
            {"day": "Saturday", "type": "patio scene", "time": "6-9 PM", "broadAppeal": True},
        ],
    },
    {
        "name": "Park 101", "area": "Carlsbad",
        "repeatFriendly": False, "conversationFriendly": False, "energy": "high",
        "events": [
            {"day": "Friday", "type": "outdoor DJ", "time": "8:00 PM", "broadAppeal": True},
            {"day": "Saturday", "type": "outdoor DJ", "time": "8:00 PM", "broadAppeal": True},
        ],
    },
]

# ─── Featured venues (always shown in plan when they have events) ────────────

# Monarch Ocean Pub is inside Del Mar Plaza — same physical location.
# Show as one featured entry under "Del Mar Plaza / Monarch".
FEATURED_VENUES = ["Belly Up Tavern", "Del Mar Plaza / Monarch"]

# Map for featured venue lookups (check both names)
FEATURED_VENUE_LOOKUPS = {
    "Del Mar Plaza / Monarch": ["Monarch Ocean Pub", "Del Mar Plaza"],
    "Belly Up Tavern": ["Belly Up Tavern"],
}

# ─── Priority map (weekly rhythm from NOTIFICATION_SPEC) ─────────────────────

PRIORITY_MAP = {
    "Thursday": "High",   # Del Mar Plaza Seaside Sessions
    "Saturday": "High",   # Del Mar Plaza Seaside Sessions
    "Friday": "High",     # Multiple strong options
    "Wednesday": "Medium", # Monarch + Cedros
    "Sunday": "Medium",   # Monarch + optional Cedros
    "Tuesday": "Low",
    "Monday": "Low",
}

# ─── Scoring (mirrors src/scoring.ts) ────────────────────────────────────────

GOAL = "both"
VIBE = "balanced"


def score_venue(venue, event, happy_hour_on_this_day=False):
    """Score a venue+event pair. Returns (score, reason).

    Prioritizes repeat-friendly conversational venues — the 'become a
    regular' strategy. Energy is a smaller factor; dating goal penalizes
    anonymous high-energy spots.
    """
    score = 5  # event exists
    reasons = []

    # BIGGEST BOOST: places you can become a regular
    if venue["repeatFriendly"]:
        score += 4
        reasons.append("Become a regular here")

    if venue["conversationFriendly"]:
        score += 3
        reasons.append("Conversation-friendly")

    # Happy hour + regular-friendly = prime time
    if happy_hour_on_this_day and venue["repeatFriendly"]:
        score += 2
        if not reasons:
            reasons.append("Happy hour regulars")

    # Energy: prefer medium (conversational) over high
    if venue["energy"] == "medium":
        score += 1
    elif venue["energy"] == "high":
        if GOAL == "social":
            score += 1
        if GOAL == "dating":
            score -= 2

    if event["broadAppeal"]:
        score += 1

    if venue.get("lowSocialValue"):
        score -= 3

    if VIBE == "quiet" and venue["energy"] == "high":
        score -= 3
    if VIBE == "high" and venue["energy"] == "low":
        score -= 2

    # Dating penalties
    if GOAL == "dating" and not venue["repeatFriendly"]:
        score -= 3
    if GOAL == "dating" and not venue["conversationFriendly"]:
        score -= 2

    return score, reasons[0] if reasons else "Decent local option"


def grade_for(score):
    if score >= 8:
        return "A"
    if score >= 5:
        return "B"
    return "C"


def decision_for(grade):
    return {"A": "GO", "B": "MAYBE", "C": "SKIP"}[grade]


# ─── Scraped events ──────────────────────────────────────────────────────────

SCRAPED_FILE = PROJECT_ROOT / "data" / "scraped_events.json"


def load_scraped_events(for_date: date) -> list[dict]:
    """Load scraped events for a specific date."""
    if not SCRAPED_FILE.exists():
        return []
    try:
        data = json.loads(SCRAPED_FILE.read_text())
        events = data.get("events", [])
        date_str = for_date.isoformat()
        return [e for e in events if e.get("date") == date_str]
    except (json.JSONDecodeError, KeyError):
        return []


# ─── Plan generation ─────────────────────────────────────────────────────────

def generate_plan(today=None, home_area=None, zones=None):
    """Generate the daily Social Plan. Returns a dict with all plan fields."""
    if today is None:
        today = date.today()
    if home_area is None:
        home_area = DEFAULT_HOME_AREA
    if zones is None:
        zones = AREAS.get(home_area, [])

    day_name = DAY_NAMES[today.weekday() + 1] if today.weekday() < 6 else "Sunday"
    # Fix: use Python's weekday (0=Mon) mapped to our DAY_NAMES (0=Sun)
    day_name = DAY_NAMES[(today.weekday() + 1) % 7]
    # Actually Python weekday: Mon=0..Sun=6. We need to map to JS-style: Sun=0..Sat=6
    py_weekday = today.weekday()  # Mon=0, Tue=1, ..., Sun=6
    js_weekday = (py_weekday + 1) % 7  # Sun=0, Mon=1, ..., Sat=6
    day_name = DAY_NAMES[js_weekday]

    allowed_areas = {home_area} | set(zones)
    priority = PRIORITY_MAP.get(day_name, "Low")

    # Load scraped events for today FIRST — we use them to enrich static venues
    scraped = load_scraped_events(today)
    scraped_for_area = [e for e in scraped if e.get("area") in allowed_areas]

    # Extract Monarch performer from scraped data (Del Mar Plaza lists them as
    # "Live Music – Monarch Ocean Pub – Lee Melton"). These replace the generic
    # "acoustic" placeholder in static data.
    monarch_performer = None
    seaside_performer = None
    other_scraped = []
    seen_artists = set()

    for ev in scraped_for_area:
        title = ev.get("title", "")
        title_lower = title.lower()

        # Monarch performer extraction
        if "monarch ocean pub" in title_lower and "–" in title:
            # "Live Music – Monarch Ocean Pub – Lee Melton" → "Lee Melton"
            parts = title.split("–")
            if len(parts) >= 3:
                monarch_performer = parts[-1].strip()
            elif len(parts) >= 2:
                monarch_performer = parts[-1].strip()
            continue  # Don't add as separate scraped event

        # Seaside Sessions extraction
        if "seaside sessions" in title_lower:
            # "Seaside Sessions – Ben Powell" or "Seaside Sessions: Ben Powell (genre)"
            for sep in ["–", ":", "-"]:
                if sep in title:
                    seaside_performer = title.split(sep, 1)[-1].strip()
                    break
            continue  # Don't add as separate scraped event

        # Dedupe same artist on same date
        artist_key = re.sub(r'\s*[-–—:].+', '', title_lower).strip()
        if artist_key in seen_artists:
            continue
        seen_artists.add(artist_key)

        other_scraped.append(ev)

    scraped_for_area = other_scraped

    # Score all venues with today's events OR happy hour on this day
    candidates = []
    for venue in VENUES:
        if venue["area"] not in allowed_areas:
            continue
        day_events = [e for e in venue["events"] if e["day"] == day_name]
        has_hh = venue.get("happyHour") and day_name in venue["happyHour"]["days"]

        if not day_events and not has_hh:
            continue

        # Build the event entry (use real event if available, else synthesize from HH)
        if day_events:
            event = day_events[0]
            event_type = event["type"]
            if venue["name"] == "Monarch Ocean Pub" and monarch_performer:
                event_type = monarch_performer
            if venue["name"] == "Del Mar Plaza" and seaside_performer:
                event_type = f"Seaside Sessions: {seaside_performer}"
            event_time = event["time"]
        else:
            hh = venue["happyHour"]
            event = {"day": day_name, "type": "happy hour", "time": f"{hh['start']}-{hh['end']}", "broadAppeal": True}
            event_type = "happy hour"
            event_time = f"{hh['start']}-{hh['end']}"

        hh_note = None
        if has_hh:
            hh = venue["happyHour"]
            hh_note = f"Happy hour {hh['start']}-{hh['end']}"

        score, reason = score_venue(venue, event, happy_hour_on_this_day=has_hh)
        grade = grade_for(score)
        candidates.append({
            "venue": venue["name"],
            "area": venue["area"],
            "time": event_time,
            "event_type": event_type,
            "score": score,
            "grade": grade,
            "decision": decision_for(grade),
            "reason": reason,
            "energy": venue["energy"],
            "conversationFriendly": venue["conversationFriendly"],
            "repeatFriendly": venue["repeatFriendly"],
            "happy_hour_note": hh_note,
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Featured venue notes (always included), enriched with scraped data
    featured_notes = {}
    for fname in FEATURED_VENUES:
        lookup_names = FEATURED_VENUE_LOOKUPS.get(fname, [fname])
        notes = []
        for lname in lookup_names:
            venue_data = next((v for v in VENUES if v["name"] == lname), None)
            if not venue_data:
                continue
            day_events = [e for e in venue_data["events"] if e["day"] == day_name]
            if day_events:
                ev = day_events[0]
                event_desc = ev["type"]
                if lname == "Monarch Ocean Pub" and monarch_performer:
                    event_desc = monarch_performer
                if lname == "Del Mar Plaza" and seaside_performer:
                    event_desc = f"Seaside Sessions: {seaside_performer}"
                notes.append(f"{event_desc} — {ev['time']}")
        if notes:
            featured_notes[fname] = " + ".join(notes)
        else:
            featured_notes[fname] = "No events tonight"

    # Area string
    area_str = home_area
    if zones:
        area_str = f"{home_area} / {' / '.join(zones[:2])}"

    # Scraped events as candidates (score them generously — they're real, timely data)
    scraped_candidates = []
    for ev in scraped_for_area:
        score = 6  # base: real event, confirmed happening
        reasons = []
        if ev.get("big_event"):
            score += 4
            reasons.append("Major event — worth the trip")
        if ev.get("category") == "live_music_small":
            score += 2
            reasons.append("Live music tonight")
        elif ev.get("category") in ("markets", "food_drink"):
            score += 1
            reasons.append("Social food/market scene")
        if ev.get("venue") in ("Belly Up Tavern", "Del Mar Plaza"):
            score += 1

        # DEL MAR FAIRGROUNDS: 1/2 mile from home — always prioritize
        if "fairgrounds" in ev.get("venue", "").lower() or ev.get("venue") == "Del Mar Racetrack":
            score += 3
            if not reasons:
                reasons.append("Right in your backyard")
            elif "backyard" not in reasons[0].lower():
                reasons[0] = f"{reasons[0]} — local to you"

        grade = grade_for(score)
        scraped_candidates.append({
            "venue": ev.get("venue", "Unknown"),
            "area": ev.get("area", ""),
            "time": ev.get("time", ""),
            "event_type": ev.get("title", ""),
            "score": score,
            "grade": grade,
            "decision": decision_for(grade),
            "reason": reasons[0] if reasons else "Confirmed local event",
            "energy": "high" if ev.get("big_event") else "medium",
            "conversationFriendly": ev.get("category") not in ("live_music_small",),
            "repeatFriendly": False,
            "source": ev.get("source", ""),
            "big_event": ev.get("big_event", False),
        })

    # Merge venue candidates + scraped, sort by score
    all_candidates = candidates + scraped_candidates
    all_candidates.sort(key=lambda x: x["score"], reverse=True)

    # Venues that are the same physical location (dedupe together)
    SAME_LOCATION = {
        "monarch ocean pub": "del mar plaza",
        "del mar plaza": "del mar plaza",
        "del mar plaza (ocean view deck)": "del mar plaza",
    }

    # Dedupe by physical location (keep highest-scored entry per location)
    seen_locations = set()
    deduped = []
    for c in all_candidates:
        vkey = c["venue"].lower()
        location_key = SAME_LOCATION.get(vkey, vkey)
        if location_key in seen_locations:
            continue
        seen_locations.add(location_key)
        deduped.append(c)

    # Top 5 picks (or fewer if not enough candidates)
    MAX_PICKS = 5
    picks = deduped[:MAX_PICKS]

    # Overall call: use #1 pick's decision, or SKIP if nothing
    if picks and picks[0]["decision"] == "GO":
        call = "GO"
    elif picks and picks[0]["decision"] == "MAYBE":
        call = "MAYBE"
    else:
        call = "SKIP"

    # Bump priority if there's a big event today
    if any(c.get("big_event") for c in all_candidates):
        priority = "High"

    crowd_grade = picks[0]["grade"] if picks else "C"

    return {
        "date": today.isoformat(),
        "day_name": day_name,
        "area_str": area_str,
        "home_area": home_area,
        "priority": priority,
        "has_events": len(picks) > 0,
        "picks": picks,
        "featured_notes": featured_notes,
        "call": call,
        "crowd_grade": crowd_grade,
        "all_candidates": all_candidates,
        "scraped_count": len(scraped_for_area),
    }


def _crowd_desc(pick):
    """Build a short crowd description string."""
    parts = []
    if pick.get("conversationFriendly"):
        parts.append("conversational")
    if pick.get("repeatFriendly"):
        parts.append("repeat-friendly")
    if pick.get("energy") == "high":
        parts.append("high energy")
    elif pick.get("energy") == "medium":
        parts.append("relaxed vibe")
    return ", ".join(parts) if parts else "standard"


def format_full_plan(plan):
    """Format the plan as the full Social Plan text (for email)."""
    lines = []
    lines.append(f"TODAY: {plan['day_name']} — {plan['area_str']} Social Plan")
    lines.append("")

    if not plan["has_events"]:
        lines.append("No events today.")
        lines.append("No strong nearby social options matched today.")
        return "\n".join(lines)

    # Numbered picks (up to 5)
    picks = plan["picks"]
    labels = ["#1 Top Pick", "#2", "#3", "#4", "#5"]

    for i, pick in enumerate(picks):
        label = labels[i] if i < len(labels) else f"#{i+1}"
        big = "  *** BIG EVENT ***" if pick.get("big_event") else ""
        lines.append(f"{label}: {pick['venue']} — {pick['time']}{big}")
        lines.append(f"  {pick['event_type']}")
        if pick.get("happy_hour_note"):
            lines.append(f"  {pick['happy_hour_note']}")
        lines.append(f"  Crowd: {_crowd_desc(pick)}  |  Grade {pick['grade']}  |  {pick['decision']}")
        lines.append(f"  {pick['reason']}")
        lines.append("")

    # Featured venue notes (only if not already in picks)
    pick_venues = {p["venue"] for p in picks}
    featured_shown = False
    for fname, note in plan["featured_notes"].items():
        if fname in pick_venues:
            continue
        if not featured_shown:
            lines.append("Venue Notes:")
            featured_shown = True
        lines.append(f"  {fname}: {note}")
    if featured_shown:
        lines.append("")

    # Summary line
    lines.append(f"Call: {plan['call']}  |  Crowd Grade: {plan['crowd_grade']}  |  Priority: {plan['priority']}")
    lines.append("")
    lines.append("Log last night: https://dlhackbart.github.io/localsocial/")

    return "\n".join(lines)


def _short_venue(name):
    """Shorten venue name for SMS."""
    return (name
            .replace("Ocean Pub", "")
            .replace("Tavern", "")
            .replace(" (Ocean View Deck)", "")
            .replace("Downtown ", "")
            .replace("(Hwy 101)", "")
            .strip())


def format_sms(plan):
    """Format a short SMS-friendly version (under 160 chars)."""
    if not plan["has_events"]:
        return f"{plan['day_name']}: No events today."

    picks = plan["picks"]
    short_day = plan["day_name"][:3]

    # First line: top pick + overall call
    p = picks[0]
    msg = f"{short_day}: 1){_short_venue(p['venue'])} {p['time']}"

    # Add picks 2-3 if they fit
    for i, pick in enumerate(picks[1:3], start=2):
        addition = f" {i}){_short_venue(pick['venue'])} {pick['time']}"
        if len(msg) + len(addition) + 25 <= 160:  # reserve space for call line
            msg += addition

    msg += f" | {plan['call']}, {plan['priority']}"

    # Add log link if it fits
    log_note = " | Log: dlhackbart.github.io/localsocial"
    if len(msg) + len(log_note) <= 160:
        msg += log_note

    return msg[:160]


def generate_weekly_plan(start_date=None, home_area=None, zones=None):
    """Generate plans for 7 days starting from start_date."""
    if start_date is None:
        start_date = date.today()
    from datetime import timedelta
    plans = []
    for offset in range(7):
        day = start_date + timedelta(days=offset)
        plan = generate_plan(today=day, home_area=home_area, zones=zones)
        plans.append(plan)
    return plans


def _format_day_picks(plan, is_today=False):
    """Format picks for a single day. Used by both tonight and upcoming days."""
    lines = []

    if is_today:
        header = f"TONIGHT: {plan['day_name']} — {plan['area_str']}"
    else:
        # Show date for upcoming days
        header = f"{plan['day_name'].upper()} {plan['date'][5:]}"  # e.g. "FRIDAY 04/18"

    priority_tag = f"  [{plan['priority']} priority]" if plan["priority"] != "Low" else ""
    lines.append(f"{header}{priority_tag}")

    if not plan["has_events"]:
        lines.append("  No events.")
        lines.append("")
        return lines

    picks = plan["picks"]
    for i, pick in enumerate(picks):
        num = i + 1
        big = " ***" if pick.get("big_event") else ""
        hh = f"  [HH {pick['happy_hour_note'].replace('Happy hour ', '')}]" if pick.get("happy_hour_note") else ""
        lines.append(f"  {num}. {pick['venue']} — {pick['time']}{big}{hh}")
        lines.append(f"     {pick['event_type']}")
        lines.append(f"     {_crowd_desc(pick)}  |  Grade {pick['grade']}  |  {pick['decision']}")

    # Featured venue notes (only if not in picks)
    pick_venues = {p["venue"] for p in picks}
    for fname, note in plan["featured_notes"].items():
        if fname not in pick_venues and "no events" not in note.lower():
            lines.append(f"  {fname}: {note}")

    lines.append("")
    return lines


def format_weekly_plan(plans):
    """Format the full 7-day Social Plan (for email)."""
    lines = []

    today_plan = plans[0]
    lines.append(f"WEEKLY SOCIAL PLAN — {today_plan['area_str']}")
    lines.append(f"Generated {today_plan['date']}")
    lines.append("=" * 50)
    lines.append("")

    # Tonight — full detail with reasons
    lines.append(f"TONIGHT: {today_plan['day_name']}")
    lines.append("-" * 40)

    if not today_plan["has_events"]:
        lines.append("No events today.")
        lines.append("")
    else:
        picks = today_plan["picks"]
        labels = ["#1 Top Pick", "#2", "#3", "#4", "#5"]
        for i, pick in enumerate(picks):
            label = labels[i] if i < len(labels) else f"#{i+1}"
            big = "  *** BIG EVENT ***" if pick.get("big_event") else ""
            lines.append(f"{label}: {pick['venue']} — {pick['time']}{big}")
            lines.append(f"  {pick['event_type']}")
            lines.append(f"  Crowd: {_crowd_desc(pick)}  |  Grade {pick['grade']}  |  {pick['decision']}")
            lines.append(f"  {pick['reason']}")
            lines.append("")

        # Featured venue notes
        pick_venues = {p["venue"] for p in picks}
        for fname, note in today_plan["featured_notes"].items():
            if fname not in pick_venues:
                lines.append(f"{fname}: {note}")
        lines.append("")

        lines.append(f"Call: {today_plan['call']}  |  Grade: {today_plan['crowd_grade']}  |  Priority: {today_plan['priority']}")
        lines.append("")

    # Upcoming 6 days — compact format
    lines.append("=" * 50)
    lines.append("COMING UP")
    lines.append("=" * 50)
    lines.append("")

    for plan in plans[1:]:
        lines.extend(_format_day_picks(plan, is_today=False))

    lines.append("Log last night: https://dlhackbart.github.io/localsocial/")

    return "\n".join(lines)


def format_log_prompt():
    """Format the 9:30 PM logging prompt SMS."""
    return "Did you go out tonight? Reply with venue name + crowd grade (A/B/C) + would go again (yes/maybe/no)"


if __name__ == "__main__":
    if "--week" in sys.argv or "--weekly" in sys.argv:
        plans = generate_weekly_plan()
        print(format_weekly_plan(plans))
        print()
        print("--- SMS (tonight only) ---")
        print(format_sms(plans[0]))
    elif "--json" in sys.argv:
        plan = generate_plan()
        output = {k: v for k, v in plan.items() if k != "all_candidates"}
        print(json.dumps(output, indent=2))
    else:
        plan = generate_plan()
        print(format_full_plan(plan))
        print()
        print("--- SMS ---")
        print(format_sms(plan))
