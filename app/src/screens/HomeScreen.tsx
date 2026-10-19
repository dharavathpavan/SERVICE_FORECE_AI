import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { api } from '../api/client';

export function HomeScreen() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.analytics()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color="#6C5CE7" /></View>;
  if (error) return <View style={styles.center}><Text style={styles.error}>{error}</Text></View>;

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Home Dashboard</Text>
      <Text style={styles.subtitle}>ServiceForce.ai — AI Calling Workspace</Text>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Total Calls Today</Text>
        <Text style={styles.cardValue}>{data?.total_calls_today ?? '—'}</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>AI-Resolved Calls</Text>
        <Text style={styles.cardValue}>{data?.ai_resolved_calls ?? '—'}</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Human Transfers</Text>
        <Text style={styles.cardValue}>{data?.human_transfers ?? '—'}</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Avg. Call Duration</Text>
        <Text style={styles.cardValue}>{data?.avg_duration ?? '—'}s</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#0F0F1A' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F0F1A' },
  title: { fontSize: 24, fontWeight: '700', color: '#FFF', marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#888', marginBottom: 20 },
  card: { backgroundColor: '#1A1A2E', borderRadius: 12, padding: 16, marginBottom: 12 },
  cardTitle: { fontSize: 13, color: '#888', marginBottom: 4 },
  cardValue: { fontSize: 28, fontWeight: '700', color: '#6C5CE7' },
  error: { color: '#FF6B6B', fontSize: 14 },
});
