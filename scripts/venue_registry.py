"""
Venue URL registry — a JSON-backed catalog of venue homepages + discovered subpages.

Each scrape run can:
  1. Load the registry
  2. Fetch every known URL per venue (seed + discovered)
  3. Find new event-relevant subpages (/events, /calendar, /happy-hour, etc.)
  4. Add those to the registry for future runs
  5. Track per-URL success/failure → prune consistently-failing URLs

Schema (data/venue_urls.json):
{
  "version": 1,
  "updated_at": "ISO timestamp",
  "venues": {
    "Jake's Del Mar": {
      "area": "Del Mar",
      "added_at": "ISO date",
      "urls": {
        "https://www.jakesdelmar.com": {
          "source": "seed" | "discovered" | "candidate_approved",
          "discovered_at": "ISO date",
          "last_success": "ISO date" | null,
          "last_failure": "ISO date" | null,
          "fail_count": int
        }
      }
    }
  }
}
"""

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
REGISTRY_FILE = DATA_DIR / "venue_urls.json"

# Failed fetches before a URL is considered dormant (still kept but not fetched)
DEAD_URL_THRESHOLD = 3

# Seed venues — used on first run if registry file doesn't exist.
# Each tuple is (area, seed_url, description). The description is the
# "what's attractive about this spot" one-liner surfaced in email output.
SEED_VENUES = {
    "Torrey Pines Gliderport": (
        "Del Mar", "https://flytorrey.com/event-calendar",
        "Cliffhanger Bar on the ocean cliffs. HH Mon-Thu 4-5 PM with $6 wine/beer. Paragliders + sunset views.",
    ),
    "Jake's Del Mar": (
        "Del Mar", "https://www.jakesdelmar.com",
        "Beachfront Del Mar patio — oceanfront bar, regular locals. HH Mon-Fri 3-6 PM, Sunday brunch into afternoon.",
    ),
    "Kitchen 1540 (L'Auberge)": (
        "Del Mar", "https://www.laubergedelmar.com/dining/kitchen-1540",
        "Upscale resort bar at L'Auberge Del Mar. Craft cocktails + light food. HH Mon-Thu 3-5 PM. Live music most nights.",
    ),
    "Pillbox Tavern": (
        "Solana Beach", "https://www.pillboxtavern.com",
        "Neighborhood beach bar above Fletcher Cove. HH Mon-Fri 3-6 PM. Burger Mondays, weekend brunch crowd.",
    ),
    "Union Kitchen & Tap": (
        "Encinitas", "https://www.localunion101.com",
        "Downtown Encinitas gastropub. Social Hour Mon-Fri 3-5 PM, weekend brunch 10-2, Friday DJ late set.",
    ),
    "Campfire": (
        "Carlsbad", "https://www.thisiscampfire.com",
        "Carlsbad patio with fire pits — conversation-friendly. HH Tue-Fri 4-6 PM.",
    ),
    "Park 101": (
        "Carlsbad", "https://www.park101.com",
        "Carlsbad outdoor beer garden. Fri/Sat outdoor DJ 8 PM — high-energy patio scene.",
    ),
}

# URL path fragments that suggest an event-relevant subpage
EVENT_PATH_HINTS = [
    "event", "events", "calendar", "schedule", "shows", "live",
    "entertainment", "music", "live-music", "livemusic", "happy-hour",
    "happyhour", "specials", "whats-on", "whatson", "bar", "drink",
    "booking", "lineup", "line-up", "tickets",
]

# Paths to exclude even if they match (reservation systems, static assets, etc.)
EXCLUDED_PATH_SUBSTRS = [
    "reservation", "booking/new", "/cart", "/checkout", "/account",
    "/login", "/signup", ".pdf", ".jpg", ".png", ".gif", ".ico", ".css", ".js",
    "mailto:", "tel:", "facebook.com", "instagram.com", "twitter.com",
    "yelp.com", "opentable.com", "resy.com", "tock.com",
]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now().date().isoformat()


def load() -> dict:
    """Load registry from disk. Seed from SEED_VENUES on first run."""
    if not REGISTRY_FILE.exists():
        reg = {"version": 1, "updated_at": _now_iso(), "venues": {}}
        for name, seed in SEED_VENUES.items():
            # Support both legacy (area, url) and new (area, url, description)
            if len(seed) == 3:
                area, url, desc = seed
            else:
                area, url = seed
                desc = ""
            add_venue(reg, name, area, url, source="seed", description=desc)
        save(reg)
        return reg
    try:
        return json.loads(REGISTRY_FILE.read_text())
    except json.JSONDecodeError:
        # Corrupted — re-seed but keep a backup
        backup = REGISTRY_FILE.with_suffix(".json.bak")
        REGISTRY_FILE.rename(backup)
        print(f"[REGISTRY] corrupted file backed up to {backup.name}, reseeding")
        return load()


def save(reg: dict):
    reg["updated_at"] = _now_iso()
    REGISTRY_FILE.write_text(json.dumps(reg, indent=2))


def add_venue(reg: dict, name: str, area: str, seed_url: str, source: str = "seed", description: str = ""):
    if name not in reg["venues"]:
        reg["venues"][name] = {
            "area": area,
            "added_at": _today(),
            "description": description,
            "urls": {},
        }
    elif description and not reg["venues"][name].get("description"):
        # Fill in a missing description without overwriting a non-empty one
        reg["venues"][name]["description"] = description
    add_url(reg, name, seed_url, source=source)


def set_description(reg: dict, venue: str, description: str) -> bool:
    """Set or update a venue's description. Returns True on success."""
    if venue not in reg["venues"]:
        return False
    reg["venues"][venue]["description"] = description
    return True


