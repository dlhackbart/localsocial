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

export function getSampleEvents(from: Date = new Date()): LocalEvent[] {
  return SEEDS.map((s, i) => ({
    id: `sample_${i}`,
    title: s.title,
    area: s.area,
    date: nextOccurrence(s.day, from),
    time: s.time,
    category: s.category,
    description: s.description,
    source: 'sample',
    sourceName: s.sourceName,
    intimate: s.intimate ?? true,
    conversationFriendly: s.conversationFriendly ?? true,
    repeatFriendly: s.repeatFriendly ?? false,
    broadAppeal: s.broadAppeal ?? true,
  }));
}
