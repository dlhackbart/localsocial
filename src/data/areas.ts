export const AREAS: Record<string, string[]> = {
  'Del Mar': ['Solana Beach', 'Encinitas'],
  'Solana Beach': ['Del Mar', 'Encinitas'],
  'Encinitas': ['Solana Beach', 'Carlsbad'],
  'Carlsbad': ['Encinitas'],
};

export const DEFAULT_HOME_AREA = 'Del Mar';
