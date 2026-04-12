import { router } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from 'react-native';
import { addUserSource } from '../src/events/resolver';
import { usePreferences } from '../src/store/preferences';
import { colors, radius, spacing } from '../src/theme';
import { CATEGORIES, Category } from '../src/types';

export default function AddSourceScreen() {
  const { prefs } = usePreferences();
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [category, setCategory] = useState<Category>('community_civic');
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!name.trim() || !url.trim()) {
      Alert.alert('Missing info', 'Name and URL are required.');
      return;
    }
    setSubmitting(true);
    const res = await addUserSource({
      areaLabel: prefs.homeArea,
      name: name.trim(),
      url: url.trim(),
      category,
    });
    setSubmitting(false);
    if (res.ok) {
      Alert.alert('Added', 'Feed validated and saved. It will show on Tonight after the next refresh.');
      router.back();
    } else {
      Alert.alert('Could not add', res.error ?? 'Unknown error');
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Add a calendar feed</Text>
      <Text style={styles.dim}>
        Help your area. Paste a public iCalendar (.ics) URL from your city, library, chamber, or community center.
        The feed is validated before being saved and shared with other users in {prefs.homeArea}.
      </Text>

      <Text style={styles.label}>Name</Text>
      <TextInput
        value={name}
        onChangeText={setName}
        placeholder="Encinitas Library Events"
        placeholderTextColor={colors.textDim}
        style={styles.input}
      />

      <Text style={styles.label}>iCal URL (.ics)</Text>
      <TextInput
        value={url}
        onChangeText={setUrl}
        placeholder="https://example.com/calendar.ics"
        placeholderTextColor={colors.textDim}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        style={styles.input}
      />

      <Text style={styles.label}>Default category</Text>
      <View style={styles.row}>
        {CATEGORIES.map((c) => (
          <Pressable
            key={c.value}
            onPress={() => setCategory(c.value)}
            style={[styles.chip, category === c.value && styles.chipActive]}
          >
            <Text style={[styles.chipText, category === c.value && styles.chipTextActive]}>
              {c.label}
            </Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.label}>Area</Text>
      <Text style={styles.area}>{prefs.homeArea}</Text>

      <Pressable onPress={submit} style={styles.submit} disabled={submitting}>
        {submitting ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.submitText}>Validate & save</Text>
        )}
      </Pressable>

      <Pressable onPress={() => router.back()} style={styles.cancel}>
        <Text style={styles.cancelText}>Cancel</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.md, gap: spacing.md },
  title: { color: colors.text, fontSize: 22, fontWeight: '700' },
  dim: { color: colors.textDim },
  label: { color: colors.textDim, marginTop: spacing.sm },
  input: {
    backgroundColor: colors.card,
    color: colors.text,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.card,
  },
  chipActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { color: colors.text, fontWeight: '600' },
  chipTextActive: { color: '#fff' },
  area: { color: colors.text, fontWeight: '600' },
  submit: {
    marginTop: spacing.md,
    backgroundColor: colors.accent,
    padding: spacing.md,
    borderRadius: radius.md,
    alignItems: 'center',
  },
  submitText: { color: '#fff', fontWeight: '700' },
  cancel: { alignItems: 'center', padding: spacing.sm },
  cancelText: { color: colors.textDim },
});