def get_description(reg: dict, venue: str) -> str:
    return reg["venues"].get(venue, {}).get("description", "")


def all_descriptions(reg: dict) -> dict[str, str]:
    """Return {venue_name: description} for every venue that has one."""
    return {
        name: v.get("description", "")
        for name, v in reg["venues"].items()
        if v.get("description")
    }


def add_url(reg: dict, venue: str, url: str, source: str = "discovered") -> bool:
    """Add a URL to a venue. Returns True if it's new."""
    if venue not in reg["venues"]:
        return False
    urls = reg["venues"][venue]["urls"]
    if url in urls:
        return False
    urls[url] = {
        "source": source,
        "discovered_at": _today(),
        "last_success": None,
        "last_failure": None,
        "fail_count": 0,
    }
    return True


def mark_success(reg: dict, venue: str, url: str):
    entry = reg["venues"].get(venue, {}).get("urls", {}).get(url)
    if entry is None:
        return
    entry["last_success"] = _today()
    entry["fail_count"] = 0


def mark_failure(reg: dict, venue: str, url: str):
    entry = reg["venues"].get(venue, {}).get("urls", {}).get(url)
    if entry is None:
        return
    entry["last_failure"] = _today()
    entry["fail_count"] = entry.get("fail_count", 0) + 1


def is_dead(entry: dict) -> bool:
    return entry.get("fail_count", 0) >= DEAD_URL_THRESHOLD


def live_urls_for(reg: dict, venue: str) -> list[str]:
    """Return URLs we should still try fetching (not dormant)."""
    urls = reg["venues"].get(venue, {}).get("urls", {})
    return [u for u, entry in urls.items() if not is_dead(entry)]


def venues(reg: dict) -> list[str]:
    return list(reg["venues"].keys())


def venue_area(reg: dict, venue: str) -> str:
    return reg["venues"].get(venue, {}).get("area", "")


# ─── Subpage discovery ───────────────────────────────────────────────────────

def discover_subpage_urls(html: str, base_url: str) -> set[str]:
    """Find links in `html` that point to event-relevant subpages on the same domain."""
    if not html:
        return set()
    base_host = urlparse(base_url).netloc.lower().removeprefix("www.")
    hrefs = re.findall(r'href\s*=\s*["\']([^"\']+)["\']', html, re.IGNORECASE)
    found: set[str] = set()
    for href in hrefs:
        href_l = href.strip().lower()
        if not href_l or href_l.startswith("#") or href_l.startswith("javascript:"):
            continue
        if any(bad in href_l for bad in EXCLUDED_PATH_SUBSTRS):
            continue
        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)
        # Only follow same-domain links
        host = parsed.netloc.lower().removeprefix("www.")
        if host != base_host:
            continue
        path = parsed.path.lower()
        if path in ("", "/"):
            continue
        if not any(hint in path for hint in EVENT_PATH_HINTS):
            continue
        # Strip fragment, keep query (some sites use ?p=events)
        clean = abs_url.split("#")[0]
        found.add(clean)
    return found


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _cli_list(reg: dict):
    for name in sorted(reg["venues"].keys()):
        v = reg["venues"][name]
        print(f"{name}  [{v['area']}]")
        if v.get("description"):
            print(f"  desc: {v['description']}")
        for url, entry in v["urls"].items():
            status = "DEAD" if is_dead(entry) else "live"
            src = entry["source"]
            fails = entry["fail_count"]
            print(f"  [{status}][{src}] {url}  fails={fails}")


def _cli_add(reg: dict, name: str, area: str, url: str, description: str = ""):
    add_venue(reg, name, area, url, source="manual", description=description)
    save(reg)
    desc_tail = f" — {description}" if description else ""
    print(f"[REGISTRY] added {name} ({area}) → {url}{desc_tail}")


def _cli_describe(reg: dict, name: str, description: str):
    if set_description(reg, name, description):
        save(reg)
        print(f"[REGISTRY] description set for {name}")
    else:
        print(f"[REGISTRY] {name} not found — add it first")


def _cli_remove(reg: dict, name: str):
    if name in reg["venues"]:
        del reg["venues"][name]
        save(reg)
        print(f"[REGISTRY] removed {name}")
    else:
        print(f"[REGISTRY] {name} not found")


def _cli_prune(reg: dict):
    """Permanently delete URLs that have been dead for a while (optional cleanup)."""
    removed = 0
    for name, v in reg["venues"].items():
        dead = [u for u, entry in v["urls"].items() if is_dead(entry)]
        for u in dead:
            del v["urls"][u]
            removed += 1
    save(reg)
    print(f"[REGISTRY] pruned {removed} dead URLs")


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    reg = load()
    if not args or args[0] == "list":
        _cli_list(reg)
    elif args[0] == "add" and len(args) >= 4:
        desc = args[4] if len(args) >= 5 else ""
        _cli_add(reg, args[1], args[2], args[3], description=desc)
    elif args[0] == "describe" and len(args) >= 3:
        _cli_describe(reg, args[1], args[2])
    elif args[0] == "remove" and len(args) >= 2:
        _cli_remove(reg, args[1])
    elif args[0] == "prune":
        _cli_prune(reg)
    else:
        print("Usage:")
        print("  python venue_registry.py list")
        print('  python venue_registry.py add "Venue Name" "Area" "https://url" ["description"]')
        print('  python venue_registry.py describe "Venue Name" "description text"')
        print('  python venue_registry.py remove "Venue Name"')
        print("  python venue_registry.py prune   # permanently delete dead URLs")
