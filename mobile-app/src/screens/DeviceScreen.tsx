import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Switch, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface DeviceItem {
  id: string;
  name: string;
  zone: string;
  type: string;
  isOn: boolean;
  statusText: string;
}

export default function DeviceScreen() {
  const [devices, setDevices] = useState<DeviceItem[]>([
    { id: '1', name: 'ปั๊มน้ำหลัก (Main Pump)', zone: 'แปลงเกษตรโซน A', type: 'Relay 1', isOn: true, statusText: 'ทำงานอัตโนมัติ / เปิดอยู่' },
    { id: '2', name: 'ระบบพ่นหมอกความชื้น', zone: 'โรงเรือนเพาะชำ', type: 'Relay 2', isOn: false, statusText: 'ปิดใช้งาน' },
    { id: '3', name: 'ไฟLED เสริมแสง', zone: 'โรงเรือนเพาะชำ', type: 'Relay 3', isOn: true, statusText: 'เปิดใช้งานตามเวลา' },
  ]);

  const toggleDevice = (id: string) => {
    setDevices(devices.map(dev => {
      if (dev.id === id) {
        const nextState = !dev.isOn;
        return {
          ...dev,
          isOn: nextState,
          statusText: nextState ? 'เปิดใช้งาน (ควบคุมด้วยมือ)' : 'ปิดใช้งาน'
        };
      }
      return dev;
    }));
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.pageTitle}>ควบคุมอุปกรณ์ฮาร์ดแวร์ & รีเลย์</Text>
      <Text style={styles.pageSub}>สั่งการและตรวจสอบสถานะอุปกรณ์ในฟาร์มแบบเรียลไทม์</Text>

      {devices.map(device => (
        <View key={device.id} style={styles.deviceCard}>
          <View style={styles.deviceInfo}>
            <View style={[styles.iconBox, { backgroundColor: device.isOn ? '#ECFDF5' : '#F1F5F9' }]}>
              <Ionicons 
                name={device.isOn ? "flash" : "flash-off"} 
                size={22} 
                color={device.isOn ? "#059669" : "#94A3B8"} 
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.deviceName}>{device.name}</Text>
              <Text style={styles.deviceZone}>📍 {device.zone}</Text>
              <Text style={[styles.deviceStatus, { color: device.isOn ? '#059669' : '#64748B' }]}>
                {device.statusText}
              </Text>
            </View>
            <Switch
              value={device.isOn}
              onValueChange={() => toggleDevice(device.id)}
              trackColor={{ false: '#CBD5E1', true: '#A7F3D0' }}
              thumbColor={device.isOn ? '#059669' : '#F8FAFC'}
            />
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  contentContainer: { padding: 16, paddingBottom: 32 },
  pageTitle: { fontSize: 20, fontWeight: '900', color: '#1E293B', marginBottom: 4 },
  pageSub: { fontSize: 12, color: '#64748B', marginBottom: 16 },
  deviceCard: { backgroundColor: '#FFF', borderRadius: 20, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: '#F1F5F9' },
  deviceInfo: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  iconBox: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  deviceName: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  deviceZone: { fontSize: 11, color: '#475569', marginVertical: 2 },
  deviceStatus: { fontSize: 11, fontWeight: 'bold' },
});
