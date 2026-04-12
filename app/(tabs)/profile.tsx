import { Link } from 'expo-router';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import { usePreferences } from '../../src/store/preferences';
import { useSubscription } from '../../src/store/subscription';
import { colors, radius, spacing } from '../../src/theme';
import { Goal, Vibe } from '../../src/types';

const GOAL_LABEL: Record<Goal, string> = {
  dating: 'Dating — conversation & repeat crowds',
  social: 'Social — energy & events',
  both: 'Both — balanced scoring',
};

const VIBE_LABEL: Record<Vibe, string> = {
  quiet: 'Quiet — conversational',
  balanced: 'Balanced',
  high: 'High energy',
};

export default function ProfileScreen() {
  const { prefs } = usePreferences();
  const { state, setPlan } = useSubscription();

  const togglePlan = () => {
    const next = state.plan === 'paid' ? 'free' : 'paid';
    Alert.alert(
      next === 'paid' ? 'Upgrade to Paid' : 'Downgrade to Free',
      next === 'paid'
        ? 'Mock upgrade — real payment wiring is out of MVP scope. Continue?'
        : 'Switch back to 1 reveal per week?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'OK', onPress: () => setPlan(next) },
      ],
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Row label="Home area" value={prefs.homeArea} />
        <Row label="Nearby zones" value={prefs.enabledZones.join(', ') || '—'} />
        <Row label="Goal" value={GOAL_LABEL[prefs.goal]} />
        <Row label="Vibe" value={VIBE_LABEL[prefs.vibe]} />
      </View>

      <View style={styles.card}>
        <Row label="Plan" value={state.plan === 'paid' ? 'Paid · $12.99/mo' : 'Free · 1/week'} />
        <Row label="Reveals used" value={`${state.reveals.length}`} />
        <Pressable onPress={togglePlan} style={styles.cta}>
          <Text style={styles.ctaText}>
            {state.plan === 'paid' ? 'Switch to Free' : 'Upgrade to Paid (mock)'}
          </Text>
        </Pressable>
      </View>

      <Link href="/preferences" style={styles.link}>
        <Text style={styles.linkText}>Edit preferences</Text>
      </Link>
      <Link href="/add-source" style={styles.link}>
        <Text style={styles.linkText}>Add a calendar feed for {prefs.homeArea}</Text>
      </Link>

      <Text style={styles.dim}>
        Free: 1 reveal per ISO week. Paid: 1 per day. (Mock — no real payment.)
      </Text>
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.md, gap: spacing.md },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.sm,
  },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  rowLabel: { color: colors.textDim },
  rowValue: { color: colors.text, fontWeight: '600', maxWidth: '60%', textAlign: 'right' },
  cta: {
    marginTop: spacing.sm,
    backgroundColor: colors.accent,
    padding: spacing.md,
    borderRadius: radius.md,
    alignItems: 'center',
  },
  ctaText: { color: '#fff', fontWeight: '700' },
  link: { alignSelf: 'center' },
  linkText: { color: colors.accent, fontWeight: '600' },
  dim: { color: colors.textDim, fontSize: 12, textAlign: 'center', marginTop: spacing.lg },
});
