// Supabase Edge Function: sources
// Handles: proxy (CORS-bypass .ics fetch), discover (probe + LLM), add (user submission),
// and list (read from DB). Runs on Deno.
//
// Deploy:  supabase functions deploy sources
// Env vars needed (set via `supabase secrets set`):
//   ANTHROPIC_API_KEY  (for Option 3 — LLM discovery)
// SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are auto-injected.

// deno-lint-ignore-file no-explicit-any
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};

const CATEGORIES = [
  'hiking_outdoor','classes_workshops','community_civic','live_music_small',
  'art_galleries','food_drink','book_clubs','markets','theater_small',
  'movies_indie','meetups_clubs','wellness',
] as const;
type Category = typeof CATEGORIES[number];

const ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001';

interface AreaInput {
  label: string;             // "Bend, OR"
}

function slugify(label: string): string {
  return label.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function citySlug(label: string): string {
  // "Bend, OR" -> "bend"
  return slugify(label.split(',')[0] ?? label);
}

function stateCode(label: string): string | null {
  const parts = label.split(',').map((s) => s.trim());
  return parts[1]?.toUpperCase() ?? null;
}

// ---------- iCal validation ----------
async function fetchIcs(url: string): Promise<{ ok: boolean; eventCount: number; text: string }> {
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': 'LocalSocial/0.1 (+https://localsocial.app)' },
      redirect: 'follow',
    });
    if (!res.ok) return { ok: false, eventCount: 0, text: '' };
    const text = await res.text();
    if (!text.trimStart().startsWith('BEGIN:VCALENDAR')) {
      return { ok: false, eventCount: 0, text };
    }
    const eventCount = (text.match(/BEGIN:VEVENT/g) ?? []).length;
    return { ok: true, eventCount, text };
  } catch {
    return { ok: false, eventCount: 0, text: '' };
  }
}

// ---------- Rule-based probe (Option 2) ----------
interface Candidate {
  name: string;
  url: string;
  defaultCategory: Category;
}

function buildProbeCandidates(areaLabel: string): Candidate[] {
  const city = citySlug(areaLabel);
  const state = stateCode(areaLabel)?.toLowerCase() ?? 'ca';

  const candidates: Candidate[] = [];
  const hosts = [
    `www.${city}${state}.gov`,          // bendor.gov style
    `www.${city}.${state}.us`,          // older .us
    `www.${city}.gov`,                  // plain .gov
    `www.ci.${city}.${state}.us`,       // ci.bend.or.us style
    `www.cityof${city}.org`,
    `www.cityof${city}.com`,
    `${city}.gov`,
  ];

  // CivicPlus (major municipal CMS — ~3000 cities)
  for (const h of hosts) {
    for (const catId of [24, 14, 13, 25]) {
      candidates.push({
        name: `${areaLabel} City Calendar`,
        url: `https://${h}/common/modules/iCalendar/iCalendar.aspx?catID=${catId}&feed=calendar`,
        defaultCategory: 'community_civic',
      });
    }
  }

  // WordPress Tribe Events
  for (const h of hosts) {
    candidates.push({
      name: `${areaLabel} Events`,
      url: `https://${h}/events/?ical=1`,
      defaultCategory: 'community_civic',
    });
  }

  // Generic static feeds
  for (const h of hosts) {
    candidates.push({ name: `${areaLabel} Calendar`, url: `https://${h}/calendar.ics`, defaultCategory: 'community_civic' });
    candidates.push({ name: `${areaLabel} Events Feed`, url: `https://${h}/events/feed`, defaultCategory: 'community_civic' });
  }

  // Common library patterns (LibCal)
  candidates.push({
    name: `${areaLabel} Library`,
    url: `https://${city}library.libcal.com/ical_subscribe/all`,
    defaultCategory: 'classes_workshops',
  });

  return candidates;
}

// ---------- LLM discovery (Option 3) ----------
async function llmDiscover(areaLabel: string): Promise<Candidate[]> {
  const apiKey = Deno.env.get('ANTHROPIC_API_KEY');
  if (!apiKey) return [];

  const prompt = `You are helping a local-events app find public iCalendar (.ics) or RSS feeds for a specific US town. For the town below, list up to 8 URLs that are MOST LIKELY to resolve to a real public iCal feed from the city government, public library, chamber of commerce, community newspaper, parks & recreation, or community centers.

Only include URLs you have reasonable confidence exist. Do NOT guess wildly. If you can't think of 8 good ones, return fewer. Prefer real, specific URL patterns you've seen for this platform:
- CivicPlus:   https://www.{city}.gov/common/modules/iCalendar/iCalendar.aspx?catID={N}&feed=calendar
- LibCal:      https://{library}.libcal.com/ical_subscribe/{id}
- WordPress Tribe:   https://www.{site}/events/?ical=1
- Squarespace: https://www.{site}/events?format=ical

Return ONLY a raw JSON array (no markdown, no prose). Each object must have:
  "name": string (display name)
  "url": string (absolute URL)
  "category": one of ${CATEGORIES.join(', ')}

Town: ${areaLabel}`;

  try {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        model: ANTHROPIC_MODEL,
        max_tokens: 1024,
        messages: [{ role: 'user', content: prompt }],
      }),
    });
    if (!res.ok) return [];
    const data = await res.json();
    const text = data.content?.[0]?.text ?? '';
    const match = text.match(/\[[\s\S]*\]/);
    if (!match) return [];
    const parsed = JSON.parse(match[0]) as Array<{ name: string; url: string; category: string }>;
    return parsed
      .filter((x) => x && typeof x.url === 'string' && CATEGORIES.includes(x.category as Category))
      .map((x) => ({ name: x.name, url: x.url, defaultCategory: x.category as Category }));
  } catch {
    return [];
  }
}

