import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { PreferencesProvider } from '../src/store/preferences';
import { SubscriptionProvider } from '../src/store/subscription';
import { colors } from '../src/theme';

export default function RootLayout() {
  return (
    <PreferencesProvider>
      <SubscriptionProvider>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.bg },
          headerTintColor: colors.text,
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="preferences" options={{ title: 'Preferences', presentation: 'modal' }} />
        <Stack.Screen name="add-source" options={{ title: 'Add a feed', presentation: 'modal' }} />
      </Stack>
      </SubscriptionProvider>
    </PreferencesProvider>
  );
}
