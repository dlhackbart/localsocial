import { Link } from 'expo-router';
import { useMemo } from 'react';
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { getSampleEvents } from '../../src/data/events';
import { getWeeklyPlan, DayPlan } from '../../src/scoring';
import { usePreferences } from '../../src/store/preferences';
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

function PickCard({ rec, rank }: { rec: Recommendation; rank: number }) {
  const tag =
    rec.kind === 'event' && rec.category
      ? CATEGORY_LABELS[rec.category] ?? 'Event'
      : rec.subtitle;

  const handlePress = () => {
    if (rec.infoUrl) Linking.openURL(rec.infoUrl);
  };

  const Wrapper = rec.infoUrl ? Pressable : View;
  const wrapperProps = rec.infoUrl ? { onPress: handlePress } : {};

  return (
    <Wrapper {...wrapperProps} style={styles.pickRow}>
      <View style={styles.rankCircle}>
        <Text style={styles.rankText}>{rank}</Text>
      </View>
      <View style={styles.pickContent}>
        <View style={styles.titleRow}>
          <Text style={styles.pickTitle}>{rec.title}</Text>
          {rec.happyHourActive && (
            <View style={styles.hhBadgeActive}>
              <Text style={styles.hhBadgeActiveText}>HH NOW</Text>
            </View>
          )}
        </View>
        <Text style={styles.pickSub}>
          {rec.area} · {rec.time} · {tag}
        </Text>
        {rec.happyHourNote && !rec.happyHourActive && (
          <Text style={styles.hhNote}>{rec.happyHourNote}</Text>
        )}
        <View style={styles.pickBadges}>
          <View style={[styles.miniBadge, { backgroundColor: decisionColor[rec.decision] }]}>
            <Text style={styles.miniBadgeText}>{rec.decision}</Text>
          </View>
          <Text style={styles.pickGrade}>Grade {rec.grade}</Text>
          <Text style={styles.pickReason}>{rec.reason}</Text>
        </View>
        {rec.infoUrl && (
          <Text style={styles.infoLink}>More info →</Text>
        )}
      </View>
    </Wrapper>
  );
}

function FairgroundsSection({ events }: { events: ReturnType<typeof getSampleEvents> }) {
  const today = new Date().toISOString().slice(0, 10);
  const upcoming = events
    .filter((e) =>
      (e.sourceName === 'Del Mar Fairgrounds' || e.sourceName === 'Del Mar Racetrack') &&
      e.date >= today,
    )
    .slice(0, 6);

  if (upcoming.length === 0) return null;

  const openEvent = (title: string) => {
    const url = title.toLowerCase().includes('racing')
      ? 'https://www.dmtc.com'
      : 'https://www.delmarfairgrounds.com/events';
    Linking.openURL(url);
  };

  return (
    <View style={styles.fairCard}>
      <View style={styles.fairHeader}>
        <Text style={styles.fairTitle}>Del Mar Fairgrounds</Text>
        <Text style={styles.fairSub}>Half a mile from you</Text>
      </View>
      {upcoming.map((ev) => (
        <Pressable
          key={ev.id}
          onPress={() => openEvent(ev.title)}
          style={styles.fairRow}
        >
          <Text style={styles.fairEventDate}>{ev.date.slice(5)}</Text>
          <View style={styles.fairEventContent}>
            <Text style={styles.fairEventTitle}>{ev.title}</Text>
            <Text style={styles.fairEventTime}>{ev.time}</Text>
          </View>
        </Pressable>
      ))}
    </View>
  );
}

function DaySection({ plan }: { plan: DayPlan }) {
  const isTonight = plan.isTonight;
  const header = isTonight ? `Tonight — ${plan.dayName}` : plan.dayName;

  return (
    <View style={[styles.dayCard, isTonight && styles.dayCardTonight]}>
      <View style={styles.dayHeader}>
        <Text style={[styles.dayTitle, isTonight && styles.dayTitleTonight]}>
          {header}
        </Text>
        {!isTonight && (
          <Text style={styles.dayDate}>{plan.date.slice(5)}</Text>
        )}
      </View>

      {plan.picks.length > 0 ? (
        plan.picks.map((pick, i) => (
          <PickCard key={`${plan.date}-${i}`} rec={pick} rank={i + 1} />
        ))
      ) : (
        <Text style={styles.noEvents}>{plan.emptyMessage}</Text>
      )}
    </View>
  );
}

