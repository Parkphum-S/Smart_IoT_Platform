import React from 'react';
import { StyleSheet, Text, View, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function AddDeviceScreen({ navigation }: any) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={20} color="#0F172A" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>เพิ่มอุปกรณ์ใหม่</Text>
      </View>

      <View style={styles.content}>
        <View style={styles.scanIconBox}>
          <Ionicons name="scan" size={48} color="#059669" />
        </View>
        <Text style={styles.scanText}>กำลังค้นหาอุปกรณ์ ESP32 และเซนเซอร์ใกล้เคียง...</Text>
        
        <TouchableOpacity style={styles.scanButton}>
          <Text style={styles.scanButtonText}>เริ่มสแกนอุปกรณ์</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC', paddingTop: 40 },
  header: { flexDirection: 'row', alignItems: 'center', padding: 20, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  backButton: { marginRight: 16 },
  headerTitle: { fontSize: 16, fontWeight: 'bold', color: '#0F172A' },
  content: { padding: 40, alignItems: 'center', justifyContent: 'center', flex: 1 },
  scanIconBox: { width: 96, height: 96, borderRadius: 48, backgroundColor: '#ECFDF5', justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  scanText: { fontSize: 14, color: '#64748B', textAlign: 'center', marginBottom: 40 },
  scanButton: { backgroundColor: '#059669', paddingVertical: 16, paddingHorizontal: 24, borderRadius: 20, width: '100%', alignItems: 'center', shadowColor: '#059669', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.2, shadowRadius: 8, elevation: 4 },
  scanButtonText: { color: '#FFFFFF', fontWeight: 'bold', fontSize: 15 },
});
