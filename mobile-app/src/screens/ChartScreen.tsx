import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function ChartScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.pageTitle}>วิเคราะห์ข้อมูลย้อนหลัง & กราฟ</Text>
      <Text style={styles.pageSub}>แสดงแนวโน้มสภาพแวดล้อมและค่า VPD ย้อนหลัง 24 ชั่วโมง</Text>

      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="stats-chart" size={20} color="#059669" />
          <Text style={styles.cardTitle}>กราฟแสดงค่าอุณหภูมิและความชื้น</Text>
        </View>
        <View style={styles.chartPlaceholder}>
          <Ionicons name="analytics-outline" size={48} color="#CBD5E1" />
          <Text style={styles.placeholderText}>กำลังดึงข้อมูล Telemetry ย้อนหลัง...</Text>
          <Text style={styles.subPlaceholder}>ระบบพร้อมเชื่อมต่อฐานข้อมูลสตรีมมิ่งเซนเซอร์</Text>
        </View>
      </View>

      <View style={styles.summaryCard}>
        <Text style={styles.summaryTitle}>📊 สรุปสถิติรอบ 24 ชั่วโมง</Text>
        <View style={styles.row}>
          <Text style={styles.label}>อุณหภูมิเฉลี่ย:</Text>
          <Text style={styles.value}>31.8 °C</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>ความชื้นเฉลี่ย:</Text>
          <Text style={styles.value}>66.5 %</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>ค่า VPD เฉลี่ย:</Text>
          <Text style={styles.value}>1.50 kPa</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  contentContainer: { padding: 16, paddingBottom: 32 },
  pageTitle: { fontSize: 20, fontWeight: '900', color: '#1E293B', marginBottom: 4 },
  pageSub: { fontSize: 12, color: '#64748B', marginBottom: 16 },
  card: { backgroundColor: '#FFF', borderRadius: 20, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: '#F1F5F9' },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  cardTitle: { fontSize: 15, fontWeight: 'bold', color: '#1E293B' },
  chartPlaceholder: { height: 180, backgroundColor: '#F8FAFC', borderRadius: 14, justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderStyle: 'dashed', borderColor: '#CBD5E1' },
  placeholderText: { fontSize: 13, fontWeight: '600', color: '#475569', marginTop: 8 },
  subPlaceholder: { fontSize: 11, color: '#94A3B8', marginTop: 4 },
  summaryCard: { backgroundColor: '#FFF', borderRadius: 20, padding: 16, borderWidth: 1, borderColor: '#F1F5F9' },
  summaryTitle: { fontSize: 14, fontWeight: 'bold', color: '#1E293B', marginBottom: 12 },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#F8FAFC' },
  label: { fontSize: 13, color: '#64748B' },
  value: { fontSize: 13, fontWeight: 'bold', color: '#059669' },
});
