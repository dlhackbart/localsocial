"""
City event source discovery for Local Social.

Replicates the manual process used to find North County sources:
1. Probe known venue/event page patterns for the city
2. Use Claude Haiku to suggest likely event sources
3. Validate each URL returns real event data
4. Save verified sources to a city config file

This is how we found sources for Del Mar / Solana Beach / Encinitas / Carlsbad:
- Main music venues → scraped event listings (Belly Up)
- Central gathering spots → event calendars (Del Mar Plaza)
- Downtown/main street associations → community events (Encinitas 101)
- Local theaters → show schedules (North Coast Rep)
- City government calendars → civic events (delmar.ca.us)
- Visitor/tourism bureaus → curated events (Visit Carlsbad)
- Newspapers → event sections (SD Union-Tribune — blocked, but pattern exists)

Usage:
    python discover_city.py "Bend, OR"           # Discover sources for Bend
    python discover_city.py "Bend, OR" --dry-run  # Probe without saving
    python discover_city.py --list                 # List all discovered cities
"""

import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_ROOT / "data" / "city_sources"
SOURCES_DIR.mkdir(parents=True, exist_ok=True)


# ─── URL probe patterns ─────────────────────────────────────────────────────
# These are the patterns that work across US cities. Each returns a list of
# candidate URLs to try for a given city.

def build_probe_urls(city: str, state: str) -> list[dict]:
    """Generate candidate event page URLs from common patterns."""
    city_lower = city.lower().replace(" ", "")
    city_dash = city.lower().replace(" ", "-")
    city_space = city.lower()
    state_lower = state.lower()

    candidates = []

    # ─── City government calendars ────────────────────────────────────
    gov_hosts = [
        f"www.{city_lower}.gov",
        f"www.{city_lower}{state_lower}.gov",
        f"www.cityof{city_lower}.org",
        f"www.cityof{city_lower}.com",
        f"www.{city_lower}.{state_lower}.us",
        f"www.ci.{city_lower}.{state_lower}.us",
        f"{city_lower}.gov",
    ]
    for host in gov_hosts:
        # CivicPlus municipal CMS (~3000 US cities)
        for cat_id in [24, 14, 13, 25]:
            candidates.append({
                "url": f"https://{host}/common/modules/iCalendar/iCalendar.aspx?catID={cat_id}&feed=calendar",
                "name": f"{city} City Calendar",
                "type": "city_calendar",
                "category": "community_civic",
                "format": "ical",
            })
        # WordPress Tribe Events
        candidates.append({
            "url": f"https://{host}/events/?ical=1",
            "name": f"{city} City Events",
            "type": "city_calendar",
            "category": "community_civic",
            "format": "ical",
        })
        # Generic calendar page
        candidates.append({
            "url": f"https://{host}/calendar",
            "name": f"{city} City Calendar",
            "type": "city_calendar",
            "category": "community_civic",
            "format": "html",
        })
        candidates.append({
            "url": f"https://{host}/events",
            "name": f"{city} City Events",
            "type": "city_calendar",
            "category": "community_civic",
            "format": "html",
        })

    # ─── Visitor / tourism bureaus ────────────────────────────────────
    tourism_patterns = [
        f"https://www.visit{city_lower}.com/events",
        f"https://www.visit{city_lower}.org/events",
        f"https://visit{city_lower}.com/events",
        f"https://www.{city_lower}chamber.com/events",
        f"https://www.{city_lower}chamber.org/events",
        f"https://www.explore{city_lower}.com/events",
        f"https://www.discover{city_lower}.com/events",
    ]
    for url in tourism_patterns:
        candidates.append({
            "url": url,
            "name": f"Visit {city} Events",
            "type": "tourism",
            "category": "community_civic",
            "format": "html",
        })

    # ─── Downtown / main street associations ──────────────────────────
    downtown_patterns = [
        f"https://www.{city_lower}101.com/events",
        f"https://www.downtown{city_lower}.com/events",
        f"https://www.downtown{city_lower}.org/events",
        f"https://www.{city_lower}downtown.com/events",
        f"https://www.{city_lower}mainstreet.org/events",
        f"https://www.{city_lower}mainstreet.com/events",
    ]
    for url in downtown_patterns:
        candidates.append({
            "url": url,
            "name": f"Downtown {city} Events",
            "type": "downtown_assoc",
            "category": "community_civic",
            "format": "html",
        })

    # ─── Library calendars (LibCal) ───────────────────────────────────
    lib_patterns = [
        f"https://{city_lower}library.libcal.com/ical_subscribe/all",
        f"https://{city_lower}lib.libcal.com/ical_subscribe/all",
        f"https://{city_lower}pl.libcal.com/ical_subscribe/all",
        f"https://{city_lower}publiclibrary.libcal.com/ical_subscribe/all",
    ]
    for url in lib_patterns:
        candidates.append({
            "url": url,
            "name": f"{city} Public Library",
            "type": "library",
            "category": "classes_workshops",
            "format": "ical",
        })

    # ─── Common venue aggregators ─────────────────────────────────────
    # Eventbrite (search page, not scrape-friendly but detectable)
    candidates.append({
        "url": f"https://www.eventbrite.com/d/{state_lower}--{city_dash}/events/",
        "name": f"Eventbrite {city}",
        "type": "aggregator",
        "category": "community_civic",
        "format": "html",
    })

    return candidates


