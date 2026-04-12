import { Link } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { loadEvents } from '../../src/events/store';
import { getRecommendations, todayName } from '../../src/scoring';
import { usePreferences } from '../../src/store/preferences';
import { useSubscription } from '../../src/store/subscription';
import { colors, radius, spacing } from '../../src/theme';
import { CATEGORIES, Decision, LocalEvent, Recommendation } from '../../src/types';

const decisionColor: Record<Decision, string> = {
  GO: colors.go,
  MAYBE: colors.maybe,
  SKIP: colors.skip,
};

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  CATEGORIES.map((c) => [c.value, c.label]),
);

function Card({ rec, label, locked }: { rec: Recommendation; label: string; locked: boolean }) {
  const tag =
    rec.kind === 'event' && rec.category
      ? CATEGORY_LABELS[rec.category] ?? 'Event'
      : 'Regular spot';

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardLabel}>{label}</Text>
        <Text style={styles.pill}>{tag}</Text>
      </View>
      <Text style={styles.venue}>{locked ? '•••••••••' : rec.title}</Text>
      <Text style={styles.sub}>
        {rec.area} · {rec.time}
        {rec.sourceName ? ` · ${rec.sourceName}` : ''}
      </Text>
      <Text style={styles.sub}>{locked ? 'details hidden' : rec.subtitle}</Text>
      <View style={styles.row}>
        <View style={[styles.badge, { backgroundColor: locked ? colors.cardAlt : decisionColor[rec.decision] }]}>
          <Text style={styles.badgeText}>{locked ? 'LOCKED' : `Decision: ${rec.decision}`}</Text>
        </View>
        <View style={[styles.badge, styles.gradeBadge]}>
          <Text style={styles.badgeText}>{locked ? 'Grade hidden' : `Grade: ${rec.grade}`}</Text>
        </View>
      </View>
      <Text style={styles.reason}>{locked ? 'Unlock to see why.' : rec.reason}</Text>
    </View>
  );
}

export default function HomeScreen() {
  const { prefs, ready: prefsReady } = usePreferences();
  const { state, ready: subReady, canReveal, revealedToday, reveal, nextResetLabel } = useSubscription();
  const [events, setEvents] = useState<LocalEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState(true);

  useEffect(() => {
    if (!prefsReady) return;
    setEventsLoading(true);
    loadEvents(prefs.homeArea)
      .then(setEvents)
      .finally(() => setEventsLoading(false));
  }, [prefsReady, prefs.homeArea]);

  const result = useMemo(
    () => getRecommendations(prefs, events),
    [prefs, events],
  );

  if (!prefsReady || !subReady || eventsLoading) {
    return (
      <View style={[styles.container, styles.loadingContainer]}>
        <ActivityIndicator size="large" color={colors.accent} />
        <Text style={styles.loadingTitle}>One moment while we gather the data</Text>
        <Text style={styles.loadingSub}>
          First-time lookups for {prefs.homeArea} can take 5–15 seconds while we
          find and validate local event feeds. Subsequent visits are instant.
        </Text>
      </View>
    );
  }

  const unlocked = state.plan === 'paid' || revealedToday();
  const canUnlock = canReveal();
  const anyPick = result.topVenue || result.topEvent;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.header}>{todayName()}</Text>
      <Text style={styles.dim}>
        {prefs.homeArea} · {prefs.enabledZones.length} nearby zones · {state.plan === 'paid' ? 'Paid plan' : 'Free plan'}
      </Text>
      <Text style={styles.dim}>
        {prefs.categories.length}/{CATEGORIES.length} categories on ·{' '}
        {events.filter((e) => e.source === 'ical').length} live ·{' '}
        {events.filter((e) => e.source === 'sample').length} sample
      </Text>

      {events.filter((e) => e.source === 'ical').length === 0 && (
        <View style={styles.cta}>
          <Text style={styles.ctaTitle}>No live feeds for {prefs.homeArea} yet</Text>
          <Text style={styles.dim}>
            Know a public calendar? Adding one helps you and every other user in your area.
          </Text>
          <Link href="/add-source" style={styles.ctaLink}>
            <Text style={styles.linkText}>Add a calendar feed →</Text>
          </Link>
        </View>
      )}

      {anyPick ? (
        <>
          {result.topEvent && (
            <Card rec={result.topEvent} label="Top Event Tonight" locked={!unlocked} />
          )}
          {result.topVenue && (
            <Card rec={result.topVenue} label="Top Venue Tonight" locked={!unlocked} />
          )}
          {unlocked && (
            <Text style={styles.legend}>
              Grade A = strong match tonight · B = decent · C = skip
            </Text>
          )}
        </>
      ) : (
        <View style={styles.card}>
          <Text style={styles.venue}>{result.emptyMessage ?? 'No matches today.'}</Text>
        </View>
      )}

      {anyPick && !unlocked && (
        <View style={styles.gate}>
          {canUnlock ? (
            <Pressable onPress={reveal} style={styles.unlockBtn}>
              <Text style={styles.unlockText}>
                Unlock tonight's picks ({state.plan === 'free' ? '1 of 1 this week' : 'daily'})
              </Text>
            </Pressable>
          ) : (
            <>
              <Text style={styles.dim}>
                You've used this week's free reveal. Resets {nextResetLabel()}.
              </Text>
              <Link href="/(tabs)/profile" style={styles.link}>
                <Text style={styles.linkText}>Upgrade for daily picks →</Text>
              </Link>
            </>
          )}
        </View>
      )}

      <Link href="/preferences" style={styles.link}>
        <Text style={styles.linkText}>Edit preferences</Text>
      </Link>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.md, gap: spacing.md },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
    gap: spacing.md,
  },
  loadingTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
  },
  loadingSub: {
    color: colors.textDim,
    textAlign: 'center',
    lineHeight: 20,
  },
  header: { color: colors.text, fontSize: 28, fontWeight: '700' },
  dim: { color: colors.textDim },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.xs,
  },
  cardHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardLabel: { color: colors.textDim, textTransform: 'uppercase', fontSize: 12, letterSpacing: 1 },
  pill: {
    color: colors.text,
    backgroundColor: colors.cardAlt,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radius.md,
    fontSize: 11,
    overflow: 'hidden',
  },
  venue: { color: colors.text, fontSize: 22, fontWeight: '700' },
  sub: { color: colors.textDim, fontSize: 14 },
  row: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.sm },
  badge: { paddingHorizontal: spacing.md, paddingVertical: spacing.xs, borderRadius: radius.md },
  gradeBadge: { backgroundColor: colors.cardAlt },
  badgeText: { color: colors.text, fontWeight: '700' },
  reason: { color: colors.text, marginTop: spacing.sm, fontStyle: 'italic' },
  legend: { color: colors.textDim, fontSize: 12, textAlign: 'center' },
  gate: {
    backgroundColor: colors.cardAlt,
    padding: spacing.md,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    gap: spacing.sm,
  },
  unlockBtn: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
  },
  unlockText: { color: '#fff', fontWeight: '700' },
  link: { marginTop: spacing.md, alignSelf: 'center' },
  linkText: { color: colors.accent, fontWeight: '600' },
  cta: {
    backgroundColor: colors.cardAlt,
    padding: spacing.md,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.sm,
  },
  ctaTitle: { color: colors.text, fontWeight: '700' },
  ctaLink: { alignSelf: 'flex-start' },
});
