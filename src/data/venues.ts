import { Venue } from '../types';

export const VENUES: Venue[] = [
  // ---------- Del Mar ----------
  {
    name: 'Monarch Ocean Pub',
    area: 'Del Mar',
    repeatFriendly: true,
    conversationFriendly: true,
    energy: 'medium',
    events: [
      { day: 'Wednesday', type: 'acoustic', time: '4-7 PM', broadAppeal: true },
      { day: 'Thursday', type: 'acoustic', time: '4-7 PM', broadAppeal: true },
      { day: 'Friday', type: 'acoustic', time: '4-7 PM', broadAppeal: true },
      { day: 'Saturday', type: 'acoustic', time: '4-7 PM', broadAppeal: true },
      { day: 'Sunday', type: 'acoustic', time: '3-6 PM', broadAppeal: true },
    ],
  },
  {
    name: 'Del Mar Plaza',
    area: 'Del Mar',
    repeatFriendly: true,
    conversationFriendly: true,
    energy: 'medium',
    events: [
      { day: 'Thursday', type: 'Seaside Sessions', time: '5-7 PM', broadAppeal: true },
      { day: 'Saturday', type: 'Seaside Sessions', time: '5-7 PM', broadAppeal: true },
    ],
  },
  {
    name: 'Jake\'s Del Mar',
    area: 'Del Mar',
    repeatFriendly: true,
    conversationFriendly: true,
    energy: 'medium',
    events: [
      { day: 'Friday', type: 'happy hour', time: '4-6 PM', broadAppeal: true },
      { day: 'Saturday', type: 'sunset crowd', time: '5-8 PM', broadAppeal: true },
      { day: 'Sunday', type: 'brunch into afternoon', time: '11 AM-3 PM', broadAppeal: true },
    ],
  },

  // ---------- Solana Beach ----------
  {
    name: 'Belly Up Tavern',
    area: 'Solana Beach',
    repeatFriendly: false,
    conversationFriendly: false,
    energy: 'high',
    events: [
      { day: 'Thursday', type: 'rock headliner', time: '8:00 PM', broadAppeal: false },
      { day: 'Friday', type: '80s dance night', time: '8:00 PM', broadAppeal: true },
      { day: 'Saturday', type: 'tribute band', time: '8:00 PM', broadAppeal: true },
      { day: 'Sunday', type: 'Sunday residency', time: '7:00 PM', broadAppeal: false },
    ],
  },
  {
    name: 'Cedros District',
    area: 'Solana Beach',
    repeatFriendly: true,
    conversationFriendly: true,
    energy: 'medium',
    events: [
      { day: 'Wednesday', type: 'walkable district', time: '6-9 PM', broadAppeal: true },
      { day: 'Thursday', type: 'walkable district', time: '6-9 PM', broadAppeal: true },
      { day: 'Friday', type: 'walkable district', time: '6-9 PM', broadAppeal: true },
    ],
  },
  {
    name: 'Pizza Port Solana',
    area: 'Solana Beach',
    repeatFriendly: true,
    conversationFriendly: false,
    energy: 'high',
    events: [
      { day: 'Friday', type: 'brewery crowd', time: '6-10 PM', broadAppeal: true },
      { day: 'Saturday', type: 'brewery crowd', time: '6-10 PM', broadAppeal: true },
    ],
  },

  // ---------- Encinitas ----------
  {
    name: 'Union Kitchen & Tap',
    area: 'Encinitas',
    repeatFriendly: true,
    conversationFriendly: true,
    energy: 'medium',
    events: [
      { day: 'Wednesday', type: 'happy hour', time: '5-7 PM', broadAppeal: true },
      { day: 'Thursday', type: 'happy hour', time: '5-7 PM', broadAppeal: true },
      { day: 'Friday', type: 'DJ late set', time: '9 PM-close', broadAppeal: true },
    ],
  },
  {
    name: 'The Saloon',
    area: 'Encinitas',
    repeatFriendly: true,
    conversationFriendly: false,
    energy: 'high',
    events: [
      { day: 'Friday', type: 'live band', time: '9:00 PM', broadAppeal: true },
      { day: 'Saturday', type: 'live band', time: '9:00 PM', broadAppeal: true },
    ],
  },
  {
    name: 'Moonlight Beach Bar',
    area: 'Encinitas',
    repeatFriendly: false,
    conversationFriendly: false,
    energy: 'high',
    events: [
      { day: 'Saturday', type: 'DJ night', time: '9:00 PM', broadAppeal: false },
    ],
  },
  {
    name: '1st Street Bar',
    area: 'Encinitas',
    repeatFriendly: true,
    conversationFriendly: true,
    energy: 'medium',
    events: [
      { day: 'Tuesday', type: 'neighborhood night', time: '7-10 PM', broadAppeal: true },
      { day: 'Thursday', type: 'neighborhood night', time: '7-10 PM', broadAppeal: true },
      { day: 'Sunday', type: 'locals day', time: '3-7 PM', broadAppeal: true },
    ],
  },

  // ---------- Carlsbad ----------
  {
    name: 'Campfire',
    area: 'Carlsbad',
    repeatFriendly: true,
    conversationFriendly: true,
    energy: 'medium',
    events: [
      { day: 'Friday', type: 'patio scene', time: '6-9 PM', broadAppeal: true },
      { day: 'Saturday', type: 'patio scene', time: '6-9 PM', broadAppeal: true },
    ],
  },
  {
    name: 'Park 101',
    area: 'Carlsbad',
    repeatFriendly: false,
    conversationFriendly: false,
    energy: 'high',
    events: [
      { day: 'Friday', type: 'outdoor DJ', time: '8:00 PM', broadAppeal: true },
      { day: 'Saturday', type: 'outdoor DJ', time: '8:00 PM', broadAppeal: true },
    ],
  },
];
