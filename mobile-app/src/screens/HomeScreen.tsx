import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface ZoneData {
  id: number;
  name: string;
  typeLabel: string;
  workspace: string;
  devicesCount: number;
  rawTemp: number;
  rawHumidity: number;
  npk: string;
  ph: string;
  relayStatus: string;
}

const ZONES: ZoneData[] = [
  {
    id: 1,
    name: 'แปลงเกษตรโซน A',
    typeLabel: 'โซนพืชสวน',
    workspace: 'ฟาร์มตัวอย่าง',
    devicesCount: 2,
    rawTemp: 32.5,
    rawHumidity: 68,
    npk: 'N: 40, P: 25, K: 60 mg/kg',
    ph: '6.5',
    relayStatus: 'เปิดใช้งาน (ปั๊มน้ำหลัก)',
  },
  {
    id: 2,
    name: 'โรงเรือนเพาะชำ',
    typeLabel: 'โซนไม้ดอก',
    workspace: 'ฟาร์มตัวอย่าง',
    devicesCount: 1,
    rawTemp: 29.0,
    rawHumidity: 75,
    npk: 'N: 35, P: 30, K: 50 mg/kg',
    ph: '6.8',
    relayStatus: 'ปิดใช้งาน (พ่นหมอก)',
  },
];

