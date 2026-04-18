"""
New-venue discovery — asks Claude Haiku for bars/restaurants/venues we don't
already track in our target North County areas, validates each candidate URL,
and writes them to data/venue_candidates.json for manual review.

Approved candidates get promoted into the venue registry (data/venue_urls.json)
and picked up on the next daily scrape.

Usage:
    python discover_venues.py                    # Run discovery for all target areas
    python discover_venues.py --area Encinitas   # Just one area
    python discover_venues.py --list             # Show pending candidates
    python discover_venues.py --approve "Name"   # Promote candidate → registry
    python discover_venues.py --reject "Name"    # Remove candidate
    python discover_venues.py --approve-all      # Promote every pending candidate

Designed to be run weekly (not daily) as a scheduled task — the API cost and
the signal-to-noise ratio both argue for less-frequent runs.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
CANDIDATES_FILE = DATA_DIR / "venue_candidates.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venue_registry

TARGET_AREAS = ["Del Mar", "Solana Beach", "Encinitas", "Carlsbad"]
MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now().date().isoformat()


def _load_api_key() -> str | None:
    """Look for ANTHROPIC_API_KEY in env or spy_timing/config.py."""
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


def load_candidates() -> dict:
    if not CANDIDATES_FILE.exists():
        return {"updated_at": _now_iso(), "candidates": {}}
    try:
        return json.loads(CANDIDATES_FILE.read_text())
    except json.JSONDecodeError:
        return {"updated_at": _now_iso(), "candidates": {}}


def save_candidates(cands: dict):
    cands["updated_at"] = _now_iso()
    CANDIDATES_FILE.write_text(json.dumps(cands, indent=2))


# ─── LLM discovery ───────────────────────────────────────────────────────────

def ask_llm_for_venues(area: str, known_names: list[str]) -> list[dict]:
    """Ask Claude Haiku for 10 bars/restaurants/venues in `area` we don't track.

    Returns list of {name, url, area, category, why}.
    """
    api_key = _load_api_key()
    if not api_key:
        print(f"[LLM] no ANTHROPIC_API_KEY — skipping {area}")
        return []

    known_str = ", ".join(known_names) if known_names else "(none yet)"
    prompt = f"""Suggest up to 10 bars, restaurants, or live-music venues in {area}, CA (San Diego North County coast) that have:
  - An active public website (not just a Google Maps listing)
  - Recurring weekly events, live music, happy hours, or trivia
  - A conversational or social atmosphere (not nightclubs)

Exclude these — we already track them: {known_str}

For each, return a JSON object:
  - "name": display name
  - "url": the venue's official website homepage (include https://)
  - "area": "{area}"
  - "category": one of "bar", "restaurant", "music_venue", "cafe", "brewery", "wine_bar"
  - "why": one sentence on why it fits (weekly event, locals spot, etc.)

