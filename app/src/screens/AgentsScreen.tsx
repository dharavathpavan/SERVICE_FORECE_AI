import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, FlatList } from 'react-native';
import { api } from '../api/client';

export function AgentsScreen() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listAgents()
      .then((d) => setAgents(Array.isArray(d) ? d : d.items || []))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color="#6C5CE7" /></View>;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>AI Agents</Text>
      <FlatList
        data={agents}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{item.name}</Text>
            <Text style={styles.cardSub}>{item.voice || 'Default voice'} · {item.language || 'en-US'}</Text>
            <Text style={styles.cardStatus}>{item.status || 'Draft'}</Text>
          </View>
        )}
        ListEmptyComponent={<Text style={styles.empty}>No agents yet. Create one to get started.</Text>}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#0F0F1A' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F0F1A' },
  title: { fontSize: 24, fontWeight: '700', color: '#FFF', marginBottom: 16 },
  card: { backgroundColor: '#1A1A2E', borderRadius: 12, padding: 16, marginBottom: 12 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#FFF' },
  cardSub: { fontSize: 13, color: '#888', marginTop: 4 },
  cardStatus: { fontSize: 12, color: '#6C5CE7', marginTop: 4 },
  empty: { color: '#888', textAlign: 'center', marginTop: 40 },
});
