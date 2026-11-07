import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Dimensions, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LineChart } from 'react-native-chart-kit';

export default function ChartScreen() {
  const screenWidth = Dimensions.get('window').width - 32;
  const [selectedZone, setSelectedZone] = useState('ZoneA');

  // ข้อมูลกราฟแยกตามโซน
  const zoneChartData = {
    ZoneA: {
      title: 'แปลงเกษตรโซน A (เมล่อนญี่ปุ่น)',
      labels: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
      datasets: [
        {
          data: [28.5, 27.8, 29.1, 31.5, 33.2, 34.0, 31.8, 29.5],
          color: (opacity = 1) => `rgba(239, 68, 68, ${opacity})`, // อุณหภูมิ
          strokeWidth: 2,
        },
        {
          data: [75, 78, 72, 65, 58, 55, 63, 70],
          color: (opacity = 1) => `rgba(5, 150, 105, ${opacity})`, // ความชื้น
          strokeWidth: 2,
        }
      ],
      legend: ['อุณหภูมิ (°C)', 'ความชื้น (%)'],
      summary: {
        tempRange: '34.0 °C / 27.8 °C',
        humidityRange: '78% / 55%',
        avgVpd: '1.55 kPa (เหมาะสม)',
      }
    },
    Greenhouse: {
      title: 'โรงเรือนเพาะชำ (ผักสลัดไฮโดรโปนิกส์)',
      labels: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
      datasets: [
        {
          data: [25.0, 24.5, 25.8, 28.0, 30.5, 31.2, 29.0, 26.5],
          color: (opacity = 1) => `rgba(239, 68, 68, ${opacity})`,
          strokeWidth: 2,
        },
        {
          data: [82, 85, 80, 72, 65, 62, 70, 78],
          color: (opacity = 1) => `rgba(5, 150, 105, ${opacity})`,
          strokeWidth: 2,
        }
      ],
      legend: ['อุณหภูมิ (°C)', 'ความชื้น (%)'],
      summary: {
        tempRange: '31.2 °C / 24.5 °C',
        humidityRange: '85% / 62%',
        avgVpd: '1.20 kPa (เหมาะสม)',
      }
    }
  };

  const current = zoneChartData[selectedZone as keyof typeof zoneChartData];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.pageTitle}>วิเคราะห์ข้อมูลย้อนหลัง & กราฟ</Text>
      <Text style={styles.pageSub}>แสดงแนวโน้มสภาพแวดล้อมรายโซนรอบ 24 ชั่วโมง</Text>

      {/* ปุ่มเลือกโซนสำหรับดูกราฟ */}
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

      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="stats-chart" size={20} color="#059669" />
          <Text style={styles.cardTitle}>{current.title}</Text>
        </View>

        <LineChart
          data={current}
          width={screenWidth}
          height={220}
          chartConfig={{
            backgroundColor: '#ffffff',
            backgroundGradientFrom: '#ffffff',
            backgroundGradientTo: '#ffffff',
            decimalPlaces: 1,
            color: (opacity = 1) => `rgba(5, 150, 105, ${opacity})`,
            labelColor: (opacity = 1) => `rgba(100, 116, 139, ${opacity})`,
            style: { borderRadius: 16 },
            propsForDots: {
              r: '5',
              strokeWidth: '2',
              stroke: '#059669',
            },
          }}
          bezier
          style={styles.chartStyle}
        />
      </View>

      <View style={styles.summaryCard}>
        <Text style={styles.summaryTitle}>📊 สรุปสถิติภาพรวมโซน</Text>
        <View style={styles.row}>
          <Text style={styles.label}>อุณหภูมิสูงสุด / ต่ำสุด:</Text>
          <Text style={styles.value}>{current.summary.tempRange}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>ความชื้นสูงสุด / ต่ำสุด:</Text>
          <Text style={styles.value}>{current.summary.humidityRange}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>ค่า VPD เฉลี่ย:</Text>
          <Text style={styles.value}>{current.summary.avgVpd}</Text>
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
  zoneTabs: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  zoneTabBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, backgroundColor: '#E2E8F0' },
  activeZoneBtn: { backgroundColor: '#059669' },
  zoneTabTxt: { fontSize: 12, fontWeight: 'bold', color: '#475569' },
  activeZoneTxt: { color: '#FFF' },
  card: { backgroundColor: '#FFF', borderRadius: 20, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: '#F1F5F9', alignItems: 'center' },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12, alignSelf: 'flex-start' },
  cardTitle: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  chartStyle: { marginVertical: 8, borderRadius: 16 },
  summaryCard: { backgroundColor: '#FFF', borderRadius: 20, padding: 16, borderWidth: 1, borderColor: '#F1F5F9' },
  summaryTitle: { fontSize: 14, fontWeight: 'bold', color: '#1E293B', marginBottom: 12 },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#F8FAFC' },
  label: { fontSize: 13, color: '#64748B' },
  value: { fontSize: 13, fontWeight: 'bold', color: '#059669' },
});
