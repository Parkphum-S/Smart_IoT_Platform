import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function NotificationScreen() {
  const notifications = [
    { id: '1', title: 'อุณหภูมิสูงเกินกำหนด', desc: 'แปลงเกษตรโซน A อุณหภูมิแตะ 34.2 °C เปิดระบบพ่นหมอกอัตโนมัติ', time: '10 นาทีที่แล้ว', type: 'warning' },
    { id: '2', title: 'ปั๊มน้ำทำงานสำเร็จ', desc: 'ระบบสั่งการรีเลย์ปั๊มน้ำ (Zone A) ทำงานตามรอบเวลา 06:00 น.', time: '2 ชั่วโมงที่แล้ว', type: 'success' },
    { id: '3', title: 'ค่า pH ผิดปกติเล็กน้อย', desc: 'ตรวจพบค่า pH ดิน 6.2 อยู่ในเกณฑ์ที่ต้องเฝ้าระวัง', time: '5 ชั่วโมงที่แล้ว', type: 'info' },
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.pageTitle}>ประวัติการแจ้งเตือน</Text>
      <Text style={styles.pageSub}>ติดตามเหตุการณ์และสถานะความผิดปกติของแปลงเกษตร</Text>

      {notifications.map(item => (
        <View key={item.id} style={styles.card}>
          <View style={styles.row}>
            <View style={[styles.iconBox, { backgroundColor: item.type === 'warning' ? '#FEF2F2' : '#F0FDF4' }]}>
              <Ionicons 
                name={item.type === 'warning' ? 'warning' : 'checkmark-circle'} 
                size={20} 
                color={item.type === 'warning' ? '#DC2626' : '#059669'} 
              />
            </View>
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text style={styles.notifTitle}>{item.title}</Text>
              <Text style={styles.notifDesc}>{item.desc}</Text>
              <Text style={styles.notifTime}>{item.time}</Text>
            </View>
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
  card: { backgroundColor: '#FFF', borderRadius: 20, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: '#F1F5F9' },
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  iconBox: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  notifTitle: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  notifDesc: { fontSize: 12, color: '#475569', marginVertical: 4 },
  notifTime: { fontSize: 10, color: '#94A3B8' },
});
