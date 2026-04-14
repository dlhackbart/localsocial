import { VENUES } from './data/venues';
import {
  DayName, Decision, Goal, Grade, LocalEvent, Preferences,
  Recommendation, RecommendationResult, Venue, VenueEvent, Vibe,
} from './types';

const DAY_NAMES: DayName[] = [
  'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
];

export function todayName(date: Date = new Date()): DayName {
  return DAY_NAMES[date.getDay()];
}

function isHappyHourActive(venue: Venue, at: Date = new Date()): boolean {
  if (!venue.happyHour) return false;
  const day = DAY_NAMES[at.getDay()];
  if (!venue.happyHour.days.includes(day)) return false;
  const startMin = parseTimeToMinutes(venue.happyHour.start);
  const endMin = parseTimeToMinutes(venue.happyHour.end);
  if (startMin === null || endMin === null) return false;
  const nowMin = at.getHours() * 60 + at.getMinutes();
  return nowMin >= startMin && nowMin <= endMin;
}

function parseTimeToMinutes(s: string): number | null {
  const m = s.trim().match(/^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$/i);
  if (!m) return null;
  let h = parseInt(m[1], 10);
  const mm = m[2] ? parseInt(m[2], 10) : 0;
  const ap = m[3]?.toUpperCase();
  if (ap === 'PM' && h < 12) h += 12;
  if (ap === 'AM' && h === 12) h = 0;
  return h * 60 + mm;
}

function scoreVenueEvent(
  venue: Venue,
  event: VenueEvent,
  goal: Goal,
  vibe: Vibe,
  happyHourOnThisDay: boolean = false,
): { score: number; reason: string } {
  let score = 0;
  const reasons: string[] = [];

  // Core: event exists
  score += 5;

  // BIGGEST BOOST: places you can become a regular.
  // Goal is casual dating via familiarity, not the hot scene.
  if (venue.repeatFriendly) {
    score += 4;
    reasons.push('Become a regular here');
  }

  if (venue.conversationFriendly) {
    score += 3;
    reasons.push('Conversation-friendly');
  }

  // Happy hour on this day = a time when regulars naturally gather
  if (happyHourOnThisDay && venue.repeatFriendly) {
    score += 2;
    if (reasons.length === 0) reasons.push('Happy hour regulars');
  }

  // Energy is now a smaller factor — prefer medium (conversational) over high
  if (venue.energy === 'medium') {
    score += 1;
  } else if (venue.energy === 'high') {
    // high energy venues work for "social" goal but hurt for dating
    if (goal === 'social') score += 1;
    if (goal === 'dating') score -= 2;
  }

  if (event.broadAppeal) score += 1;
  if (venue.lowSocialValue) score -= 3;

  // Vibe override
  if (vibe === 'quiet' && venue.energy === 'high') score -= 3;
  if (vibe === 'high' && venue.energy === 'low') score -= 2;

  // Dating penalties — missing regulars or conversation is a dealbreaker
  if (goal === 'dating' && !venue.repeatFriendly) score -= 3;
  if (goal === 'dating' && !venue.conversationFriendly) score -= 2;

  return { score, reason: reasons[0] ?? 'Decent local option' };
}

function scoreLocalEvent(
  ev: LocalEvent,
  goal: Goal,
  vibe: Vibe,
): { score: number; reason: string } {
  let score = 0;
  const reasons: string[] = [];

  score += 5; // event exists

  // Fairgrounds / Racetrack — 1/2 mile from home, always prioritize
  const isFairgrounds = ev.sourceName === 'Del Mar Fairgrounds' ||
                        ev.sourceName === 'Del Mar Racetrack';
  if (isFairgrounds) {
    score += 4;
    reasons.push('Right in your backyard');
  }

  if (ev.intimate) {
    score += 2;
    reasons.push('Small intimate gathering');
  }

  const wantConversation = goal === 'dating' || goal === 'both';
  if (ev.conversationFriendly && wantConversation) {
    score += 3;
    if (reasons.length === 0) reasons.push('Strong for conversation');
  }

  if (ev.repeatFriendly) {
    score += 2;
    if (reasons.length === 0) reasons.push('Recurring — same crowd returns');
  }

  if (ev.broadAppeal) score += 1;

  if (goal === 'dating' && !ev.repeatFriendly && !isFairgrounds) score -= 1;
  if (vibe === 'quiet' && !ev.intimate && !isFairgrounds) score -= 1;

  return { score, reason: reasons[0] ?? 'Good local option' };
}

function gradeFor(score: number): Grade {
  if (score >= 8) return 'A';
  if (score >= 5) return 'B';
  return 'C';
}

function decisionFor(grade: Grade): Decision {
  if (grade === 'A') return 'GO';
  if (grade === 'B') return 'MAYBE';
  return 'SKIP';
}

