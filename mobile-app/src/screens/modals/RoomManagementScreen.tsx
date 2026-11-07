import React, { useState } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function RoomManagementScreen({ navigation }: any) {
  const [rooms] = useState([
    { id: 'r1', name: 'แปลงเกษตรโซน A', devices: 2 },
    { id: 'r2', name: 'โรงเรือนเพาะชำ', devices: 1 },
    { id: 'r3', name: 'แปลงเกษตรโซน B', devices: 2 },
  ]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={20} color="#0F172A" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>จัดการโซนและห้อง</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {rooms.map(room => (
          <View key={room.id} style={styles.roomCard}>
            <View>
              <Text style={styles.roomName}>{room.name}</Text>
              <Text style={styles.roomDevices}>อุปกรณ์ในโซนนี้: {room.devices} ตัว</Text>
            </View>
            <TouchableOpacity>
              <Ionicons name="trash-outline" size={18} color="#DC2626" />
            </TouchableOpacity>
          </View>
        ))}

        <TouchableOpacity style={styles.addButton}>
          <Ionicons name="add" size={18} color="#059669" style={{ marginRight: 8 }} />
          <Text style={styles.addButtonText}>เพิ่มโซนหรือห้องใหม่</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC', paddingTop: 40 },
  header: { flexDirection: 'row', alignItems: 'center', padding: 20, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  backButton: { marginRight: 16 },
  headerTitle: { fontSize: 16, fontWeight: 'bold', color: '#0F172A' },
  content: { padding: 20 },
  roomCard: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#FFFFFF', padding: 18, borderRadius: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 1 },
  roomName: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  roomDevices: { fontSize: 12, color: '#64748B', marginTop: 2 },
  addButton: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', backgroundColor: '#ECFDF5', padding: 16, borderRadius: 16, borderWidth: 1, borderColor: '#D1FAE5', marginTop: 10 },
  addButtonText: { color: '#059669', fontWeight: 'bold', fontSize: 14 },
});
