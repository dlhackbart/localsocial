export type Goal = 'dating' | 'social' | 'both';
export type Vibe = 'quiet' | 'balanced' | 'high';
export type Energy = 'low' | 'medium' | 'high';
export type Grade = 'A' | 'B' | 'C';
export type Decision = 'GO' | 'MAYBE' | 'SKIP';
export type DayName =
  | 'Sunday' | 'Monday' | 'Tuesday' | 'Wednesday'
  | 'Thursday' | 'Friday' | 'Saturday';

export type Category =
  | 'hiking_outdoor'
  | 'classes_workshops'
  | 'community_civic'
  | 'live_music_small'
  | 'art_galleries'
  | 'food_drink'
  | 'book_clubs'
  | 'markets'
  | 'theater_small'
  | 'movies_indie'
  | 'meetups_clubs'
  | 'wellness'
  | 'happy_hour';

export const CATEGORIES: { value: Category; label: string; icon: string }[] = [
  { value: 'hiking_outdoor',    label: 'Hiking & Outdoor',    icon: 'mountain' },
  { value: 'classes_workshops', label: 'Classes & Workshops', icon: 'class' },
  { value: 'community_civic',   label: 'Community & Civic',   icon: 'community' },
  { value: 'live_music_small',  label: 'Live Music (small)',  icon: 'music' },
  { value: 'art_galleries',     label: 'Art & Galleries',     icon: 'art' },
  { value: 'food_drink',        label: 'Food & Drink',        icon: 'food' },
  { value: 'book_clubs',        label: 'Book Clubs & Lit',    icon: 'book' },
  { value: 'markets',           label: 'Markets',             icon: 'market' },
  { value: 'theater_small',     label: 'Community Theater',   icon: 'theater' },
  { value: 'movies_indie',      label: 'Indie & Outdoor Film', icon: 'movie' },
  { value: 'meetups_clubs',     label: 'Meetups & Clubs',     icon: 'meetup' },
  { value: 'wellness',          label: 'Wellness & Yoga',     icon: 'wellness' },
  { value: 'happy_hour',        label: 'Happy Hour',          icon: 'drinks' },
];

export interface VenueEvent {
  day: DayName;
  type: string;
  time: string;
  broadAppeal: boolean;
}

export interface HappyHour {
  days: DayName[];       // e.g. ['Monday','Tuesday','Wednesday','Thursday','Friday']
  start: string;         // "3:00 PM" or "15:00"
  end: string;           // "5:00 PM" or "17:00"
  details?: string;      // "Half-off apps, $5 drafts, $8 wells"
}

export interface Venue {
  name: string;
  area: string;
  repeatFriendly: boolean;
  conversationFriendly: boolean;
  energy: Energy;
  lowSocialValue?: boolean;
  infoUrl?: string;
  happyHour?: HappyHour;
  events: VenueEvent[];
}

export interface Preferences {
  homeArea: string;
  enabledZones: string[];
  goal: Goal;
  vibe: Vibe;
  categories: Category[];
}

export interface LocalEvent {
  id: string;
  title: string;
  area: string;
  date: string;             // ISO YYYY-MM-DD
  time: string;             // human-readable, e.g. "6:00 PM"
  category: Category;
  description?: string;
  source: 'sample' | 'ical' | 'manual';
  sourceName?: string;      // e.g. "Del Mar Library"
  intimate: boolean;        // small gathering friendly
  conversationFriendly: boolean;
  repeatFriendly: boolean;  // recurring event, same crowd
  broadAppeal: boolean;
}

export type RecommendationKind = 'venue' | 'event';

export interface Recommendation {
  kind: RecommendationKind;
  title: string;            // venue name or event title
  area: string;
  time: string;
  subtitle: string;         // lineup / description
  grade: Grade;
  decision: Decision;
  reason: string;
  score: number;
  category?: Category;      // events only
  sourceName?: string;      // events only
  infoUrl?: string;         // tappable link for more info
  happyHourNote?: string;   // "Happy hour 3-5 PM" or "HH active now"
  happyHourActive?: boolean; // true if HH is happening right now (when viewing today)
}

export interface RecommendationResult {
  topVenue: Recommendation | null;
  topEvent: Recommendation | null;
  emptyMessage?: string;
}

export interface LogEntry {
  id: string;
  date: string;
  wentOut: boolean;
  venue: string;
  crowdGrade: Grade | null;
  wouldGoAgain: 'yes' | 'maybe' | 'no' | null;
}
