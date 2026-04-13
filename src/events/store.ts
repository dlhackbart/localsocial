import AsyncStorage from '@react-native-async-storage/async-storage';
import { getSampleEvents } from '../data/events';
import { supabase } from '../supabase/client';
import { LocalEvent } from '../types';
import { parseICal, RawICalEvent } from './ical';
import { resolveSourcesForArea, ResolvedSource } from './resolver';

const CACHE_KEY = 'localsocial:events:v2';
const CACHE_TTL_MS = 6 * 60 * 60 * 1000; // 6 hours

interface CacheShape {
  fetchedAt: number;
  areaLabel: string;
  events: LocalEvent[];
}

async function readCache(areaLabel: string): Promise<CacheShape | null> {
  const raw = await AsyncStorage.getItem(CACHE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as CacheShape;
    if (parsed.areaLabel !== areaLabel) return null;
    if (Date.now() - parsed.fetchedAt > CACHE_TTL_MS) return null;
    return parsed;
  } catch {
    return null;
  }
}

async function writeCache(areaLabel: string, events: LocalEvent[]): Promise<void> {
  const payload: CacheShape = { fetchedAt: Date.now(), areaLabel, events };
  await AsyncStorage.setItem(CACHE_KEY, JSON.stringify(payload));
}

function toLocalEvent(raw: RawICalEvent, src: ResolvedSource): LocalEvent | null {
  if (!raw.start) return null;
  const date = raw.start.toISOString().slice(0, 10);
  const time = raw.start.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  return {
    id: `ical_${src.name}_${raw.uid}`,
    title: raw.summary,
    area: src.area,
    date,
    time,
    category: src.defaultCategory,
    description: raw.description ?? raw.location,
    source: 'ical',
    sourceName: src.name,
    intimate: src.intimate ?? true,
    conversationFriendly: src.conversationFriendly ?? true,
    repeatFriendly: src.repeatFriendly ?? false,
    broadAppeal: true,
  };
}

async function fetchIcsViaProxy(url: string): Promise<string | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.functions.invoke('sources', {
    body: { action: 'proxy', url },
  });
  if (error) return null;
  if (typeof data === 'string') return data;
  // functions.invoke returns the raw text for non-JSON responses
  try { return String(data); } catch { return null; }
}

async function fetchIcsDirect(url: string): Promise<string | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}

async function fetchSource(src: ResolvedSource): Promise<LocalEvent[]> {
  // Prefer edge function proxy (works on web + mobile, bypasses CORS).
  // Fall back to direct fetch (works on native; may fail on web).
  const text = (await fetchIcsViaProxy(src.url)) ?? (await fetchIcsDirect(src.url));
  if (!text) return [];
  const raws = parseICal(text);
  return raws.map((r) => toLocalEvent(r, src)).filter((e): e is LocalEvent => e !== null);
}

export async function loadEvents(
  areaLabel: string,
  options: { force?: boolean } = {},
): Promise<LocalEvent[]> {
  const sampleNow = getSampleEvents();

  if (!options.force) {
    const cached = await readCache(areaLabel);
    if (cached) return mergeAndDedupe(cached.events, sampleNow);
  }

  // Fetch live sources with a timeout — always fall back to samples
  let fetched: LocalEvent[] = [];
  try {
    const fetchWithTimeout = new Promise<LocalEvent[]>(async (resolve) => {
      try {
        const sources = await resolveSourcesForArea(areaLabel);
        const results: LocalEvent[] = [];
        for (const src of sources) {
          const events = await fetchSource(src);
          results.push(...events);
        }
        resolve(results);
      } catch {
        resolve([]);
      }
    });

    const timeout = new Promise<LocalEvent[]>((resolve) =>
      setTimeout(() => resolve([]), 8000),
    );

    fetched = await Promise.race([fetchWithTimeout, timeout]);
  } catch {
    fetched = [];
  }

  const merged = mergeAndDedupe(fetched, sampleNow);
  await writeCache(areaLabel, merged);
  return merged;
}

function mergeAndDedupe(live: LocalEvent[], samples: LocalEvent[]): LocalEvent[] {
  const seen = new Set(live.map((e) => `${e.title.toLowerCase()}|${e.date}`));
  const extras = samples.filter((s) => !seen.has(`${s.title.toLowerCase()}|${s.date}`));
  return [...live, ...extras];
}
