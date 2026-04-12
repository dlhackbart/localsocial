import { useEffect, useState } from 'react';
import {
  FlatList, Pressable, StyleSheet, Text, TextInput, View,
} from 'react-native';
import { loadLogs, saveLog } from '../../src/store/logs';
import { colors, radius, spacing } from '../../src/theme';
import { Grade, LogEntry } from '../../src/types';

const GRADES: Grade[] = ['A', 'B', 'C'];
const AGAIN: LogEntry['wouldGoAgain'][] = ['yes', 'maybe', 'no'];

export default function LogScreen() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [wentOut, setWentOut] = useState(true);
  const [venue, setVenue] = useState('');
  const [grade, setGrade] = useState<Grade | null>(null);
  const [again, setAgain] = useState<LogEntry['wouldGoAgain']>(null);

  useEffect(() => { loadLogs().then(setLogs); }, []);

  const submit = async () => {
    if (!venue.trim()) return;
    const entry: LogEntry = {
      id: `${Date.now()}`,
      date: new Date().toISOString().slice(0, 10),
      wentOut,
      venue: venue.trim(),
      crowdGrade: grade,
      wouldGoAgain: again,
    };
    const next = await saveLog(entry);
    setLogs(next);
    setVenue(''); setGrade(null); setAgain(null); setWentOut(true);
  };

  return (
    <FlatList
      contentContainerStyle={styles.container}
      data={logs}
      keyExtractor={(item) => item.id}
      ListHeaderComponent={
        <View style={styles.form}>
          <Text style={styles.label}>Went out?</Text>
          <View style={styles.row}>
            <Chip active={wentOut} onPress={() => setWentOut(true)} label="Yes" />
            <Chip active={!wentOut} onPress={() => setWentOut(false)} label="No" />
          </View>

          <Text style={styles.label}>Venue</Text>
          <TextInput
            value={venue}
            onChangeText={setVenue}
            placeholder="Monarch Ocean Pub"
            placeholderTextColor={colors.textDim}
            style={styles.input}
          />

          <Text style={styles.label}>Crowd grade</Text>
          <View style={styles.row}>
            {GRADES.map((g) => (
              <Chip key={g} active={grade === g} onPress={() => setGrade(g)} label={g} />
            ))}
          </View>

          <Text style={styles.label}>Would go again?</Text>
          <View style={styles.row}>
            {AGAIN.map((a) => (
              <Chip key={a!} active={again === a} onPress={() => setAgain(a)} label={a!} />
            ))}
          </View>

          <Pressable onPress={submit} style={styles.submit}>
            <Text style={styles.submitText}>Save entry</Text>
          </Pressable>

          <Text style={[styles.label, { marginTop: spacing.lg }]}>Recent</Text>
        </View>
      }
      renderItem={({ item }) => (
        <View style={styles.logCard}>
          <Text style={styles.venueLine}>{item.venue}</Text>
          <Text style={styles.dim}>
            {item.date} · {item.wentOut ? 'went out' : 'stayed in'}
            {item.crowdGrade ? ` · grade ${item.crowdGrade}` : ''}
            {item.wouldGoAgain ? ` · again: ${item.wouldGoAgain}` : ''}
          </Text>
        </View>
      )}
      ListEmptyComponent={<Text style={styles.dim}>No entries yet.</Text>}
    />
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
  container: { padding: spacing.md, gap: spacing.md },
  form: { gap: spacing.sm },
  label: { color: colors.textDim, marginTop: spacing.sm },
  row: { flexDirection: 'row', gap: spacing.sm, flexWrap: 'wrap' },
  input: {
    backgroundColor: colors.card,
    color: colors.text,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.card,
  },
  chipText: { color: colors.text, textTransform: 'capitalize', fontWeight: '600' },
  submit: {
    marginTop: spacing.md,
    backgroundColor: colors.accent,
    padding: spacing.md,
    borderRadius: radius.md,
    alignItems: 'center',
  },
  submitText: { color: '#fff', fontWeight: '700' },
  logCard: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    marginTop: spacing.sm,
  },
  venueLine: { color: colors.text, fontWeight: '700' },
  dim: { color: colors.textDim, marginTop: spacing.xs },
});
