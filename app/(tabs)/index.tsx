import { Link } from 'expo-router';
import { useMemo } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { VENUES } from '../../src/data/venues';
import { getSampleEvents } from '../../src/data/events';
import { getRecommendations, todayName } from '../../src/scoring';
import { usePreferences } from '../../src/store/preferences';
import { useSubscription } from '../../src/store/subscription';
import { colors, radius, spacing } from '../../src/theme';
import { CATEGORIES, Decision, Recommendation } from '../../src/types';

const decisionColor: Record<Decision, string> = {
  GO: colors.go,
  MAYBE: colors.maybe,
  SKIP: colors.skip,
};

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  CATEGORIES.map((c) => [c.value, c.label]),
);

function Card({ rec, label }: { rec: Recommendation; label: string }) {
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
      <Text style={styles.venue}>{rec.title}</Text>
      <Text style={styles.sub}>
        {rec.area} · {rec.time}
        {rec.sourceName ? ` · ${rec.sourceName}` : ''}
      </Text>
      <Text style={styles.sub}>{rec.subtitle}</Text>
      <View style={styles.row}>
        <View style={[styles.badge, { backgroundColor: decisionColor[rec.decision] }]}>
          <Text style={styles.badgeText}>{rec.decision}</Text>
        </View>
        <View style={[styles.badge, styles.gradeBadge]}>
          <Text style={styles.badgeText}>Grade {rec.grade}</Text>
        </View>
      </View>
      <Text style={styles.reason}>{rec.reason}</Text>
    </View>
  );
}

export default function HomeScreen() {
  const { prefs, ready: prefsReady } = usePreferences();
  const sub = useSubscription();

  // Compute everything synchronously — no async, no network, no loading screen
  const events = useMemo(() => getSampleEvents(), []);

  const result = useMemo(
    () => prefsReady ? getRecommendations(prefs, events) : null,
    [prefsReady, prefs, events],
  );

  if (!prefsReady || !sub.ready || !result) {
    return (
      <View style={[styles.container, styles.loadingContainer]}>
        <Text style={styles.loadingTitle}>Loading...</Text>
      </View>
    );
  }

  const now = new Date();
  const isLateNight = now.getHours() >= 22;
  const dayLabel = isLateNight
    ? `Tomorrow · ${todayName(new Date(Date.now() + 86400000))}`
    : todayName();

  const anyPick = result.topVenue || result.topEvent;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.header}>{dayLabel}</Text>
      <Text style={styles.dim}>
        {prefs.homeArea} · {prefs.enabledZones.length} nearby zones
      </Text>

      {anyPick ? (
        <>
          {result.topVenue && (
            <Card rec={result.topVenue} label={isLateNight ? 'Top Venue Tomorrow' : 'Top Venue Tonight'} />
          )}
          {result.topEvent && (
            <Card rec={result.topEvent} label={isLateNight ? 'Top Event Tomorrow' : 'Top Event Tonight'} />
          )}
          <Text style={styles.legend}>
            Grade A = strong match · B = decent · C = skip
          </Text>
        </>
      ) : (
        <View style={styles.card}>
          <Text style={styles.venue}>{result.emptyMessage ?? 'No matches today.'}</Text>
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
  },
  loadingTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
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
  link: { marginTop: spacing.md, alignSelf: 'center' },
  linkText: { color: colors.accent, fontWeight: '600' },
});
