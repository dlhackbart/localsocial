import { getDeviceId, supabase } from '../supabase/client';
import { Category } from '../types';
import { ICalSource, ICAL_SOURCES } from './sources';

// Resolver chain for per-area iCal sources:
//   1. Local constant (ICAL_SOURCES) — always available, matches area
//   2. Supabase `sources` table — crowdsourced + previously discovered
//   3. Edge function `discover` — rule-based probe + LLM discovery (first time only)

export interface ResolvedSource extends ICalSource {
  id?: number;
  discoveryMethod?: 'probe' | 'llm' | 'user' | 'seed' | 'local';
  eventCount?: number;
}

function rowToSource(row: any): ResolvedSource {
  return {
    id: row.id,
    name: row.name,
    url: row.url,
    area: row.area_label,
    defaultCategory: row.default_category as Category,
    intimate: row.intimate,
    conversationFriendly: row.conversation_friendly,
    repeatFriendly: row.repeat_friendly,
    discoveryMethod: row.discovery_method,
    eventCount: row.last_event_count,
  };
}

function localForArea(areaLabel: string): ResolvedSource[] {
  return ICAL_SOURCES
    .filter((s) => s.area === areaLabel)
    .map((s) => ({ ...s, discoveryMethod: 'local' as const }));
}

async function listRemote(areaLabel: string): Promise<ResolvedSource[]> {
  if (!supabase) return [];
  const { data, error } = await supabase.functions.invoke('sources', {
    body: { action: 'list', area_label: areaLabel },
  });
  if (error || !data?.sources) return [];
  return (data.sources as any[]).map(rowToSource);
}

async function triggerDiscovery(areaLabel: string): Promise<ResolvedSource[]> {
  if (!supabase) return [];
  const { data, error } = await supabase.functions.invoke('sources', {
    body: { action: 'discover', area_label: areaLabel },
  });
  if (error || !data?.sources) return [];
  return (data.sources as any[]).map(rowToSource);
}

export async function resolveSourcesForArea(areaLabel: string): Promise<ResolvedSource[]> {
  const local = localForArea(areaLabel);

  if (!supabase) return local;

  const remote = await listRemote(areaLabel);
  if (remote.length > 0) {
    return dedupe([...remote, ...local]);
  }

  // First time for this area — run discovery (probe + LLM).
  const discovered = await triggerDiscovery(areaLabel);
  return dedupe([...discovered, ...local]);
}

function dedupe(sources: ResolvedSource[]): ResolvedSource[] {
  const seen = new Set<string>();
  return sources.filter((s) => {
    if (seen.has(s.url)) return false;
    seen.add(s.url);
    return true;
  });
}

export async function addUserSource(input: {
  areaLabel: string;
  name: string;
  url: string;
  category: Category;
}): Promise<{ ok: boolean; error?: string }> {
  if (!supabase) return { ok: false, error: 'Supabase not configured.' };
  const deviceId = await getDeviceId();
  const { data, error } = await supabase.functions.invoke('sources', {
    body: {
      action: 'add',
      area_label: input.areaLabel,
      name: input.name,
      url: input.url,
      default_category: input.category,
      contributed_by: deviceId,
    },
  });
  if (error) return { ok: false, error: error.message };
  if (data?.error) return { ok: false, error: data.error };
  return { ok: true };
}