// ---------- Handlers ----------
async function handleProxy(url: string): Promise<Response> {
  const result = await fetchIcs(url);
  return new Response(result.text, {
    headers: { ...CORS, 'Content-Type': 'text/calendar' },
    status: result.ok ? 200 : 502,
  });
}

async function handleDiscover(areaLabel: string, supabase: any): Promise<Response> {
  const slug = slugify(areaLabel);

  // Already discovered? Return what we have.
  const existing = await supabase
    .from('sources')
    .select('*')
    .eq('area_slug', slug)
    .eq('last_fetch_ok', true);

  if (existing.data && existing.data.length > 0) {
    return json({ area_slug: slug, sources: existing.data, cached: true });
  }

  // Run probe + LLM in parallel.
  const [probeCandidates, llmCandidates] = await Promise.all([
    Promise.resolve(buildProbeCandidates(areaLabel)),
    llmDiscover(areaLabel),
  ]);

  const seen = new Set<string>();
  const dedupedCandidates: Array<Candidate & { method: 'probe' | 'llm' }> = [];
  for (const c of probeCandidates) {
    if (seen.has(c.url)) continue;
    seen.add(c.url);
    dedupedCandidates.push({ ...c, method: 'probe' });
  }
  for (const c of llmCandidates) {
    if (seen.has(c.url)) continue;
    seen.add(c.url);
    dedupedCandidates.push({ ...c, method: 'llm' });
  }

  // Validate each candidate — keep only ones that return real iCal.
  const valid: any[] = [];
  for (const c of dedupedCandidates) {
    const res = await fetchIcs(c.url);
    if (!res.ok) continue;
    valid.push({
      area_slug: slug,
      area_label: areaLabel,
      name: c.name,
      url: c.url,
      default_category: c.defaultCategory,
      discovery_method: c.method,
      verified_at: new Date().toISOString(),
      last_fetch_ok: true,
      last_fetch_at: new Date().toISOString(),
      last_event_count: res.eventCount,
    });
  }

  if (valid.length > 0) {
    await supabase.from('sources').upsert(valid, { onConflict: 'area_slug,url' });
  }
  await supabase.from('area_discovery').upsert({
    area_slug: slug,
    area_label: areaLabel,
    sources_found: valid.length,
    method_used: valid.length > 0 ? 'probe+llm' : 'none',
    discovered_at: new Date().toISOString(),
  });

  return json({ area_slug: slug, sources: valid, cached: false, probed: dedupedCandidates.length });
}

async function handleAdd(payload: any, supabase: any): Promise<Response> {
  const { area_label, name, url, default_category, contributed_by } = payload;
  if (!area_label || !name || !url || !default_category) {
    return json({ error: 'Missing fields' }, 400);
  }
  if (!CATEGORIES.includes(default_category)) {
    return json({ error: 'Invalid category' }, 400);
  }

  const res = await fetchIcs(url);
  if (!res.ok) {
    return json({ error: 'URL did not return a valid iCalendar feed.' }, 422);
  }

  const slug = slugify(area_label);
  const row = {
    area_slug: slug,
    area_label,
    name,
    url,
    default_category,
    discovery_method: 'user',
    contributed_by: contributed_by ?? null,
    verified_at: new Date().toISOString(),
    last_fetch_ok: true,
    last_fetch_at: new Date().toISOString(),
    last_event_count: res.eventCount,
  };
  const { error } = await supabase.from('sources').upsert(row, { onConflict: 'area_slug,url' });
  if (error) return json({ error: error.message }, 500);
  return json({ ok: true, source: row });
}

async function handleList(areaLabel: string, supabase: any): Promise<Response> {
  const slug = slugify(areaLabel);
  const { data, error } = await supabase
    .from('sources')
    .select('*')
    .eq('area_slug', slug)
    .eq('last_fetch_ok', true);
  if (error) return json({ error: error.message }, 500);
  return json({ area_slug: slug, sources: data ?? [] });
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { ...CORS, 'Content-Type': 'application/json' },
    status,
  });
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS });
  if (req.method !== 'POST') return json({ error: 'POST only' }, 405);

  const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
  const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
  const supabase = createClient(supabaseUrl, serviceKey);

  let body: any;
  try { body = await req.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }
  const action = body?.action;

  try {
    switch (action) {
      case 'proxy':
        if (!body.url) return json({ error: 'url required' }, 400);
        return await handleProxy(body.url);
      case 'discover':
        if (!body.area_label) return json({ error: 'area_label required' }, 400);
        return await handleDiscover(body.area_label, supabase);
      case 'list':
        if (!body.area_label) return json({ error: 'area_label required' }, 400);
        return await handleList(body.area_label, supabase);
      case 'add':
        return await handleAdd(body, supabase);
      default:
        return json({ error: 'Unknown action' }, 400);
    }
  } catch (e) {
    return json({ error: (e as Error).message }, 500);
  }
});
