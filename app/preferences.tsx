import { router } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { AREAS } from '../src/data/areas';
import { usePreferences } from '../src/store/preferences';
import { colors, radius, spacing } from '../src/theme';
import { CATEGORIES, Category, Goal, Vibe } from '../src/types';

const GOALS: { value: Goal; label: string; hint: string }[] = [
  { value: 'dating', label: 'Dating', hint: 'Conversation-friendly, repeat crowds' },
  { value: 'social', label: 'Social', hint: 'High energy, events, density' },
  { value: 'both', label: 'Both', hint: 'Balanced scoring' },
];

const VIBES: { value: Vibe; label: string }[] = [
  { value: 'quiet', label: 'Quiet' },
  { value: 'balanced', label: 'Balanced' },
  { value: 'high', label: 'High energy' },
];

const HOME_AREAS = Object.keys(AREAS);

export default function PreferencesScreen() {
  const { prefs, updatePrefs } = usePreferences();

  const toggleZone = (zone: string) => {
    const enabled = prefs.enabledZones.includes(zone)
      ? prefs.enabledZones.filter((z) => z !== zone)
      : [...prefs.enabledZones, zone];
    updatePrefs({ enabledZones: enabled });
  };

  const setHomeArea = (area: string) => {
    updatePrefs({ homeArea: area, enabledZones: AREAS[area] ?? [] });
  };

  const toggleCategory = (cat: Category) => {
    const enabled = prefs.categories.includes(cat)
      ? prefs.categories.filter((c) => c !== cat)
      : [...prefs.categories, cat];
    updatePrefs({ categories: enabled });
  };

  const allOn = () => updatePrefs({ categories: CATEGORIES.map((c) => c.value) });
  const allOff = () => updatePrefs({ categories: [] });

  const nearby = AREAS[prefs.homeArea] ?? [];

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Section title="Home area">
        <View style={styles.row}>
          {HOME_AREAS.map((area) => (
            <Chip key={area} active={prefs.homeArea === area} onPress={() => setHomeArea(area)} label={area} />
          ))}
        </View>
      </Section>

      <Section title="Nearby zones">
        <View style={styles.row}>
          {nearby.map((zone) => (
            <Chip
              key={zone}
              active={prefs.enabledZones.includes(zone)}
              onPress={() => toggleZone(zone)}
              label={zone}
            />
          ))}
        </View>
      </Section>

      <Section title="Goal">
        {GOALS.map((g) => (
          <Pressable
            key={g.value}
            onPress={() => updatePrefs({ goal: g.value })}
            style={[styles.option, prefs.goal === g.value && styles.optionActive]}
          >
            <Text style={styles.optionLabel}>{g.label}</Text>
            <Text style={styles.optionHint}>{g.hint}</Text>
          </Pressable>
        ))}
      </Section>

      <Section title="Vibe">
        <View style={styles.row}>
          {VIBES.map((v) => (
            <Chip key={v.value} active={prefs.vibe === v.value} onPress={() => updatePrefs({ vibe: v.value })} label={v.label} />
          ))}
        </View>
      </Section>

      <Section title={`Event categories (${prefs.categories.length}/${CATEGORIES.length})`}>
        <View style={styles.row}>
          <Chip active={false} onPress={allOn} label="All on" />
          <Chip active={false} onPress={allOff} label="All off" />
        </View>
        <View style={[styles.row, { marginTop: spacing.sm }]}>
          {CATEGORIES.map((c) => (
            <Chip
              key={c.value}
              active={prefs.categories.includes(c.value)}
              onPress={() => toggleCategory(c.value)}
              label={c.label}
            />
          ))}
        </View>
      </Section>

      <Pressable onPress={() => router.back()} style={styles.done}>
        <Text style={styles.doneText}>Done</Text>
      </Pressable>
    </ScrollView>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Chip({ active, onPress, label }: { active: boolean; onPress: () => void; label: string }) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.chip, active && { backgroundColor: colors.accent, borderColor: colors.accent }]}
    >
      <Text style={[styles.chipText, active && { color: '#fff' }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.md, gap: spacing.lg },
  section: { gap: spacing.sm },
  sectionTitle: { color: colors.textDim, textTransform: 'uppercase', fontSize: 12, letterSpacing: 1 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.card,
  },
  chipText: { color: colors.text, fontWeight: '600' },
  option: {
    padding: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.card,
  },
  optionActive: { borderColor: colors.accent },
  optionLabel: { color: colors.text, fontWeight: '700' },
  optionHint: { color: colors.textDim, marginTop: spacing.xs, fontSize: 12 },
  done: {
    marginTop: spacing.md,
    backgroundColor: colors.accent,
    padding: spacing.md,
    borderRadius: radius.md,
    alignItems: 'center',
  },
  doneText: { color: '#fff', fontWeight: '700' },
});