Return ONLY a raw JSON array. No markdown, no prose."""

    try:
        body = json.dumps({
            "model": MODEL,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            ANTHROPIC_ENDPOINT,
            data=body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
        text = result.get("content", [{}])[0].get("text", "")
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        data = json.loads(match.group(0))
        return [s for s in data if isinstance(s, dict) and "url" in s and "name" in s]
    except Exception as e:
        print(f"[LLM] discovery failed for {area}: {e}")
        return []


# ─── URL validation ──────────────────────────────────────────────────────────

def validate_url(url: str) -> tuple[bool, str]:
    """Fetch a URL to confirm it resolves + looks like a venue site. Returns (ok, reason)."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "LocalSocial/0.1 (+https://localsocial.app)"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            if status != 200:
                return False, f"status {status}"
            body = resp.read(60_000).decode("utf-8", errors="replace").lower()
    except Exception as e:
        return False, f"fetch error: {e}"

    # Very light signal check — looking for words suggesting a venue site
    signals = ["menu", "hours", "happy hour", "events", "reservation", "music", "drinks", "bar", "restaurant"]
    hits = sum(1 for s in signals if s in body)
    if hits < 2:
        return False, "no venue signals found"
    return True, f"ok ({hits} signals)"


# ─── Discovery run ───────────────────────────────────────────────────────────

def discover_for_area(area: str, reg: dict, cands: dict) -> int:
    """Discover candidates for one area. Returns count of new candidates added."""
    known_in_area = [n for n in venue_registry.venues(reg) if venue_registry.venue_area(reg, n) == area]
    pending_in_area = [c["name"] for c in cands["candidates"].values() if c.get("area") == area]
    exclude = known_in_area + pending_in_area

    print(f"[DISCOVER] {area} (excluding {len(exclude)} known/pending)...")
    suggestions = ask_llm_for_venues(area, exclude)
    if not suggestions:
        print(f"  no suggestions returned")
        return 0

    added = 0
    for s in suggestions:
        name = s.get("name", "").strip()
        url = s.get("url", "").strip()
        if not name or not url:
            continue
        if name in cands["candidates"] or name in venue_registry.venues(reg):
            continue
        print(f"  checking: {name} → {url}")
        ok, reason = validate_url(url)
        status = "validated" if ok else "invalid"
        print(f"    {status}: {reason}")
        cands["candidates"][name] = {
            "name": name,
            "url": url,
            "area": s.get("area", area),
            "category": s.get("category", ""),
            "why": s.get("why", ""),
            "discovered_at": _today(),
            "validation": {"ok": ok, "reason": reason, "checked_at": _today()},
        }
        if ok:
            added += 1
    return added


def run_discovery(areas: list[str]):
    reg = venue_registry.load()
    cands = load_candidates()
    total_added = 0
    for area in areas:
        total_added += discover_for_area(area, reg, cands)
    save_candidates(cands)
    print(f"\n[DISCOVER] {total_added} new validated candidates saved to {CANDIDATES_FILE.name}")
    print(f"           Review with: python {Path(__file__).name} --list")


# ─── Candidate management ───────────────────────────────────────────────────

def list_candidates(cands: dict):
    if not cands["candidates"]:
        print("No pending candidates.")
        return
    print(f"Pending candidates ({len(cands['candidates'])}):\n")
    for name, c in cands["candidates"].items():
        valid = c.get("validation", {})
        ok = valid.get("ok", False)
        badge = "[OK]" if ok else "[BAD]"
        print(f"  {badge} {name}  [{c.get('area')}]  ({c.get('category')})")
        print(f"       {c.get('url')}")
        if c.get("why"):
            print(f"       why: {c['why']}")
        print(f"       validation: {valid.get('reason', '?')}")
        print()


def approve(name: str, cands: dict, reg: dict) -> bool:
    c = cands["candidates"].get(name)
    if not c:
        print(f"[APPROVE] {name} not found in candidates")
        return False
    if not c.get("validation", {}).get("ok"):
        print(f"[APPROVE] refusing — {name} failed URL validation ({c['validation'].get('reason')})")
        return False
    venue_registry.add_venue(reg, name, c["area"], c["url"], source="candidate_approved")
    del cands["candidates"][name]
    print(f"[APPROVE] {name} promoted to registry")
    return True


def reject(name: str, cands: dict) -> bool:
    if name in cands["candidates"]:
        del cands["candidates"][name]
        print(f"[REJECT] removed {name}")
        return True
    print(f"[REJECT] {name} not found")
    return False


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if "--list" in args:
        list_candidates(load_candidates())
        return

    if "--approve-all" in args:
        cands = load_candidates()
        reg = venue_registry.load()
        names = list(cands["candidates"].keys())
        promoted = 0
        for n in names:
            if approve(n, cands, reg):
                promoted += 1
        save_candidates(cands)
        venue_registry.save(reg)
        print(f"\n[APPROVE-ALL] promoted {promoted}/{len(names)} candidates")
        return

    if "--approve" in args:
        idx = args.index("--approve")
        if idx + 1 >= len(args):
            print("Usage: --approve \"Venue Name\"")
            return
        name = args[idx + 1]
        cands = load_candidates()
        reg = venue_registry.load()
        if approve(name, cands, reg):
            save_candidates(cands)
            venue_registry.save(reg)
        return

    if "--reject" in args:
        idx = args.index("--reject")
        if idx + 1 >= len(args):
            print("Usage: --reject \"Venue Name\"")
            return
        name = args[idx + 1]
        cands = load_candidates()
        if reject(name, cands):
            save_candidates(cands)
        return

    # Default: run discovery
    areas = TARGET_AREAS
    if "--area" in args:
        idx = args.index("--area")
        if idx + 1 < len(args):
            areas = [args[idx + 1]]
    run_discovery(areas)


if __name__ == "__main__":
    main()
