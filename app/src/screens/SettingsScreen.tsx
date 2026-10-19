import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';

export function SettingsScreen() {
  const items = [
    { label: 'Business Profile', icon: 'business-outline' },
    { label: 'Team & Permissions', icon: 'people-outline' },
    { label: 'SIM Gateways', icon: 'hardware-chip-outline' },
    { label: 'Knowledge Bases', icon: 'book-outline' },
    { label: 'Integrations', icon: 'extension-puzzle-outline' },
    { label: 'Calling Hours', icon: 'time-outline' },
    { label: 'Usage & Billing', icon: 'card-outline' },
    { label: 'Security & Sessions', icon: 'shield-outline' },
    { label: 'Help & Support', icon: 'help-circle-outline' },
  ];

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Settings</Text>
      {items.map((item) => (
        <TouchableOpacity key={item.label} style={styles.row}>
          <Text style={styles.label}>{item.label}</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#0F0F1A' },
  title: { fontSize: 24, fontWeight: '700', color: '#FFF', marginBottom: 16 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#1A1A2E', borderRadius: 12, padding: 16, marginBottom: 8 },
  label: { fontSize: 16, color: '#FFF' },
  chevron: { fontSize: 20, color: '#6C5CE7' },
});