# ─── URL validation ──────────────────────────────────────────────────────────

def probe_url(url: str, expected_format: str = "html") -> dict:
    """Probe a URL and check if it returns useful event data."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "LocalSocial/0.1 (+https://localsocial.app)"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read(50_000).decode("utf-8", errors="replace")

        result = {
            "url": url,
            "status": status,
            "content_type": content_type,
            "reachable": True,
        }

        # Check for iCal content
        if "BEGIN:VCALENDAR" in body:
            event_count = body.count("BEGIN:VEVENT")
            result["format"] = "ical"
            result["has_events"] = event_count > 0
            result["event_count"] = event_count
            return result

        # Check for HTML with event-like content
        if "<html" in body.lower() or "<!doctype" in body.lower():
            result["format"] = "html"
            # Look for event signals in the page
            event_signals = 0
            lower_body = body.lower()
            for signal in ["event", "calendar", "schedule", "tonight", "upcoming",
                          "live music", "concert", "festival", "show", "performance",
                          "ticket", "admission", "doors open", "showtime"]:
                if signal in lower_body:
                    event_signals += 1

            # Check for structured data
            has_json_ld = '"@type":"Event"' in body or '"@type": "Event"' in body
            has_microdata = 'itemtype="http://schema.org/Event"' in body

            result["has_events"] = event_signals >= 3 or has_json_ld or has_microdata
            result["event_signals"] = event_signals
            result["has_structured_data"] = has_json_ld or has_microdata

            # Extract page title
            title_match = re.search(r'<title[^>]*>(.*?)</title>', body, re.IGNORECASE | re.DOTALL)
            if title_match:
                result["page_title"] = title_match.group(1).strip()[:100]

            return result

        result["format"] = "unknown"
        result["has_events"] = False
        return result

    except Exception as e:
        return {
            "url": url,
            "reachable": False,
            "error": str(e)[:200],
        }


# ─── LLM discovery (Claude Haiku) ────────────────────────────────────────────

def llm_discover(city: str, state: str) -> list[dict]:
    """Ask Claude Haiku to suggest event sources for a city."""
    # Try to load API key from spy_timing config
    api_key = None
    try:
        config_path = Path(__file__).resolve().parent.parent.parent / "spy_timing" / "config.py"
        if config_path.exists():
            # Read ANTHROPIC_API_KEY if it exists, otherwise skip
            pass
    except Exception:
        pass

    # Try environment variable
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[LLM] No ANTHROPIC_API_KEY set — skipping LLM discovery")
        return []

    prompt = f"""You are helping a local social events app find event sources for a specific US city.
For {city}, {state}, suggest up to 10 specific websites or pages that list local events.

Focus on:
1. The city's main live music venue(s) — their /events or /calendar page
2. The city's central downtown area / main street — plaza, district, or downtown association event page
3. Community theater companies in or near the city
4. The city government events calendar
5. Visitor bureau / tourism board events page
6. Local newspaper events section
7. Any well-known local festivals, farmers markets, or recurring community events
8. Library event calendars

For each, return:
- "name": display name
- "url": the specific events/calendar page URL (not just the homepage)
- "type": one of "music_venue", "downtown_assoc", "theater", "city_calendar", "tourism", "newspaper", "library", "community"
- "why": one sentence on why this is a good source

