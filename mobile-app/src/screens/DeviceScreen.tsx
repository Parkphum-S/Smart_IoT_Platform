import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Switch, TouchableOpacity, TextInput, Modal } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface DeviceItem {
  id: string;
  name: string;
  zone: string;
  type: string;
  isOn: boolean;
  statusText: string;
}

export default function DeviceScreen() {
  const [devices, setDevices] = useState<DeviceItem[]>([
    { id: '1', name: 'ปั๊มน้ำหลัก (Main Pump)', zone: 'แปลงเกษตรโซน A', type: 'Relay 1', isOn: true, statusText: 'ทำงานอัตโนมัติ / เปิดอยู่' },
    { id: '2', name: 'ระบบพ่นหมอกความชื้น', zone: 'โรงเรือนเพาะชำ', type: 'Relay 2', isOn: false, statusText: 'ปิดใช้งาน' },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [newName, setNewName] = useState('');
  const [newZone, setNewZone] = useState('');

  const toggleDevice = (id: string) => {
    setDevices(devices.map(dev => {
      if (dev.id === id) {
        const nextState = !dev.isOn;
        return { ...dev, isOn: nextState, statusText: nextState ? 'เปิดใช้งาน (ควบคุมด้วยมือ)' : 'ปิดใช้งาน' };
      }
      return dev;
    }));
  };

  const addDevice = () => {
    if (!newName.trim()) return;
    const newItem: DeviceItem = {
      id: Date.now().toString(),
      name: newName,
      zone: newZone || 'แปลงเกษตรทั่วไป',
      type: 'Relay',
      isOn: false,
      statusText: 'ปิดใช้งาน',
    };
    setDevices([...devices, newItem]);
    setNewName('');
    setNewZone('');
    setModalVisible(false);
  };

  const deleteDevice = (id: string) => {
    setDevices(devices.filter(dev => dev.id !== id));
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.contentContainer}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.pageTitle}>ควบคุม & จัดการอุปกรณ์</Text>
            <Text style={styles.pageSub}>เพิ่มและควบคุมรีเลย์ฮาร์ดแวร์ในฟาร์ม</Text>
          </View>
          <TouchableOpacity style={styles.addButton} onPress={() => setModalVisible(true)}>
            <Ionicons name="add" size={20} color="#FFF" />
            <Text style={styles.addButtonText}>เพิ่มอุปกรณ์</Text>
          </TouchableOpacity>
        </View>

        {devices.map(device => (
          <View key={device.id} style={styles.deviceCard}>
            <View style={styles.deviceInfo}>
              <View style={[styles.iconBox, { backgroundColor: device.isOn ? '#ECFDF5' : '#F1F5F9' }]}>
                <Ionicons name={device.isOn ? "flash" : "flash-off"} size={22} color={device.isOn ? "#059669" : "#94A3B8"} />
              </View>
              <View style={{ flex: 1, marginHorizontal: 10 }}>
                <Text style={styles.deviceName}>{device.name}</Text>
                <Text style={styles.deviceZone}>📍 {device.zone}</Text>
                <Text style={[styles.deviceStatus, { color: device.isOn ? '#059669' : '#64748B' }]}>{device.statusText}</Text>
              </View>
              <Switch
                value={device.isOn}
                onValueChange={() => toggleDevice(device.id)}
                trackColor={{ false: '#CBD5E1', true: '#A7F3D0' }}
                thumbColor={device.isOn ? '#059669' : '#F8FAFC'}
              />
              <TouchableOpacity onPress={() => deleteDevice(device.id)} style={styles.deleteBtn}>
                <Ionicons name="trash-outline" size={18} color="#DC2626" />
              </TouchableOpacity>
            </View>
          </View>
        ))}
      </ScrollView>

      {/* Modal เพิ่มอุปกรณ์ */}
      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>➕ เพิ่มอุปกรณ์รีเลย์ใหม่</Text>
            <TextInput
              style={styles.input}
              placeholder="ชื่ออุปกรณ์ (เช่น ปั๊มน้ำโซน B)"
              placeholderTextColor="#94A3B8"
              value={newName}
              onChangeText={setNewName}
            />
            <TextInput
              style={styles.input}
              placeholder="โซน / โรงเรือน (เช่น โรงเรือนเพาะชำ)"
              placeholderTextColor="#94A3B8"
              value={newZone}
              onChangeText={setNewZone}
            />
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
                <Text style={styles.cancelText}>ยกเลิก</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.submitBtn} onPress={addDevice}>
                <Text style={styles.submitText}>บันทึก</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  contentContainer: { padding: 16, paddingBottom: 32 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  pageTitle: { fontSize: 18, fontWeight: '900', color: '#1E293B' },
  pageSub: { fontSize: 11, color: '#64748B', marginTop: 2 },
  addButton: { flexDirection: 'row', backgroundColor: '#059669', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 12, alignItems: 'center', gap: 4 },
  addButtonText: { color: '#FFF', fontSize: 12, fontWeight: 'bold' },
  deviceCard: { backgroundColor: '#FFF', borderRadius: 16, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: '#F1F5F9' },
  deviceInfo: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  deviceName: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  deviceZone: { fontSize: 11, color: '#475569', marginVertical: 2 },
  deviceStatus: { fontSize: 10, fontWeight: 'bold' },
  deleteBtn: { marginLeft: 12, padding: 6 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#FFF', width: '100%', borderRadius: 20, padding: 20 },
  modalTitle: { fontSize: 16, fontWeight: 'bold', color: '#1E293B', marginBottom: 16 },
  input: { borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 12, padding: 12, fontSize: 13, marginBottom: 12, color: '#1E293B' },
  modalActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, marginTop: 10 },
  cancelBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#F1F5F9' },
  cancelText: { color: '#64748B', fontWeight: 'bold', fontSize: 13 },
  submitBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#059669' },
  submitText: { color: '#FFF', fontWeight: 'bold', fontSize: 13 },
});
