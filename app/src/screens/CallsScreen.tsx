import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { api } from '../api/client';

export function CallsScreen() {
  const [calls, setCalls] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listCalls()
      .then((d) => setCalls(Array.isArray(d) ? d : d.items || []))
      .catch(() => setCalls([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color="#6C5CE7" /></View>;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Call History</Text>
      <FlatList
        data={calls}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.caller}>{item.caller_id || item.phone_number}</Text>
              <Text style={styles.status}>{item.status}</Text>
            </View>
            <Text style={styles.sub}>{item.direction} · {item.duration_seconds}s · ${item.estimated_cost?.toFixed(3)}</Text>
            <Text style={styles.outcome}>{item.outcome || 'pending'}</Text>
          </View>
        )}
        ListEmptyComponent={<Text style={styles.empty}>No calls yet.</Text>}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#0F0F1A' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F0F1A' },
  title: { fontSize: 24, fontWeight: '700', color: '#FFF', marginBottom: 16 },
  card: { backgroundColor: '#1A1A2E', borderRadius: 12, padding: 16, marginBottom: 12 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  caller: { fontSize: 16, fontWeight: '600', color: '#FFF' },
  status: { fontSize: 12, color: '#6C5CE7' },
  sub: { fontSize: 13, color: '#888', marginTop: 4 },
  outcome: { fontSize: 12, color: '#4ECDC4', marginTop: 2 },
  empty: { color: '#888', textAlign: 'center', marginTop: 40 },
});
