import { Category } from '../types';

export interface ICalSource {
  name: string;
  url: string;            // .ics URL
  area: string;           // area tag applied to all events from this feed
  defaultCategory: Category;
  intimate?: boolean;
  conversationFriendly?: boolean;
  repeatFriendly?: boolean;
}

// Live iCal feeds. On web (browser), cross-origin fetches to most municipal
// sites are blocked by CORS — this works from Expo Go / native builds, but
// will silently return no events on `expo start --web` without a proxy.
// The scoring engine falls back to sample events in src/data/events.ts, so
// the app still has content.

export const ICAL_SOURCES: ICalSource[] = [
  {
    name: 'Del Mar Community Calendar',
    url: 'https://www.delmar.ca.us/common/modules/iCalendar/iCalendar.aspx?catID=24&feed=calendar',
    area: 'Del Mar',
    defaultCategory: 'community_civic',
    intimate: true,
    conversationFriendly: true,
    repeatFriendly: false,
  },
  // ---- Investigated and rejected ----
  // Del Mar Public Meetings (catID=14): 51 events but all city council / holiday closures — not social.
  // Solana Beach city: Drupal, no public iCal export.
  // City of Encinitas: site blocks automated access.
  // Carlsbad city + library: blocks automated access.
  // SDCL (BiblioCommons): no public iCal feed.
  // Encinitas 101 (Squarespace): per-event .ics only, no master feed.
  // Visit Encinitas: Airtable-backed, no feed.
  // North County Daily Star / North Coast Current: WP Event Manager, no free feed.
];
