import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface RoomItem {
  id: number;
  name: string;
  zoneType: string;
  workspace: string;
  npk: string;
  ph: string;
}

export default function RoomManagementScreen() {
  const [rooms, setRooms] = useState<RoomItem[]>([
    { id: 1, name: 'แปลงเกษตรโซน A', zoneType: 'โซนพืชสวน', workspace: 'ฟาร์มตัวอย่าง', npk: 'N: 40, P: 25, K: 60', ph: '6.5' },
    { id: 2, name: 'โรงเรือนเพาะชำ', zoneType: 'โซนไม้ดอก', workspace: 'ฟาร์มตัวอย่าง', npk: 'N: 35, P: 30, K: 50', ph: '6.8' },
  ]);

  const [name, setName] = useState('');
  const [npk, setNpk] = useState('');
  const [ph, setPh] = useState('');

  const handleAddRoom = () => {
    if (!name.trim()) {
      Alert.alert('แจ้งเตือน', 'กรุณากรอกชื่อโซน');
      return;
    }
    const newRoom: RoomItem = {
      id: Date.now(),
      name: name.trim(),
      zoneType: 'โซนพืชสวน',
      workspace: 'ฟาร์มตัวอย่าง',
      npk: npk.trim() || '-',
      ph: ph.trim() || '-',
    };
    setRooms([newRoom, ...rooms]);
    setName('');
    setNpk('');
    setPh('');
    Alert.alert('สำเร็จ', 'เพิ่มโซนใหม่เรียบร้อยแล้ว');
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.pageTitle}>จัดการโซนและบันทึกค่า NPK/pH</Text>

      {/* ฟอร์มเพิ่มโซน */}
      <View style={styles.formCard}>
        <Text style={styles.formHeader}>เพิ่มโซนใหม่ / บันทึกข้อมูลดิน</Text>
        <TextInput
          style={styles.input}
          placeholder="ชื่อโซน (เช่น แปลงผักโซน B)"
          placeholderTextColor="#94A3B8"
          value={name}
          onChangeText={setName}
        />
        <TextInput
          style={styles.input}
          placeholder="ค่า NPK (เช่น N: 40, P: 25, K: 60)"
          placeholderTextColor="#94A3B8"
          value={npk}
          onChangeText={setNpk}
        />
        <TextInput
          style={styles.input}
          placeholder="ค่า pH ดิน (เช่น 6.5)"
          placeholderTextColor="#94A3B8"
          value={ph}
          onChangeText={setPh}
          keyboardType="numeric"
        />
        <TouchableOpacity style={styles.submitBtn} onPress={handleAddRoom}>
          <Ionicons name="add" size={18} color="#FFF" />
          <Text style={styles.submitBtnText}>บันทึกโซนใหม่</Text>
        </TouchableOpacity>
      </View>

      {/* รายการโซน */}
      <Text style={styles.listTitle}>รายชื่อโซนทั้งหมดในระบบ</Text>
      {rooms.map((room) => (
        <View key={room.id} style={styles.roomCard}>
          <View style={styles.roomLeft}>
            <View style={styles.roomIconBox}>
              <Ionicons name="grid-outline" size={20} color="#059669" />
            </View>
            <View>
              <Text style={styles.roomName}>{room.name}</Text>
              <Text style={styles.roomSub}>{room.zoneType} • {room.workspace}</Text>
              <Text style={styles.roomData}>🧪 NPK: {room.npk}</Text>
              <Text style={styles.roomData}>⚗️ pH: {room.ph}</Text>
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
  pageTitle: { fontSize: 20, fontWeight: '900', color: '#1E293B', marginBottom: 16 },
  formCard: { backgroundColor: '#FFF', borderRadius: 24, padding: 16, marginBottom: 20, borderWidth: 1, borderColor: '#F1F5F9' },
  formHeader: { fontSize: 14, fontWeight: 'bold', color: '#1E293B', marginBottom: 12 },
  input: { backgroundColor: '#F8FAFC', borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 16, paddingHorizontal: 14, paddingVertical: 12, fontSize: 12, fontWeight: '600', color: '#1E293B', marginBottom: 10 },
  submitBtn: { backgroundColor: '#059669', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 12, borderRadius: 16, gap: 6, marginTop: 4 },
  submitBtnText: { color: '#FFF', fontSize: 12, fontWeight: 'bold' },
  listTitle: { fontSize: 14, fontWeight: 'bold', color: '#1E293B', marginBottom: 10 },
  roomCard: { backgroundColor: '#FFF', borderRadius: 20, padding: 16, marginBottom: 10, borderWidth: 1, borderColor: '#F1F5F9' },
  roomLeft: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  roomIconBox: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#ECFDF5', alignItems: 'center', justifyContent: 'center' },
  roomName: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  roomSub: { fontSize: 11, color: '#059669', fontWeight: '600', marginVertical: 2 },
  roomData: { fontSize: 11, color: '#64748B', marginTop: 1 },
});
