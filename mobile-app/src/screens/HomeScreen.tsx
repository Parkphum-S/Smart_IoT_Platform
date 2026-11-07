import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function HomeScreen() {
  const [selectedZone, setSelectedZone] = useState('ZoneA');

  const zoneData = {
    ZoneA: {
      name: 'แปลงเกษตรโซน A',
      desc: 'พื้นที่: ฟาร์มตัวอย่างหลัก',
      temp: '32.5 °C',
      humidity: '68 %',
      vpd: '1.56 kPa',
      npk: 'N: 40, P: 25, K: 60 mg/kg',
      ph: '6.5',
      relayStatus: 'เปิดใช้งาน (ปั๊มน้ำหลัก)',
    },
    Greenhouse: {
      name: 'โรงเรือนเพาะชำ',
      desc: 'พื้นที่: โรงเรือนปิดควบคุมอุณหภูมิ',
      temp: '29.0 °C',
      humidity: '75 %',
      vpd: '1.20 kPa',
      npk: 'N: 50, P: 30, K: 70 mg/kg',
      ph: '6.8',
      relayStatus: 'เปิดใช้งาน (ระบบพ่นหมอก)',
    },
  };

  const current = zoneData[selectedZone as keyof typeof zoneData];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* สภาพอากาศภายนอก */}
      <View style={styles.weatherCard}>
        <View style={styles.rowBetween}>
          <Text style={styles.weatherBadge}>OpenWeather API</Text>
          <Text style={styles.locationText}>📍 นนทบุรี, ประเทศไทย</Text>
        </View>
        <Text style={styles.tempText}>31°C • มีเมฆบางส่วน</Text>
        <Text style={styles.weatherSub}>ความรู้สึกเหมือน 34°C • เหมาะกับการเปิดพ่นหมอก</Text>
        <View style={styles.weatherDetails}>
          <View style={styles.weatherItem}><Text style={styles.wLabel}>ความชื้นอากาศ</Text><Text style={styles.wVal}>65%</Text></View>
          <View style={styles.weatherItem}><Text style={styles.wLabel}>ความเร็วลม</Text><Text style={styles.wVal}>4.2 m/s</Text></View>
          <View style={styles.weatherItem}><Text style={styles.wLabel}>ดัชนี UV</Text><Text style={styles.wVal}>ปานกลาง (5)</Text></View>
        </View>
      </View>

      <Text style={styles.sectionTitle}>รายงานสถานะเซนเซอร์โซน</Text>

      {/* ปุ่มเลือกโซน (Zone Selector Tabs) */}
      <View style={styles.zoneTabs}>
        <TouchableOpacity 
          style={[styles.zoneTabBtn, selectedZone === 'ZoneA' && styles.activeZoneBtn]}
          onPress={() => setSelectedZone('ZoneA')}
        >
          <Text style={[styles.zoneTabTxt, selectedZone === 'ZoneA' && styles.activeZoneTxt]}>แปลงเกษตรโซน A</Text>
        </TouchableOpacity>

        <TouchableOpacity 
          style={[styles.zoneTabBtn, selectedZone === 'Greenhouse' && styles.activeZoneBtn]}
          onPress={() => setSelectedZone('Greenhouse')}
        >
          <Text style={[styles.zoneTabTxt, selectedZone === 'Greenhouse' && styles.activeZoneTxt]}>โรงเรือนเพาะชำ</Text>
        </TouchableOpacity>
      </View>

      {/* การ์ดแสดงค่าเซนเซอร์ตามโซนที่เลือก */}
      <View style={styles.sensorCard}>
        <Text style={styles.zoneCategory}>โซนพืชสวน</Text>
        <Text style={styles.zoneTitle}>{current.name}</Text>
        <Text style={styles.zoneDesc}>{current.desc}</Text>

        <View style={styles.sensorGrid}>
          <View style={styles.sensorBox}>
            <Ionicons name="thermometer-outline" size={18} color="#EF4444" />
            <Text style={styles.sLabel}>อุณหภูมิ</Text>
            <Text style={styles.sVal}>{current.temp}</Text>
          </View>
          <View style={styles.sensorBox}>
            <Ionicons name="water-outline" size={18} color="#3B82F6" />
            <Text style={styles.sLabel}>ความชื้นอากาศ</Text>
            <Text style={styles.sVal}>{current.humidity}</Text>
          </View>
          <View style={styles.sensorBox}>
            <Ionicons name="pulse-outline" size={18} color="#059669" />
            <Text style={styles.sLabel}>ค่า VPD (คำนวณ)</Text>
            <Text style={styles.sVal}>{current.vpd}</Text>
          </View>
        </View>

        <View style={styles.infoRow}>
          <Ionicons name="leaf-outline" size={16} color="#059669" />
          <Text style={styles.infoText}>ค่า NPK (ผู้ใช้กรอก): {current.npk}</Text>
        </View>

        <View style={styles.infoRow}>
          <Ionicons name="flask-outline" size={16} color="#059669" />
          <Text style={styles.infoText}>ค่า pH ดิน (ผู้ใช้กรอก): {current.ph}</Text>
        </View>

        <View style={styles.relayBox}>
          <Ionicons name="flash" size={16} color="#059669" />
          <Text style={styles.relayText}>สถานะรีเลย์: {current.relayStatus}</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  contentContainer: { padding: 16, paddingBottom: 32 },
  weatherCard: { backgroundColor: '#059669', borderRadius: 20, padding: 16, marginBottom: 16 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  weatherBadge: { backgroundColor: 'rgba(255,255,255,0.2)', color: '#FFF', fontSize: 10, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6, fontWeight: 'bold' },
  locationText: { color: '#FFF', fontSize: 12, fontWeight: '600' },
  tempText: { color: '#FFF', fontSize: 24, fontWeight: '900', marginBottom: 2 },
  weatherSub: { color: '#E2E8F0', fontSize: 11, marginBottom: 12 },
  weatherDetails: { flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.2)', paddingTop: 10 },
  weatherItem: { alignItems: 'center' },
  wLabel: { color: '#E2E8F0', fontSize: 10 },
  wVal: { color: '#FFF', fontSize: 12, fontWeight: 'bold', marginTop: 2 },
  sectionTitle: { fontSize: 15, fontWeight: 'bold', color: '#1E293B', marginBottom: 10 },
  zoneTabs: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  zoneTabBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, backgroundColor: '#E2E8F0' },
  activeZoneBtn: { backgroundColor: '#059669' },
  zoneTabTxt: { fontSize: 12, fontWeight: 'bold', color: '#475569' },
  activeZoneTxt: { color: '#FFF' },
  sensorCard: { backgroundColor: '#FFF', borderRadius: 20, padding: 16, borderWidth: 1, borderColor: '#F1F5F9' },
  zoneCategory: { fontSize: 11, color: '#64748B', fontWeight: 'bold' },
  zoneTitle: { fontSize: 18, fontWeight: '900', color: '#1E293B', marginVertical: 2 },
  zoneDesc: { fontSize: 11, color: '#94A3B8', marginBottom: 14 },
  sensorGrid: { flexDirection: 'row', gap: 8, marginBottom: 14 },
  sensorBox: { flex: 1, backgroundColor: '#F8FAFC', borderRadius: 12, padding: 10, alignItems: 'center', borderWidth: 1, borderColor: '#F1F5F9' },
  sLabel: { fontSize: 9, color: '#64748B', marginTop: 4, textAlign: 'center' },
  sVal: { fontSize: 12, fontWeight: 'bold', color: '#1E293B', marginTop: 2 },
  infoRow: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#F8FAFC', padding: 10, borderRadius: 10, marginBottom: 8, borderWidth: 1, borderColor: '#F1F5F9' },
  infoText: { fontSize: 12, color: '#334155', fontWeight: '600' },
  relayBox: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#ECFDF5', padding: 10, borderRadius: 10, borderWidth: 1, borderColor: '#A7F3D0', marginTop: 4 },
  relayText: { fontSize: 12, color: '#059669', fontWeight: 'bold' },
});
