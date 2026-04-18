"""
One-shot seed script: populate venue descriptions in the registry.

Run once to apply descriptions to every known venue. Idempotent —
re-running just refreshes the text. Also adds venues that aren't yet
in the registry (Belly Up, Del Mar Plaza, etc.) since they belong in
the canonical list even when they're handled by dedicated scrapers.

Usage:
    python scripts/seed_venue_descriptions.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venue_registry

# (name, area, url, description)
# URL "" means the venue is handled entirely by dedicated scrapers and
# shouldn't be fetched by the weekly-pattern LLM pass — but we still
# keep its description here so plan output can surface it.
VENUE_DESCRIPTIONS: list[tuple[str, str, str, str]] = [
    # ─── Del Mar ─────────────────────────────────────────────────────────────
    ("Torrey Pines Gliderport", "Del Mar", "https://flytorrey.com/event-calendar",
     "Cliffhanger Bar on the ocean cliffs. HH Mon-Thu 4-5 PM with $6 wine/beer. Paragliders + sunset views."),

    ("Jake's Del Mar", "Del Mar", "https://www.jakesdelmar.com",
     "Beachfront Del Mar patio — oceanfront bar, regular locals. HH Mon-Fri 3-6 PM, Sunday brunch into afternoon."),

    ("Kitchen 1540 (L'Auberge)", "Del Mar", "https://www.laubergedelmar.com/dining/kitchen-1540",
     "Upscale resort bar at L'Auberge Del Mar. Craft cocktails + light food. HH Mon-Thu 3-5 PM. Live music most nights."),

    ("Monarch Ocean Pub", "Del Mar", "https://www.delmarplaza.com/events",
     "Ocean-view patio inside Del Mar Plaza. HH Tue-Fri 4-6 PM. Live acoustic Wed-Sun afternoons (rotating performers)."),

    ("Del Mar Plaza", "Del Mar", "",
     "Ocean View Deck at the Plaza. Seaside Sessions Wed/Fri/Sat 5-7 PM — named artists, free live music with ocean sunset."),

    ("Poseidon Del Mar", "Del Mar", "",
     "Right on the sand — massive patio, classic HH crowd. HH Mon-Fri 3-6 PM. Saturday sunset + Sunday beach brunch."),

    ("Pacifica Del Mar", "Del Mar", "https://pacificadelmar.com",
     "Oceanfront sunset fine-dining. HH Tue-Sat 4-6:30 PM + all night Sun/Mon. Taco Tuesday $5. Wed $9 gin/vodka. Thu half-off bottles."),

    ("Del Mar Fairgrounds", "Del Mar", "",
     "Half a mile from home. SD County Fair (June 10 - July 5), Toyota Summer Concert Series (Chicago, Marshmello, Nelly, AJR, more), Del Mar Racing opens July 17."),

    # ─── Solana Beach ────────────────────────────────────────────────────────
    ("Pillbox Tavern", "Solana Beach", "https://www.pillboxtavern.com",
     "Neighborhood beach bar above Fletcher Cove. HH Mon-Fri 3-6 PM. Burger Mondays, weekend brunch crowd."),

    ("Belly Up Tavern", "Solana Beach", "https://www.bellyup.com",
     "Iconic North County music room since 1974. Intimate sound, defining live-music spot on the coast. Atomic Groove Happy Hour Thursdays. Headliners nightly 8 PM."),

    ("North Coast Repertory Theatre", "Solana Beach", "",
     "Solana Beach's resident theater company. Seasonal productions — currently Beau Jest, upcoming The Most Happy Fella."),

    # ─── Encinitas / Cardiff ─────────────────────────────────────────────────
    ("The Third Corner", "Encinitas", "",
     "Wine bar in Encinitas — quiet, conversation-friendly. Wine tastings Tue + Thu 6-8 PM. HH Mon-Fri 3-6 PM."),

    ("Lofty Coffee", "Encinitas", "",
     "Daytime coffee spot — dog walkers, yoga crowd, quality morning regulars Mon-Fri 7-10 AM. Weekend crowd 8-12."),

    ("The Saloon", "Encinitas", "",
     "Encinitas dive bar. Live band Fri/Sat 9 PM — high energy, loud, not for conversation."),

    ("Moonlight Beach Bar", "Encinitas", "",
     "Encinitas beach bar. Saturday DJ night 9 PM — high energy."),

    ("1st Street Bar", "Encinitas", "",
     "Neighborhood Encinitas dive — core regular crowd. HH Mon-Fri 3-6 PM. Neighborhood night Tue/Thu, locals day Sunday."),

    ("Union Kitchen & Tap", "Encinitas", "https://www.localunion101.com",
     "Downtown Encinitas gastropub. Social Hour Mon-Fri 3-5 PM, weekend brunch 10-2, Friday DJ late set."),

    ("Chart House Cardiff", "Encinitas", "https://www.chart-house.com/locations/cardiff-by-the-sea/",
     "Oceanfront seafood on Cardiff 101. Classic HH crowd + sunset views."),

    ("Ki's Restaurant", "Encinitas", "https://www.kisrestaurant.com",
     "Cliffside Cardiff organic/health food + bar. HH daily 3:30-6 PM (well drinks + appetizer pricing). Live music Fri 7-9 PM ('The Spell' — 70s/80s/90s classics)."),

    ("Pacific Coast Grill", "Encinitas", "https://www.pacificcoastgrill.com",
     "Oceanfront Cardiff 101 spot. Raw bar 3-4 PM (oyster window). Dinner 4-8:30 PM (9 Fri/Sat)."),

    ("Fish 101", "Encinitas", "https://fish101restaurant.com",
     "Casual Leucadia oyster/seafood on 101. Counter-service vibe, local regular crowd."),

    ("La Paloma Theatre", "Encinitas", "",
     "Historic 1928 single-screen theater on Encinitas 101. Classic films, indie screenings, Rocky Horror with live shadow cast, SD Italian Film Festival."),

    # ─── Carlsbad ────────────────────────────────────────────────────────────
    ("Campfire", "Carlsbad", "https://www.thisiscampfire.com",
     "Carlsbad patio with fire pits — conversation-friendly. HH Tue-Fri 4-6 PM."),

    ("Park 101", "Carlsbad", "https://www.park101.com",
     "Carlsbad outdoor beer garden. Fri/Sat outdoor DJ 8 PM — high-energy patio scene."),

    ("Vigilucci's Cucina Italiana", "Carlsbad", "https://www.vigiluccis.com",
     "Downtown Carlsbad Italian (3878 Carlsbad Blvd). Full-service bar, romantic dinner spot."),

    ("Pizza Port Carlsbad", "Carlsbad", "https://pizzaport.com",
     "Craft brewery + pizza on Carlsbad Village. Multiple locations; the OG brewpub vibe."),
]


def main():
    reg = venue_registry.load()
    added = 0
    updated = 0

    for name, area, url, desc in VENUE_DESCRIPTIONS:
        existed = name in reg["venues"]
        if not existed and url:
            venue_registry.add_venue(reg, name, area, url, source="seed", description=desc)
            added += 1
        elif not existed and not url:
            # Venue handled by dedicated scrapers — still register it for its
            # description, but don't add a URL for the weekly-pattern LLM pass
            reg["venues"][name] = {
                "area": area,
                "added_at": venue_registry._today(),
                "description": desc,
                "urls": {},
            }
            added += 1
        else:
            # Already in registry — just refresh description
            prev = reg["venues"][name].get("description", "")
            reg["venues"][name]["description"] = desc
            # Also make sure area is set (could be empty on old entries)
            reg["venues"][name].setdefault("area", area)
            if prev != desc:
                updated += 1

    venue_registry.save(reg)
    print(f"[SEED] added {added} new venue(s), updated {updated} description(s)")
    print(f"[SEED] registry now has {len(reg['venues'])} venue(s)")


if __name__ == "__main__":
    main()
