import { DayName, LocalEvent } from '../types';

// Sample events — seeded so the app has content before any iCal source is wired.
// `day` is used to project onto the current week (next occurrence).
// Replace/augment with live iCal feeds via src/events/fetcher.ts.

interface SampleSeed {
  title: string;
  area: string;
  day: DayName;
  time: string;
  category: LocalEvent['category'];
  description?: string;
  sourceName?: string;
  intimate?: boolean;
  conversationFriendly?: boolean;
  repeatFriendly?: boolean;
  broadAppeal?: boolean;
}

const SEEDS: SampleSeed[] = [
  // ---------- Hiking / Outdoor ----------
  { title: 'Torrey Pines Sunrise Hike', area: 'Del Mar', day: 'Saturday', time: '7:00 AM',
    category: 'hiking_outdoor', sourceName: 'North County Hikers',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true,
    description: 'Weekly sunrise hike, all levels. Coffee after at Roberto\'s.' },
  { title: 'Elfin Forest Moderate Hike', area: 'Encinitas', day: 'Sunday', time: '8:30 AM',
    category: 'hiking_outdoor', sourceName: 'Coastal Trail Group',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
  { title: 'Cardiff Beach Walk & Talk', area: 'Encinitas', day: 'Wednesday', time: '6:00 PM',
    category: 'hiking_outdoor', sourceName: 'Encinitas Parks & Rec',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },

  // ---------- Classes / Workshops ----------
  { title: 'Intro to Watercolor', area: 'Encinitas', day: 'Thursday', time: '6:30 PM',
    category: 'classes_workshops', sourceName: 'Encinitas Library',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
  { title: 'Spanish Conversation Circle', area: 'Solana Beach', day: 'Tuesday', time: '7:00 PM',
    category: 'classes_workshops', sourceName: 'Solana Beach Library',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true,
    description: 'All skill levels welcome. Small group, everyone introduces themselves.' },
  { title: 'Beginner Pottery Wheel', area: 'Carlsbad', day: 'Saturday', time: '10:00 AM',
    category: 'classes_workshops', sourceName: 'Carlsbad Community Arts',
    intimate: true, conversationFriendly: true, repeatFriendly: false, broadAppeal: true },

  // ---------- Community / Civic ----------
  { title: 'Del Mar Community Mixer', area: 'Del Mar', day: 'Thursday', time: '5:30 PM',
    category: 'community_civic', sourceName: 'Del Mar Village Association',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
  { title: 'Neighborhood Cleanup + Coffee', area: 'Solana Beach', day: 'Saturday', time: '9:00 AM',
    category: 'community_civic', sourceName: 'Solana Beach City',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },

  // ---------- Live Music (small) ----------
  { title: 'Acoustic Singer-Songwriter Night', area: 'Del Mar', day: 'Wednesday', time: '6:00 PM',
    category: 'live_music_small', sourceName: 'Monarch Ocean Pub',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
  { title: 'Jazz Trio on the Patio', area: 'Encinitas', day: 'Friday', time: '6:30 PM',
    category: 'live_music_small', sourceName: 'Union Kitchen',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },

  // ---------- Art / Galleries ----------
  { title: 'Cedros Art Walk', area: 'Solana Beach', day: 'Saturday', time: '5:00 PM',
    category: 'art_galleries', sourceName: 'Cedros District',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
  { title: 'Gallery Opening: Coastal Photography', area: 'Encinitas', day: 'Friday', time: '6:00 PM',
    category: 'art_galleries', sourceName: 'Encinitas Arts Center',
    intimate: true, conversationFriendly: true, repeatFriendly: false, broadAppeal: true },

  // ---------- Food / Drink ----------
  { title: 'Wine Tasting Flight Night', area: 'Del Mar', day: 'Thursday', time: '6:00 PM',
    category: 'food_drink', sourceName: 'Del Mar Plaza',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
  { title: 'Chef\'s Counter Tasting', area: 'Carlsbad', day: 'Friday', time: '7:00 PM',
    category: 'food_drink', sourceName: 'Campfire',
    intimate: true, conversationFriendly: true, repeatFriendly: false, broadAppeal: true },

  // ---------- Book Clubs ----------
  { title: 'Non-Fiction Book Club', area: 'Encinitas', day: 'Tuesday', time: '6:30 PM',
    category: 'book_clubs', sourceName: 'Encinitas Library',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: false },
  { title: 'Mystery Readers Circle', area: 'Solana Beach', day: 'Monday', time: '7:00 PM',
    category: 'book_clubs', sourceName: 'Solana Beach Library',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: false },

  // ---------- Markets ----------
  { title: 'Del Mar Farmers Market', area: 'Del Mar', day: 'Saturday', time: '1:00 PM',
    category: 'markets', sourceName: 'Del Mar City',
    intimate: false, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
  { title: 'Leucadia Farmers Market', area: 'Encinitas', day: 'Sunday', time: '10:00 AM',
    category: 'markets', sourceName: 'Leucadia 101',
    intimate: false, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },

  // ---------- Community Theater ----------
  { title: 'North Coast Rep Preview Night', area: 'Solana Beach', day: 'Thursday', time: '7:30 PM',
    category: 'theater_small', sourceName: 'North Coast Repertory',
    intimate: true, conversationFriendly: true, repeatFriendly: false, broadAppeal: true },

  // ---------- Indie / Outdoor Film ----------
  { title: 'Sunset Cinema on the Lawn', area: 'Del Mar', day: 'Friday', time: '7:30 PM',
    category: 'movies_indie', sourceName: 'Del Mar Plaza',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
  { title: 'Indie Film Discussion', area: 'Encinitas', day: 'Wednesday', time: '7:00 PM',
    category: 'movies_indie', sourceName: 'La Paloma Theatre',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: false },

  // ---------- Meetups / Clubs ----------
  { title: 'Classic Car Meetup', area: 'Carlsbad', day: 'Sunday', time: '8:00 AM',
    category: 'meetups_clubs', sourceName: 'North County Classics',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
  { title: 'Photography Walk', area: 'Encinitas', day: 'Saturday', time: '4:00 PM',
    category: 'meetups_clubs', sourceName: 'Coastal Lens Club',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },

  // ---------- Wellness ----------
  { title: 'Sunset Beach Yoga', area: 'Del Mar', day: 'Tuesday', time: '6:00 PM',
    category: 'wellness', sourceName: 'Coastal Yoga Collective',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
  { title: 'Sunrise Meditation & Tea', area: 'Solana Beach', day: 'Friday', time: '6:45 AM',
    category: 'wellness', sourceName: 'Mindful North County',
    intimate: true, conversationFriendly: true, repeatFriendly: true, broadAppeal: true },
];

const DAYS: DayName[] = [
  'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
];

function nextOccurrence(day: DayName, from: Date = new Date()): string {
  const todayIdx = from.getDay();
  const targetIdx = DAYS.indexOf(day);
  const offset = (targetIdx - todayIdx + 7) % 7;
  const d = new Date(from);
  d.setDate(d.getDate() + offset);
  return d.toISOString().slice(0, 10);
}

// ─── Del Mar Fairgrounds Events (fixed dates, 1/2 mile from home) ──────────
// San Diego County Fair: June 10 - July 5, 2026 (Wed-Sun)
// Toyota Summer Concert Series: specific dates during fair
// Del Mar Thoroughbred Club: July 17 - Sep 6 (Thu-Sun)

interface FixedEvent {
  title: string;
  date: string;           // ISO YYYY-MM-DD
  time: string;
  area: string;
  category: LocalEvent['category'];
  sourceName: string;
  description?: string;
  big?: boolean;
}

const FAIRGROUNDS_EVENTS: FixedEvent[] = [
  // Toyota Summer Concert Series
  { title: 'Chicago (Grandstand)', date: '2026-06-10', time: '7:30 PM', area: 'Del Mar', category: 'live_music_small', sourceName: 'Del Mar Fairgrounds', big: true },
  { title: 'Koe Wetzel (Grandstand)', date: '2026-06-12', time: '7:30 PM', area: 'Del Mar', category: 'live_music_small', sourceName: 'Del Mar Fairgrounds', big: true },
  { title: 'Los Tucanes de Tijuana (Grandstand)', date: '2026-06-14', time: '7:30 PM', area: 'Del Mar', category: 'live_music_small', sourceName: 'Del Mar Fairgrounds', big: true },
  { title: 'Marshmello (Grandstand)', date: '2026-06-19', time: '7:30 PM', area: 'Del Mar', category: 'live_music_small', sourceName: 'Del Mar Fairgrounds', big: true },
  { title: 'Good Charlotte (Grandstand)', date: '2026-06-20', time: '7:30 PM', area: 'Del Mar', category: 'live_music_small', sourceName: 'Del Mar Fairgrounds', big: true },
  { title: 'Nelly (Grandstand)', date: '2026-06-25', time: '7:30 PM', area: 'Del Mar', category: 'live_music_small', sourceName: 'Del Mar Fairgrounds', big: true },
  { title: 'Maren Morris (Grandstand)', date: '2026-06-26', time: '7:30 PM', area: 'Del Mar', category: 'live_music_small', sourceName: 'Del Mar Fairgrounds', big: true },
  { title: 'AJR (Grandstand)', date: '2026-07-01', time: '7:30 PM', area: 'Del Mar', category: 'live_music_small', sourceName: 'Del Mar Fairgrounds', big: true },
  // Del Mar Racing Opening Day
  { title: 'Del Mar Racing — Opening Day', date: '2026-07-17', time: '2:00 PM', area: 'Del Mar', category: 'meetups_clubs', sourceName: 'Del Mar Racetrack', description: 'Opening Day festivities, Hats Contest, Seabiscuit Society', big: true },
];

function getFairgroundsEvents(from: Date): LocalEvent[] {
  const today = from.toISOString().slice(0, 10);
  const out: LocalEvent[] = [];

  // Fixed-date events
  for (const fe of FAIRGROUNDS_EVENTS) {
    if (fe.date < today) continue;
    out.push({
      id: `fair_${fe.date}_${fe.title.slice(0, 20)}`,
      title: fe.title,
      area: fe.area,
      date: fe.date,
      time: fe.time,
      category: fe.category,
      description: fe.description,
      source: 'sample',
      sourceName: fe.sourceName,
      intimate: false,
      conversationFriendly: false,
      repeatFriendly: false,
      broadAppeal: true,
    });
  }

  // San Diego County Fair: June 10 - July 5, Wed-Sun
  const fairStart = new Date('2026-06-10');
  const fairEnd = new Date('2026-07-05');
  const d = new Date(Math.max(from.getTime(), fairStart.getTime()));
  while (d <= fairEnd) {
    const dow = d.getDay(); // 0=Sun
    // Wed=3, Thu=4, Fri=5, Sat=6, Sun=0
    if (dow === 0 || dow >= 3) {
      const iso = d.toISOString().slice(0, 10);
      out.push({
        id: `countyfair_${iso}`,
        title: 'San Diego County Fair',
        area: 'Del Mar',
        date: iso,
        time: '11:00 AM - 11:00 PM',
        category: 'markets',
        description: 'SD County Fair at Del Mar Fairgrounds',
        source: 'sample',
        sourceName: 'Del Mar Fairgrounds',
        intimate: false,
        conversationFriendly: true,
        repeatFriendly: false,
        broadAppeal: true,
      });
    }
    d.setDate(d.getDate() + 1);
  }

  // Del Mar Racing: July 17 - Sep 6, Thu-Sun
  const raceStart = new Date('2026-07-17');
  const raceEnd = new Date('2026-09-06');
  const rd = new Date(Math.max(from.getTime(), raceStart.getTime()));
  while (rd <= raceEnd) {
    const dow = rd.getDay();
    if (dow === 0 || dow >= 4) {  // Thu=4, Fri=5, Sat=6, Sun=0
      const iso = rd.toISOString().slice(0, 10);
      // Skip if already added (opening day)
      if (iso !== '2026-07-17') {
        out.push({
          id: `racing_${iso}`,
          title: 'Del Mar Racing',
          area: 'Del Mar',
          date: iso,
          time: '2:00 PM',
          category: 'meetups_clubs',
          description: 'Horse racing at Del Mar Thoroughbred Club',
          source: 'sample',
          sourceName: 'Del Mar Racetrack',
          intimate: false,
          conversationFriendly: true,
          repeatFriendly: true,
          broadAppeal: true,
        });
      }
    }
    rd.setDate(rd.getDate() + 1);
  }

  return out;
}

export function getSampleEvents(from: Date = new Date()): LocalEvent[] {
  const weekly = SEEDS.map((s, i) => ({
    id: `sample_${i}`,
    title: s.title,
    area: s.area,
    date: nextOccurrence(s.day, from),
    time: s.time,
    category: s.category,
    description: s.description,
    source: 'sample' as const,
    sourceName: s.sourceName,
    intimate: s.intimate ?? true,
    conversationFriendly: s.conversationFriendly ?? true,
    repeatFriendly: s.repeatFriendly ?? false,
    broadAppeal: s.broadAppeal ?? true,
  }));

  return [...weekly, ...getFairgroundsEvents(from)];
}