export default function HomeScreen() {
  const [selectedZone, setSelectedZone] = useState<ZoneData>(ZONES[0]);

  // คำนวณค่า VPD อัตโนมัติจากเซนเซอร์
  const calculateVPD = (temp: number, humidity: number) => {
    const svp = 0.61078 * Math.exp((17.27 * temp) / (temp + 237.3));
    const avp = svp * (humidity / 100);
    return (svp - avp).toFixed(2);
  };

  const vpdValue = calculateVPD(selectedZone.rawTemp, selectedZone.rawHumidity);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.pageTitle}>แดชบอร์ดภาพรวมแปลงเกษตร</Text>
      
      {/* OpenWeather API Widget */}
      <View style={styles.weatherCard}>
        <View style={styles.weatherHeader}>
          <View style={styles.weatherBadge}>
            <Text style={styles.weatherBadgeText}>OpenWeather API</Text>
          </View>
          <Text style={styles.weatherLocation}>📍 นนทบุรี, ประเทศไทย</Text>
        </View>
        <Text style={styles.weatherTemp}>31°C • มีเมฆบางส่วน</Text>
        <Text style={styles.weatherSub}>ความรู้สึกเหมือน 34°C • เหมาะแก่การเปิดพ่นหมอก</Text>
        
        <View style={styles.weatherStatsRow}>
          <View style={styles.weatherStatItem}>
            <Text style={styles.statLabel}>ความชื้นอากาศ</Text>
            <Text style={styles.statVal}>65%</Text>
          </View>
          <View style={[styles.weatherStatItem, styles.statBorder]}>
            <Text style={styles.statLabel}>ความเร็วลม</Text>
            <Text style={styles.statVal}>4.2 m/s</Text>
          </View>
          <View style={styles.weatherStatItem}>
            <Text style={styles.statLabel}>ดัชนี UV</Text>
            <Text style={[styles.statVal, { color: '#FCD34D' }]}>ปานกลาง (5)</Text>
          </View>
        </View>
      </View>

      {/* เลือกโซน */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>รายงานสถานะเซนเซอร์โซน</Text>
        <View style={styles.zoneSelectorRow}>
          {ZONES.map((zone) => (
            <TouchableOpacity
              key={zone.id}
              style={[styles.zoneBtn, selectedZone.id === zone.id && styles.zoneBtnActive]}
              onPress={() => setSelectedZone(zone)}
            >
              <Text style={[styles.zoneBtnText, selectedZone.id === zone.id && styles.zoneBtnTextActive]}>
                {zone.name}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* การแสดงผลข้อมูลเซนเซอร์, VPD, NPK, pH */}
      <View style={styles.zoneCard}>
        <View style={styles.zoneCardTop}>
          <Text style={styles.zoneTypeBadge}>{selectedZone.typeLabel}</Text>
          <Text style={styles.zoneNameText}>{selectedZone.name}</Text>
          <Text style={styles.workspaceText}>พื้นที่: {selectedZone.workspace}</Text>
        </View>

        <View style={styles.metricsGrid}>
          <View style={styles.metricBox}>
            <Ionicons name="thermometer-outline" size={18} color="#EF4444" />
            <Text style={styles.metricLabel}>อุณหภูมิ</Text>
            <Text style={styles.metricVal}>{selectedZone.rawTemp} °C</Text>
          </View>

          <View style={styles.metricBox}>
            <Ionicons name="water-outline" size={18} color="#3B82F6" />
            <Text style={styles.metricLabel}>ความชื้นอากาศ</Text>
            <Text style={styles.metricVal}>{selectedZone.rawHumidity} %</Text>
          </View>

          <View style={[styles.metricBox, styles.metricBoxVpd]}>
            <Ionicons name="analytics-outline" size={18} color="#059669" />
            <Text style={styles.metricLabelVpd}>ค่า VPD (คำนวณ)</Text>
            <Text style={styles.metricValVpd}>{vpdValue} kPa</Text>
          </View>
        </View>

        <View style={styles.infoBox}>
          <Text style={styles.infoTitle}>🧪 ค่า NPK (ผู้ใช้กรอก)</Text>
          <Text style={styles.infoText}>{selectedZone.npk}</Text>
        </View>

        <View style={styles.infoBox}>
          <Text style={styles.infoTitle}>⚗️ ค่า pH ดิน (ผู้ใช้กรอก)</Text>
          <Text style={styles.infoText}>{selectedZone.ph}</Text>
        </View>

        <View style={styles.relayBox}>
          <Ionicons name="flash-outline" size={16} color="#059669" />
          <Text style={styles.relayText}>สถานะรีเลย์: {selectedZone.relayStatus}</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  contentContainer: { padding: 16, paddingBottom: 32 },
  pageTitle: { fontSize: 20, fontWeight: '900', color: '#1E293B', marginBottom: 16 },
  weatherCard: { backgroundColor: '#059669', borderRadius: 24, padding: 20, marginBottom: 20 },
  weatherHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  weatherBadge: { backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  weatherBadgeText: { color: '#FFF', fontSize: 10, fontWeight: 'bold' },
  weatherLocation: { color: '#D1FAE5', fontSize: 12, fontWeight: '600' },
  weatherTemp: { color: '#FFF', fontSize: 28, fontWeight: '900', marginVertical: 4 },
  weatherSub: { color: '#ECFDF5', fontSize: 12, marginBottom: 16 },
  weatherStatsRow: { flexDirection: 'row', backgroundColor: 'rgba(0,0,0,0.15)', borderRadius: 16, padding: 12, justifyContent: 'space-between' },
  weatherStatItem: { flex: 1, alignItems: 'center' },
  statBorder: { borderLeftWidth: 1, borderRightWidth: 1, borderColor: 'rgba(255,255,255,0.2)' },
  statLabel: { color: '#D1FAE5', fontSize: 10, fontWeight: 'bold' },
  statVal: { color: '#FFF', fontSize: 13, fontWeight: '900', marginTop: 2 },
  sectionHeader: { marginBottom: 12 },
  sectionTitle: { fontSize: 14, fontWeight: 'bold', color: '#1E293B', marginBottom: 8 },
  zoneSelectorRow: { flexDirection: 'row', gap: 8 },
  zoneBtn: { backgroundColor: '#E2E8F0', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16 },
  zoneBtnActive: { backgroundColor: '#059669' },
  zoneBtnText: { fontSize: 12, fontWeight: 'bold', color: '#475569' },
  zoneBtnTextActive: { color: '#FFF' },
  zoneCard: { backgroundColor: '#FFF', borderRadius: 24, padding: 20, borderWidth: 1, borderColor: '#F1F5F9' },
  zoneCardTop: { marginBottom: 16 },
  zoneTypeBadge: { alignSelf: 'flex-start', backgroundColor: '#ECFDF5', color: '#047857', fontSize: 10, fontWeight: 'bold', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10, overflow: 'hidden', marginBottom: 6 },
  zoneNameText: { fontSize: 18, fontWeight: '900', color: '#1E293B' },
  workspaceText: { fontSize: 12, color: '#94A3B8', marginTop: 2 },
  metricsGrid: { flexDirection: 'row', gap: 10, marginBottom: 12 },
  metricBox: { flex: 1, backgroundColor: '#F8FAFC', padding: 12, borderRadius: 16, borderWidth: 1, borderColor: '#F1F5F9' },
  metricBoxVpd: { backgroundColor: '#ECFDF5', borderColor: '#A7F3D0' },
  metricLabel: { fontSize: 10, color: '#64748B', fontWeight: '600', marginTop: 4 },
  metricVal: { fontSize: 14, fontWeight: '900', color: '#1E293B', marginTop: 2 },
  metricLabelVpd: { fontSize: 10, color: '#047857', fontWeight: 'bold', marginTop: 4 },
  metricValVpd: { fontSize: 14, fontWeight: '900', color: '#065F46', marginTop: 2 },
  infoBox: { backgroundColor: '#F8FAFC', padding: 12, borderRadius: 16, marginBottom: 10, borderWidth: 1, borderColor: '#F1F5F9' },
  infoTitle: { fontSize: 11, fontWeight: 'bold', color: '#475569', marginBottom: 2 },
  infoText: { fontSize: 12, fontWeight: 'bold', color: '#1E293B' },
  relayBox: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#ECFDF5', padding: 12, borderRadius: 16, marginTop: 4 },
  relayText: { fontSize: 12, fontWeight: 'bold', color: '#065F46' },
});
