#!/usr/bin/env node
// Seed venues + events into Supabase. Run: node scripts/seed_supabase.mjs
// Requires EXPO_PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in env.
import { createClient } from '@supabase/supabase-js';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

const url = process.env.EXPO_PUBLIC_SUPABASE_URL;
const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
if (!url || !key) {
  console.error('Missing EXPO_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY.');
  process.exit(1);
}
const supabase = createClient(url, key);

// Extract VENUES literal from src/data/venues.ts (simple — avoids TS runtime dep).
const src = readFileSync(resolve(__dirname, '..', 'src', 'data', 'venues.ts'), 'utf8');
const match = src.match(/export const VENUES[^=]*=\s*(\[[\s\S]*\]);/);
if (!match) { console.error('Could not parse VENUES.'); process.exit(1); }
// eslint-disable-next-line no-new-func
const venues = new Function('return ' + match[1])();

console.log(`Seeding ${venues.length} venues…`);
for (const v of venues) {
  const { data, error } = await supabase
    .from('venues')
    .upsert(
      {
        name: v.name,
        area: v.area,
        repeat_friendly: v.repeatFriendly,
        conversation_friendly: v.conversationFriendly,
        energy: v.energy,
        low_social_value: v.lowSocialValue ?? false,
      },
      { onConflict: 'name,area' },
    )
    .select('id')
    .single();
  if (error) { console.error('venue error', v.name, error); continue; }
  const venueId = data.id;
  await supabase.from('events').delete().eq('venue_id', venueId);
  if (v.events?.length) {
    await supabase.from('events').insert(
      v.events.map((e) => ({
        venue_id: venueId,
        day: e.day,
        type: e.type,
        time: e.time,
        broad_appeal: e.broadAppeal,
      })),
    );
  }
  console.log(`  ✓ ${v.name} (${v.events.length} events)`);
}
console.log('Done.');
