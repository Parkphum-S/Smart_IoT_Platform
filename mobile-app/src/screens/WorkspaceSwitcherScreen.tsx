import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function WorkspaceSwitcherScreen({ navigation }: any) {
  const workspaces = [
    { id: '1', name: 'ฟาร์มตัวอย่าง นนทบุรี (หลัก)', role: 'Owner', active: true, zones: '3 โซนใช้งาน' },
    { id: '2', name: 'โรงเรือนสมุนไพร ปทุมธานี', role: 'Manager', active: false, zones: '2 โซนใช้งาน' },
    { id: '3', name: 'แปลงทดลองเกษตรอัจฉริยะ เชียงใหม่', role: 'Viewer', active: false, zones: '1 โซนใช้งาน' },
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.pageTitle}>สลับ Workspace / ฟาร์ม</Text>
      <Text style={styles.pageSub}>เลือกฟาร์มหรือโรงเรือนที่คุณต้องการจัดการข้อมูล</Text>

      {workspaces.map(ws => (
        <TouchableOpacity key={ws.id} style={[styles.card, ws.active && styles.activeCard]}>
          <View style={styles.cardHeader}>
            <View style={styles.iconBox}>
              <Ionicons name="business" size={20} color="#059669" />
            </View>
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text style={styles.wsName}>{ws.name}</Text>
              <Text style={styles.wsMeta}>สิทธิ์ของคุณ: {ws.role} • {ws.zones}</Text>
            </View>
            {ws.active && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>ใช้งานอยู่</Text>
              </View>
            )}
          </View>
        </TouchableOpacity>
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
  activeCard: { borderColor: '#059669', backgroundColor: '#F0FDF4' },
  cardHeader: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#E6F4EA', alignItems: 'center', justifyContent: 'center' },
  wsName: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  wsMeta: { fontSize: 11, color: '#64748B', marginTop: 2 },
  badge: { backgroundColor: '#059669', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  badgeText: { fontSize: 10, color: '#FFF', fontWeight: 'bold' },
});
