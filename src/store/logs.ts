import AsyncStorage from '@react-native-async-storage/async-storage';
import { getDeviceId, supabase } from '../supabase/client';
import { LogEntry } from '../types';

const KEY = 'localsocial:logs:v1';

export async function loadLogs(): Promise<LogEntry[]> {
  const raw = await AsyncStorage.getItem(KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as LogEntry[];
  } catch {
    return [];
  }
}

export async function saveLog(entry: LogEntry): Promise<LogEntry[]> {
  const existing = await loadLogs();
  const next = [entry, ...existing].slice(0, 200);
  await AsyncStorage.setItem(KEY, JSON.stringify(next));
  syncLog(entry).catch(() => {});
  return next;
}

export async function clearLogs(): Promise<void> {
  await AsyncStorage.removeItem(KEY);
}

async function syncLog(entry: LogEntry): Promise<void> {
  if (!supabase) return;
  const deviceId = await getDeviceId();
  await supabase.from('users').upsert({ device_id: deviceId }, { onConflict: 'device_id' });
  await supabase.from('logs').upsert({
    id: entry.id,
    device_id: deviceId,
    date: entry.date,
    went_out: entry.wentOut,
    venue: entry.venue,
    crowd_grade: entry.crowdGrade,
    would_go_again: entry.wouldGoAgain,
  });
}
