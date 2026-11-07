import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function AuditLogScreen() {
  const logs = [
    { id: '1', action: 'UPDATE_RELAY_STATE', user: 'parkphum@smartiot.local', ip: '192.168.1.50', time: '01:15:20' },
    { id: '2', action: 'SWITCH_WORKSPACE', user: 'parkphum@smartiot.local', ip: '192.168.1.50', time: '00:42:10' },
    { id: '3', action: 'SYSTEM_LOGIN_SUCCESS', user: 'parkphum@smartiot.local', ip: '192.168.1.50', time: '23:00:05' },
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.pageTitle}>ระบบ Audit Logs & ความปลอดภัย</Text>
      <Text style={styles.pageSub}>ตรวจสอบประวัติการทำรายการและสิทธิ์การใช้งานระบบ (RBAC)</Text>

      {logs.map(log => (
        <View key={log.id} style={styles.card}>
          <View style={styles.row}>
            <Ionicons name="shield-checkmark" size={18} color="#059669" />
            <View style={{ flex: 1, marginLeft: 10 }}>
              <Text style={styles.logAction}>{log.action}</Text>
              <Text style={styles.logMeta}>ผู้ใช้งาน: {log.user}</Text>
              <Text style={styles.logMeta}>IP: {log.ip} • เวลา: {log.time}</Text>
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
  card: { backgroundColor: '#FFF', borderRadius: 16, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: '#F1F5F9' },
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  logAction: { fontSize: 13, fontWeight: 'bold', color: '#1E293B' },
  logMeta: { fontSize: 11, color: '#64748B', marginTop: 2 },
});
