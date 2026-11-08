import React from 'react';
import { StyleSheet, Text, View, TouchableOpacity, SafeAreaView, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function SettingsScreen({ navigation }: { navigation: any }) {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.title}>ตั้งค่าระบบ</Text>
          <Text style={styles.subtitle}>Smart IoT Platform - Farm Solution</Text>
        </View>

        <TouchableOpacity 
          style={styles.card}
          onPress={() => navigation.navigate('TuyaSettings')}
        >
          <View style={styles.iconContainer}>
            <Ionicons name="cloud-outline" size={24} color="#059669" />
          </View>
          <View style={styles.cardTextContainer}>
            <Text style={styles.cardTitle}>Tuya Cloud Integration</Text>
            <Text style={styles.cardDesc}>ตั้งค่า Access ID, Secret และซิงก์อุปกรณ์</Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color="#94a3b8" />
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  scrollContent: { padding: 20 },
  header: { marginBottom: 24 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#0f172a' },
  subtitle: { fontSize: 13, color: '#64748b', marginTop: 4 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: '#ecfdf5',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16
  },
  cardTextContainer: { flex: 1 },
  cardTitle: { fontSize: 15, fontWeight: '600', color: '#0f172a' },
  cardDesc: { fontSize: 12, color: '#64748b', marginTop: 2 }
});
