// Minimal iCalendar parser — handles line folding, VEVENT blocks, DTSTART/DTEND,
// SUMMARY, DESCRIPTION, LOCATION, CATEGORIES. Not a full RFC5545 implementation
// (no RRULE expansion, no VTIMEZONE resolution) but good enough for city/library
// calendar feeds which mostly publish flat instance events.

export interface RawICalEvent {
  uid: string;
  summary: string;
  description?: string;
  location?: string;
  categories?: string[];
  start: Date | null;
  end?: Date | null;
}

function unfold(text: string): string {
  // iCal folds long lines with CRLF + space/tab. Unfold first.
  return text.replace(/\r?\n[ \t]/g, '');
}

function parseDate(value: string): Date | null {
  // Forms: 20260412T190000Z, 20260412T190000, 20260412
  const m = value.match(/^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})(Z)?)?$/);
  if (!m) return null;
  const [, y, mo, d, h = '00', mi = '00', s = '00', z] = m;
  if (z) {
    return new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi, +s));
  }
  return new Date(+y, +mo - 1, +d, +h, +mi, +s);
}

function stripParams(line: string): { key: string; value: string } {
  const idx = line.indexOf(':');
  if (idx < 0) return { key: line, value: '' };
  const left = line.slice(0, idx);
  const value = line.slice(idx + 1);
  const keyEnd = left.indexOf(';');
  const key = (keyEnd < 0 ? left : left.slice(0, keyEnd)).toUpperCase();
  return { key, value };
}

export function parseICal(text: string): RawICalEvent[] {
  const unfolded = unfold(text);
  const lines = unfolded.split(/\r?\n/);
  const events: RawICalEvent[] = [];
  let current: Partial<RawICalEvent> | null = null;

  for (const raw of lines) {
    if (!raw) continue;
    if (raw === 'BEGIN:VEVENT') { current = {}; continue; }
    if (raw === 'END:VEVENT') {
      if (current && current.summary && current.start) {
        events.push({
          uid: current.uid ?? `ical_${events.length}_${current.start.getTime()}`,
          summary: current.summary,
          description: current.description,
          location: current.location,
          categories: current.categories,
          start: current.start,
          end: current.end,
        });
      }
      current = null;
      continue;
    }
    if (!current) continue;
    const { key, value } = stripParams(raw);
    switch (key) {
      case 'UID': current.uid = value; break;
      case 'SUMMARY': current.summary = decodeText(value); break;
      case 'DESCRIPTION': current.description = decodeText(value); break;
      case 'LOCATION': current.location = decodeText(value); break;
      case 'CATEGORIES':
        current.categories = value.split(',').map((s) => s.trim()).filter(Boolean);
        break;
      case 'DTSTART': current.start = parseDate(value); break;
      case 'DTEND': current.end = parseDate(value); break;
    }
  }
  return events;
}

function decodeText(s: string): string {
  return s
    .replace(/\\n/g, '\n')
    .replace(/\\,/g, ',')
    .replace(/\\;/g, ';')
    .replace(/\\\\/g, '\\');
}