export default function HomeScreen() {
  const { prefs, ready } = usePreferences();

  const events = useMemo(() => getSampleEvents(), []);

  const weeklyPlan = useMemo(
    () => ready ? getWeeklyPlan(prefs, events) : [],
    [ready, prefs, events],
  );

  if (!ready || weeklyPlan.length === 0) {
    return (
      <View style={[styles.container, styles.loadingContainer]}>
        <Text style={styles.loadingTitle}>Loading...</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.header}>Social Plan</Text>
      <Text style={styles.dim}>
        {prefs.homeArea} + {prefs.enabledZones.join(', ')}
      </Text>

      {/* Happy Hour Now banner */}
      {weeklyPlan[0]?.picks.some((p) => p.happyHourActive) && (
        <View style={styles.hhBanner}>
          <Text style={styles.hhBannerTitle}>Happy Hour active right now</Text>
          <Text style={styles.hhBannerSub}>
            Regulars are showing up. Good chance to start being one.
          </Text>
        </View>
      )}

      {/* Del Mar Fairgrounds upcoming — 1/2 mile from home */}
      <FairgroundsSection events={events} />

      {weeklyPlan.map((plan) => (
        <DaySection key={plan.date} plan={plan} />
      ))}

      <Text style={styles.legend}>
        Grade A = strong match · B = decent · C = skip
      </Text>

      <Link href="/preferences" style={styles.link}>
        <Text style={styles.linkText}>Edit preferences</Text>
      </Link>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.md, gap: spacing.md },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
  },
  header: { color: colors.text, fontSize: 28, fontWeight: '700' },
  dim: { color: colors.textDim, marginBottom: spacing.sm },

  // Day sections
  dayCard: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.sm,
  },
  dayCardTonight: {
    borderColor: colors.accent,
    borderWidth: 2,
  },
  dayHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  dayTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
  },
  dayTitleTonight: {
    color: colors.accent,
    fontSize: 20,
  },
  dayDate: {
    color: colors.textDim,
    fontSize: 13,
  },
  noEvents: {
    color: colors.textDim,
    fontStyle: 'italic',
    paddingVertical: spacing.sm,
  },

  // Pick rows
  pickRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    paddingVertical: spacing.xs,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  rankCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.cardAlt,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 2,
  },
  rankText: {
    color: colors.text,
    fontWeight: '700',
    fontSize: 13,
  },
  pickContent: {
    flex: 1,
    gap: 2,
  },
  pickTitle: {
    color: colors.text,
    fontWeight: '700',
    fontSize: 16,
  },
  pickSub: {
    color: colors.textDim,
    fontSize: 13,
  },
  pickBadges: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: 2,
  },
  miniBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  miniBadgeText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 11,
  },
  pickGrade: {
    color: colors.textDim,
    fontSize: 12,
    fontWeight: '600',
  },
  pickReason: {
    color: colors.textDim,
    fontSize: 12,
    fontStyle: 'italic',
  },

  fairCard: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.md,
    borderWidth: 2,
    borderColor: colors.maybe, // gold-ish border for prominence
    gap: spacing.xs,
  },
  fairHeader: {
    marginBottom: spacing.sm,
  },
  fairTitle: {
    color: colors.maybe,
    fontSize: 18,
    fontWeight: '800',
  },
  fairSub: {
    color: colors.textDim,
    fontSize: 13,
    fontStyle: 'italic',
  },
  fairRow: {
    flexDirection: 'row',
    gap: spacing.md,
    paddingVertical: spacing.xs,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  fairEventDate: {
    color: colors.maybe,
    fontWeight: '700',
    fontSize: 14,
    width: 50,
  },
  fairEventContent: {
    flex: 1,
  },
  fairEventTitle: {
    color: colors.text,
    fontWeight: '600',
    fontSize: 15,
  },
  fairEventTime: {
    color: colors.textDim,
    fontSize: 12,
  },
  hhBanner: {
    backgroundColor: colors.go,
    padding: spacing.md,
    borderRadius: radius.lg,
    marginTop: spacing.sm,
  },
  hhBannerTitle: {
    color: '#fff',
    fontWeight: '800',
    fontSize: 16,
  },
  hhBannerSub: {
    color: '#fff',
    fontSize: 13,
    opacity: 0.9,
    marginTop: 4,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  hhBadgeActive: {
    backgroundColor: colors.go,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  hhBadgeActiveText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  hhNote: {
    color: colors.maybe,
    fontSize: 12,
    fontWeight: '600',
    fontStyle: 'italic',
  },
  infoLink: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: '600',
    marginTop: 4,
  },
  legend: { color: colors.textDim, fontSize: 12, textAlign: 'center' },
  link: { alignSelf: 'center' },
  linkText: { color: colors.accent, fontWeight: '600' },
});
