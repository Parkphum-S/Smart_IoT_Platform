import React from 'react';
import { StyleSheet, Text, View, SafeAreaView, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function DeviceDetailScreen({ route, navigation }: any) {
  const { deviceName } = route.params || { deviceName: 'อุปกรณ์ IoT' };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={20} color="#0F172A" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>ตั้งค่าอุปกรณ์เชิงลึก</Text>
      </View>

      <View style={styles.content}>
        <View style={styles.deviceIconLarge}>
          <Ionicons name="water" size={40} color="#059669" />
        </View>
        <Text style={styles.deviceName}>{deviceName}</Text>
        <Text style={styles.deviceStatus}>สถานะ: กำลังทำงาน (Online)</Text>

        <View style={styles.settingCard}>
          <Text style={styles.settingLabel}>ตั้งเวลาปิดอัตโนมัติ (Timer)</Text>
          <Text style={styles.settingValue}>15 นาที</Text>
        </View>

        <View style={styles.settingCard}>
          <Text style={styles.settingLabel}>เชื่อมต่อฮาร์ดแวร์ (Gateway)</Text>
          <Text style={styles.settingValue}>ESP32-Gateway-01</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  header: { flexDirection: 'row', alignItems: 'center', padding: 20, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  backButton: { marginRight: 16 },
  headerTitle: { fontSize: 16, fontWeight: 'bold', color: '#0F172A' },
  content: { padding: 24, alignItems: 'center' },
  deviceIconLarge: { width: 80, height: 80, borderRadius: 40, backgroundColor: '#D1FAE5', justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  deviceName: { fontSize: 18, fontWeight: 'bold', color: '#1E293B' },
  deviceStatus: { fontSize: 13, color: '#059669', marginTop: 4, marginBottom: 30 },
  settingCard: { width: '100%', flexDirection: 'row', justifyContent: 'space-between', backgroundColor: '#FFFFFF', padding: 18, borderRadius: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 1 },
  settingLabel: { fontSize: 14, color: '#334155', fontWeight: '500' },
  settingValue: { fontSize: 14, color: '#64748B', fontWeight: 'bold' },
});