function allowedAreas(prefs: Preferences): Set<string> {
  return new Set([prefs.homeArea, ...prefs.enabledZones]);
}

function isSameDay(isoDate: string, now: Date): boolean {
  return isoDate === now.toISOString().slice(0, 10);
}

// Grace window: don't drop an event whose start time is a few minutes old —
// you can still walk into a 6:55 PM event at 7:05 PM. Larger window for
// all-day/no-time events so they stay visible.
const UPCOMING_GRACE_MINUTES = 60;

function parseEventTimeToMinutes(time: string): number | null {
  // Accept "7:00 AM", "6:30 PM", "19:00", "7 PM", "4-7 PM" (use start).
  // For ranges like "4-7 PM", the PM applies to both parts.
  const first = time.split(/[-–—]/)[0].trim();
  const m = first.match(/^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$/i);
  if (!m) return null;
  let h = parseInt(m[1], 10);
  const mm = m[2] ? parseInt(m[2], 10) : 0;
  // If first part has no AM/PM, inherit from the full string (e.g., "4-7 PM" → PM)
  let ap = m[3]?.toUpperCase();
  if (!ap) {
    const fullMatch = time.match(/(AM|PM)\s*$/i);
    if (fullMatch) ap = fullMatch[1].toUpperCase();
  }
  if (ap === 'PM' && h < 12) h += 12;
  if (ap === 'AM' && h === 12) h = 0;
  if (h > 23 || mm > 59) return null;
  return h * 60 + mm;
}

function isStillUpcomingToday(time: string, now: Date): boolean {
  const minutes = parseEventTimeToMinutes(time);
  if (minutes === null) return true; // keep unparseable times visible
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  return minutes + UPCOMING_GRACE_MINUTES >= nowMinutes;
}

// After this hour, show tomorrow's events instead of tonight's
const NEXT_DAY_CUTOFF_HOUR = 22; // 10 PM

export function getRecommendations(
  prefs: Preferences,
  events: LocalEvent[] = [],
  now: Date = new Date(),
): RecommendationResult {
  // After 10 PM, shift to tomorrow — tonight's over, show what's next
  if (now.getHours() >= NEXT_DAY_CUTOFF_HOUR) {
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(12, 0, 0, 0); // noon tomorrow so all events pass time filter
    now = tomorrow;
  }

  const day = todayName(now);
  const areas = allowedAreas(prefs);
  const categorySet = new Set(prefs.categories);

  // ---------- venue candidates ----------
  const venueCandidates: Recommendation[] = [];
  for (const venue of VENUES) {
    if (!areas.has(venue.area)) continue;
    const ev = venue.events.find((e) => e.day === day);
    if (!ev) continue;
    if (!isStillUpcomingToday(ev.time, now)) continue;

    const { score, reason } = scoreVenueEvent(venue, ev, prefs.goal, prefs.vibe);
    const grade = gradeFor(score);
    venueCandidates.push({
      kind: 'venue',
      title: venue.name,
      area: venue.area,
      time: ev.time,
      subtitle: ev.type,
      grade,
      decision: decisionFor(grade),
      reason,
      score,
      infoUrl: venue.infoUrl,
    });
  }
  venueCandidates.sort((a, b) => b.score - a.score);

  // ---------- local event candidates ----------
  const eventCandidates: Recommendation[] = [];
  for (const ev of events) {
    if (!areas.has(ev.area)) continue;
    if (!categorySet.has(ev.category)) continue;
    if (!isSameDay(ev.date, now)) continue;
    if (!isStillUpcomingToday(ev.time, now)) continue;

    const { score, reason } = scoreLocalEvent(ev, prefs.goal, prefs.vibe);
    const grade = gradeFor(score);
    eventCandidates.push({
      kind: 'event',
      title: ev.title,
      area: ev.area,
      time: ev.time,
      subtitle: ev.description ?? ev.category.replace(/_/g, ' '),
      grade,
      decision: decisionFor(grade),
      reason,
      score,
      category: ev.category,
      sourceName: ev.sourceName,
    });
  }
  eventCandidates.sort((a, b) => b.score - a.score);

  const topVenue = venueCandidates[0] ?? null;
  const topEvent = eventCandidates[0] ?? null;

  if (!topVenue && !topEvent) {
    const isShowingTomorrow = new Date().getHours() >= NEXT_DAY_CUTOFF_HOUR;
    const hadEarlierToday =
      VENUES.some((v) => areas.has(v.area) && v.events.some((e) => e.day === day)) ||
      events.some((e) => areas.has(e.area) && categorySet.has(e.category) && isSameDay(e.date, now));
    return {
      topVenue: null,
      topEvent: null,
      emptyMessage: isShowingTomorrow
        ? `Nothing scheduled for tomorrow (${day}).`
        : hadEarlierToday
        ? 'No more events tonight. Check back tomorrow.'
        : 'Nothing matching today. Try widening zones or categories.',
    };
  }

  return { topVenue, topEvent };
}

