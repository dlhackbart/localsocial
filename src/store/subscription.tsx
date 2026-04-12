import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { createContext, useContext, useEffect, useState } from 'react';

const KEY = 'localsocial:sub:v1';

export type Plan = 'free' | 'paid';

interface SubState {
  plan: Plan;
  reveals: string[]; // ISO date strings (YYYY-MM-DD)
}

const DEFAULT: SubState = { plan: 'free', reveals: [] };

function isoWeekKey(d: Date): string {
  // ISO week number — free plan unlocks once per ISO week.
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((t.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return `${t.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

interface Ctx {
  state: SubState;
  ready: boolean;
  canReveal: (now?: Date) => boolean;
  revealedToday: (now?: Date) => boolean;
  reveal: () => Promise<void>;
  setPlan: (plan: Plan) => Promise<void>;
  nextResetLabel: (now?: Date) => string;
}

const SubContext = createContext<Ctx | null>(null);

export function SubscriptionProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SubState>(DEFAULT);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(KEY);
        if (raw) setState({ ...DEFAULT, ...JSON.parse(raw) });
      } finally {
        setReady(true);
      }
    })();
  }, []);

  const persist = async (next: SubState) => {
    setState(next);
    await AsyncStorage.setItem(KEY, JSON.stringify(next));
  };

  const revealedToday = (now: Date = new Date()) =>
    state.reveals.includes(todayIso());

  const canReveal = (now: Date = new Date()) => {
    if (state.plan === 'paid') return !revealedToday(now);
    // Free: one reveal per ISO week
    const thisWeek = isoWeekKey(now);
    return !state.reveals.some((d) => isoWeekKey(new Date(d)) === thisWeek);
  };

  const reveal = async () => {
    const today = todayIso();
    if (state.reveals.includes(today)) return;
    await persist({ ...state, reveals: [today, ...state.reveals].slice(0, 60) });
  };

  const setPlan = async (plan: Plan) => {
    await persist({ ...state, plan });
  };

  const nextResetLabel = (now: Date = new Date()) => {
    if (state.plan === 'paid') {
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      return `tomorrow`;
    }
    const d = new Date(now);
    const day = d.getDay(); // 0=Sun
    const daysToMonday = (8 - day) % 7 || 7;
    const next = new Date(d);
    next.setDate(d.getDate() + daysToMonday);
    return `Monday (${next.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })})`;
  };

  return (
    <SubContext.Provider
      value={{ state, ready, canReveal, revealedToday, reveal, setPlan, nextResetLabel }}
    >
      {children}
    </SubContext.Provider>
  );
}

export function useSubscription(): Ctx {
  const ctx = useContext(SubContext);
  if (!ctx) throw new Error('useSubscription must be used inside SubscriptionProvider');
  return ctx;
}
