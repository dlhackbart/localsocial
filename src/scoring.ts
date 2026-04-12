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

function scoreVenueEvent(
  venue: Venue,
  event: VenueEvent,
  goal: Goal,
  vibe: Vibe,
): { score: number; reason: string } {
  let score = 0;
  const reasons: string[] = [];

  score += 5;

  const wantEnergy = goal === 'social' || goal === 'both';
  if (venue.energy === 'high' && wantEnergy) {
    score += 3;
    reasons.push('High social energy');
  }

  const wantConversation = goal === 'dating' || goal === 'both';
  if (venue.conversationFriendly && wantConversation) {
    score += 3;
    reasons.push('Strong for conversation');
  }

  if (venue.repeatFriendly) {
    score += 2;
    if (reasons.length === 0) reasons.push('Familiar local crowd');
  }

  if (event.broadAppeal) score += 2;
  if (venue.lowSocialValue) score -= 3;

  if (vibe === 'quiet' && venue.energy === 'high') score -= 2;
  if (vibe === 'high' && venue.energy === 'low') score -= 2;
  if (vibe === 'balanced' && venue.energy === 'medium') score += 1;

  if (goal === 'dating' && !venue.repeatFriendly) score -= 2;
  if (goal === 'dating' && !venue.conversationFriendly) score -= 2;

  return { score, reason: reasons[0] ?? 'Balanced environment' };
}

function scoreLocalEvent(
  ev: LocalEvent,
  goal: Goal,
  vibe: Vibe,
): { score: number; reason: string } {
  let score = 0;
  const reasons: string[] = [];

  score += 5; // event exists

  if (ev.intimate) {
    score += 2;
    reasons.push('Small intimate gathering');
  }

  const wantConversation = goal === 'dating' || goal === 'both';
  if (ev.conversationFriendly && wantConversation) {
    score += 3;
    reasons.push('Strong for conversation');
  }

  if (ev.repeatFriendly) {
    score += 2;
    if (reasons.length === 0) reasons.push('Recurring — same crowd returns');
  }

  if (ev.broadAppeal) score += 1;

  if (goal === 'dating' && !ev.repeatFriendly) score -= 1;
  if (vibe === 'quiet' && !ev.intimate) score -= 1;

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
  const first = time.split(/[-–—]/)[0].trim();
  const m = first.match(/^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$/i);
  if (!m) return null;
  let h = parseInt(m[1], 10);
  const mm = m[2] ? parseInt(m[2], 10) : 0;
  const ap = m[3]?.toUpperCase();
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

export function getRecommendations(
  prefs: Preferences,
  events: LocalEvent[] = [],
  now: Date = new Date(),
): RecommendationResult {
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
    // Was there anything earlier today that we just missed?
    const hadEarlierToday =
      VENUES.some((v) => areas.has(v.area) && v.events.some((e) => e.day === day)) ||
      events.some((e) => areas.has(e.area) && categorySet.has(e.category) && isSameDay(e.date, now));
    return {
      topVenue: null,
      topEvent: null,
      emptyMessage: hadEarlierToday
        ? 'No more events tonight. Check back tomorrow.'
        : 'Nothing matching today. Try widening zones or categories.',
    };
  }

  return { topVenue, topEvent };
}