Return ONLY a raw JSON array. No markdown, no prose."""

    try:
        data = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())

        text = result.get("content", [{}])[0].get("text", "")
        match = re.search(r'\[[\s\S]*\]', text)
        if not match:
            return []

        suggestions = json.loads(match.group(0))
        return [s for s in suggestions if isinstance(s, dict) and "url" in s]

    except Exception as e:
        print(f"[LLM] Discovery failed: {e}")
        return []


# ─── Main discovery flow ─────────────────────────────────────────────────────

def discover_city(city_label: str, dry_run: bool = False) -> dict:
    """
    Discover event sources for a city.
    city_label: "Bend, OR" or "Austin, TX"
    """
    parts = [p.strip() for p in city_label.split(",")]
    if len(parts) < 2:
        print(f"Error: Use format 'City, ST' (e.g., 'Bend, OR')")
        sys.exit(1)

    city = parts[0]
    state = parts[1]
    slug = f"{city.lower().replace(' ', '-')}-{state.lower()}"

    print(f"\n{'='*60}")
    print(f"DISCOVERING EVENT SOURCES: {city}, {state}")
    print(f"{'='*60}\n")

    # Step 1: Rule-based probing
    print("[PROBE] Generating candidate URLs...")
    probe_candidates = build_probe_urls(city, state)
    print(f"[PROBE] Testing {len(probe_candidates)} URLs...\n")

    verified = []
    for i, cand in enumerate(probe_candidates):
        result = probe_url(cand["url"], cand["format"])
        if result.get("reachable") and result.get("has_events"):
            fmt = result.get("format", "?")
            count = result.get("event_count", "?")
            title = result.get("page_title", "")
            print(f"  FOUND: {cand['url']}")
            print(f"         format={fmt}, events={count}, title={title}")
            verified.append({
                **cand,
                "verified": True,
                "format_detected": fmt,
                "event_count": result.get("event_count"),
                "page_title": result.get("page_title"),
                "has_structured_data": result.get("has_structured_data", False),
            })

        # Progress indicator (every 10 URLs)
        if (i + 1) % 10 == 0:
            print(f"  ... probed {i+1}/{len(probe_candidates)} URLs, {len(verified)} found so far")

    print(f"\n[PROBE] Found {len(verified)} sources from {len(probe_candidates)} probes\n")

    # Step 2: LLM discovery
    print("[LLM] Asking Claude for additional sources...")
    llm_suggestions = llm_discover(city, state)
    print(f"[LLM] Got {len(llm_suggestions)} suggestions\n")

    # Validate LLM suggestions
    llm_verified = []
    seen_urls = {v["url"] for v in verified}
    for sug in llm_suggestions:
        url = sug.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        result = probe_url(url)
        if result.get("reachable"):
            has_events = result.get("has_events", False)
            status_icon = "FOUND" if has_events else "reachable (no events detected)"
            print(f"  {status_icon}: {url}")
            if sug.get("why"):
                print(f"         Reason: {sug['why']}")
            llm_verified.append({
                "url": url,
                "name": sug.get("name", f"{city} Events"),
                "type": sug.get("type", "community"),
                "category": "community_civic",
                "format": "html",
                "verified": has_events,
                "llm_suggested": True,
                "why": sug.get("why", ""),
                "has_structured_data": result.get("has_structured_data", False),
                "page_title": result.get("page_title"),
            })

    all_sources = verified + llm_verified

    # Build output
    output = {
        "city": city,
        "state": state,
        "slug": slug,
        "label": f"{city}, {state}",
        "discovered_at": datetime.now().isoformat(),
        "probe_count": len(probe_candidates),
        "llm_suggestion_count": len(llm_suggestions),
        "sources": all_sources,
        "verified_count": len([s for s in all_sources if s.get("verified")]),
    }

    print(f"\n{'='*60}")
    print(f"RESULTS: {city}, {state}")
    print(f"{'='*60}")
    print(f"  Probed: {len(probe_candidates)} URLs")
    print(f"  LLM suggestions: {len(llm_suggestions)}")
    print(f"  Total sources found: {len(all_sources)}")
    print(f"  Verified with events: {output['verified_count']}")

    if all_sources:
        print(f"\n  Sources:")
        for s in all_sources:
            verified_str = "VERIFIED" if s.get("verified") else "reachable"
            llm_str = " (LLM)" if s.get("llm_suggested") else ""
            print(f"    [{verified_str}]{llm_str} {s['name']}")
            print(f"      {s['url']}")
    else:
        print(f"\n  No sources found. Try adding sources manually or check the city name.")

    if not dry_run:
        output_file = SOURCES_DIR / f"{slug}.json"
        output_file.write_text(json.dumps(output, indent=2))
        print(f"\n  Saved: {output_file}")

    return output


def list_cities():
    """List all discovered cities."""
    files = sorted(SOURCES_DIR.glob("*.json"))
    if not files:
        print("No cities discovered yet. Run: python discover_city.py 'City, ST'")
        return

    print(f"\nDiscovered cities ({len(files)}):\n")
    for f in files:
        data = json.loads(f.read_text())
        verified = data.get("verified_count", 0)
        total = len(data.get("sources", []))
        print(f"  {data.get('label', f.stem)}: {verified} verified, {total} total sources")
        print(f"    File: {f}")


if __name__ == "__main__":
    if "--list" in sys.argv:
        list_cities()
        sys.exit(0)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv

    if not args:
        print("Usage:")
        print("  python discover_city.py 'City, ST'           # Discover sources")
        print("  python discover_city.py 'City, ST' --dry-run  # Probe without saving")
        print("  python discover_city.py --list                 # List discovered cities")
        print()
        print("Examples:")
        print("  python discover_city.py 'Bend, OR'")
        print("  python discover_city.py 'Austin, TX'")
        print("  python discover_city.py 'Asheville, NC'")
        sys.exit(1)

    discover_city(args[0], dry_run=dry_run)
