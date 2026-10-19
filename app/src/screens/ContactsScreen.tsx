import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { api } from '../api/client';

export function ContactsScreen() {
  const [contacts, setContacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listContacts()
      .then((d) => setContacts(Array.isArray(d) ? d : d.items || []))
      .catch(() => setContacts([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color="#6C5CE7" /></View>;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Contacts</Text>
      <FlatList
        data={contacts}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.name}>{item.name || item.phone_number}</Text>
            <Text style={styles.sub}>{item.phone_number} · {item.email || 'no email'}</Text>
            <Text style={styles.tag}>{item.opted_out ? 'Opted out' : 'Active'}</Text>
          </View>
        )}
        ListEmptyComponent={<Text style={styles.empty}>No contacts yet.</Text>}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#0F0F1A' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F0F1A' },
  title: { fontSize: 24, fontWeight: '700', color: '#FFF', marginBottom: 16 },
  card: { backgroundColor: '#1A1A2E', borderRadius: 12, padding: 16, marginBottom: 12 },
  name: { fontSize: 16, fontWeight: '600', color: '#FFF' },
  sub: { fontSize: 13, color: '#888', marginTop: 4 },
  tag: { fontSize: 12, color: '#4ECDC4', marginTop: 4 },
  empty: { color: '#888', textAlign: 'center', marginTop: 40 },
});
