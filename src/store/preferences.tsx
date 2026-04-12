import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { createContext, useContext, useEffect, useState } from 'react';
import { AREAS, DEFAULT_HOME_AREA } from '../data/areas';
import { getDeviceId, supabase } from '../supabase/client';
import { CATEGORIES, Preferences } from '../types';

const STORAGE_KEY = 'localsocial:prefs:v2';

async function syncPrefs(next: Preferences): Promise<void> {
  if (!supabase) return;
  const deviceId = await getDeviceId();
  await supabase.from('users').upsert({ device_id: deviceId }, { onConflict: 'device_id' });
  await supabase.from('preferences').upsert({
    device_id: deviceId,
    home_area: next.homeArea,
    enabled_zones: next.enabledZones,
    goal: next.goal,
    vibe: next.vibe,
    updated_at: new Date().toISOString(),
  });
}

const DEFAULT_PREFS: Preferences = {
  homeArea: DEFAULT_HOME_AREA,
  enabledZones: AREAS[DEFAULT_HOME_AREA] ?? [],
  goal: 'both',
  vibe: 'balanced',
  categories: CATEGORIES.map((c) => c.value),
};

interface Ctx {
  prefs: Preferences;
  ready: boolean;
  setPrefs: (next: Preferences) => Promise<void>;
  updatePrefs: (patch: Partial<Preferences>) => Promise<void>;
}

const PreferencesContext = createContext<Ctx | null>(null);

export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const [prefs, setPrefsState] = useState<Preferences>(DEFAULT_PREFS);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (raw) setPrefsState({ ...DEFAULT_PREFS, ...JSON.parse(raw) });
      } finally {
        setReady(true);
      }
    })();
  }, []);

  const setPrefs = async (next: Preferences) => {
    setPrefsState(next);
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    syncPrefs(next).catch(() => {});
  };

  const updatePrefs = async (patch: Partial<Preferences>) => {
    const next = { ...prefs, ...patch };
    await setPrefs(next);
  };

  return (
    <PreferencesContext.Provider value={{ prefs, ready, setPrefs, updatePrefs }}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences(): Ctx {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error('usePreferences must be used inside PreferencesProvider');
  return ctx;
}