// ─── Multi-pick + weekly views ─────────────────────────────────────────────

export interface DayPlan {
  date: string;          // ISO YYYY-MM-DD
  dayName: DayName;
  isTonight: boolean;
  picks: Recommendation[];
  emptyMessage?: string;
}

export function getDayPicks(
  prefs: Preferences,
  events: LocalEvent[],
  targetDate: Date,
): DayPlan {
  const day = todayName(targetDate);
  const areas = allowedAreas(prefs);
  const categorySet = new Set(prefs.categories);
  const dateStr = targetDate.toISOString().slice(0, 10);

  const now = new Date();
  const todayStrNow = now.toISOString().slice(0, 10);
  const isLookingAtToday = dateStr === todayStrNow;

  // Score all venues for this day (including venues with happy hour but no event)
  const all: Recommendation[] = [];
  const seenVenueNames = new Set<string>();

  for (const venue of VENUES) {
    if (!areas.has(venue.area)) continue;
    const ev = venue.events.find((e) => e.day === day);
    const hasHappyHour = !!venue.happyHour && venue.happyHour.days.includes(day);

    // Include venue if it has an event today OR an active happy hour today
    if (!ev && !hasHappyHour) continue;

    // Build happy hour note
    let happyHourNote: string | undefined;
    let happyHourActive = false;
    if (hasHappyHour) {
      const hh = venue.happyHour!;
      happyHourNote = `Happy hour ${hh.start}-${hh.end}`;
      if (isLookingAtToday) {
        happyHourActive = isHappyHourActive(venue, now);
        if (happyHourActive) happyHourNote = `HH active now (until ${hh.end})`;
      }
    }

    // If there's a live event use it, otherwise show the happy hour as the "event"
    const eventTime = ev?.time ?? (venue.happyHour ? `${venue.happyHour.start}-${venue.happyHour.end}` : '');
    const eventType = ev?.type ?? (venue.happyHour ? (venue.happyHour.details ?? 'happy hour') : '');
    const fakeEvent: VenueEvent = ev ?? {
      day,
      type: eventType,
      time: eventTime,
      broadAppeal: true,
    };

    const { score, reason } = scoreVenueEvent(venue, fakeEvent, prefs.goal, prefs.vibe, hasHappyHour);
    const grade = gradeFor(score);

    seenVenueNames.add(venue.name);
    all.push({
      kind: 'venue',
      title: venue.name,
      area: venue.area,
      time: eventTime,
      subtitle: eventType,
      grade,
      decision: decisionFor(grade),
      reason,
      score,
      infoUrl: venue.infoUrl,
      happyHourNote,
      happyHourActive,
    });
  }

  // Score sample events for this day
  for (const ev of events) {
    if (!areas.has(ev.area)) continue;
    if (!categorySet.has(ev.category)) continue;
    if (ev.date !== dateStr) continue;

    const { score, reason } = scoreLocalEvent(ev, prefs.goal, prefs.vibe);
    const grade = gradeFor(score);
    all.push({
      kind: 'event',
      title: ev.title,
      area: ev.area,
      time: ev.time,
      subtitle: ev.description ?? ev.category.replace(/_/g, ' '),
      grade,
      decision: decisionFor(grade),
      reason,
      score,
      category: ev.category,
      sourceName: ev.sourceName,
    });
  }

  all.sort((a, b) => b.score - a.score);

  // Top 5 picks
  const picks = all.slice(0, 5);

  const todayStr = now.toISOString().slice(0, 10);
  const isTonight = dateStr === todayStr ||
    (now.getHours() >= NEXT_DAY_CUTOFF_HOUR && dateStr === new Date(Date.now() + 86400000).toISOString().slice(0, 10));

  return {
    date: dateStr,
    dayName: day,
    isTonight,
    picks,
    emptyMessage: picks.length === 0 ? `No events ${day}.` : undefined,
  };
}

export function getWeeklyPlan(
  prefs: Preferences,
  events: LocalEvent[],
): DayPlan[] {
  const now = new Date();
  const startDate = now.getHours() >= NEXT_DAY_CUTOFF_HOUR
    ? new Date(Date.now() + 86400000)
    : now;

  const plans: DayPlan[] = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(startDate);
    d.setDate(d.getDate() + i);
    d.setHours(12, 0, 0, 0);
    plans.push(getDayPicks(prefs, events, d));
  }
  return plans;
}
