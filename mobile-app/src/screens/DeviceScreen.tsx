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
    { id: '1', name: 'ปั๊มน้ำหลัก (Main Pump)', zone: 'แปลงเกษตรโซน A', type: 'Relay ปั๊มน้ำ', isOn: true, statusText: 'ทำงานอัตโนมัติ / เปิดอยู่' },
    { id: '2', name: 'ระบบพ่นหมอกความชื้น', zone: 'โรงเรือนเพาะชำ', type: 'ระบบพ่นหมอก', isOn: false, statusText: 'ปิดใช้งาน' },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [selectedZone, setSelectedZone] = useState('แปลงเกษตรโซน A');
  const [deviceType, setDeviceType] = useState('Relay ปั๊มน้ำ');

  const toggleDevice = (id: string) => {
    setDevices(devices.map(dev => {
      if (dev.id === id) {
        const nextState = !dev.isOn;
        return { ...dev, isOn: nextState, statusText: nextState ? 'เปิดใช้งาน (ควบคุมด้วยมือ)' : 'ปิดใช้งาน' };
      }
      return dev;
    }));
  };

  const openAddModal = () => {
    setEditingId(null);
    setNewName('');
    setSelectedZone('แปลงเกษตรโซน A');
    setDeviceType('Relay ปั๊มน้ำ');
    setModalVisible(true);
  };

  const openEditModal = (device: DeviceItem) => {
    setEditingId(device.id);
    setNewName(device.name);
    setSelectedZone(device.zone);
    setDeviceType(device.type);
    setModalVisible(true);
  };

  const saveDevice = () => {
    if (!newName.trim()) return;
    if (editingId) {
      setDevices(devices.map(dev => dev.id === editingId ? {
        ...dev,
        name: newName,
        zone: selectedZone,
        type: deviceType,
      } : dev));
    } else {
      const newItem: DeviceItem = {
        id: Date.now().toString(),
        name: newName,
        zone: selectedZone,
        type: deviceType,
        isOn: false,
        statusText: 'ปิดใช้งาน',
      };
      setDevices([...devices, newItem]);
    }
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
            <Text style={styles.pageTitle}>จัดการอุปกรณ์ฮาร์ดแวร์</Text>
            <Text style={styles.pageSub}>ควบคุมรีเลย์และเชื่อมต่อเซนเซอร์รายโซน</Text>
          </View>
          <TouchableOpacity style={styles.addButton} onPress={openAddModal}>
            <Ionicons name="add" size={18} color="#FFF" />
            <Text style={styles.addButtonText}>เพิ่มอุปกรณ์</Text>
          </TouchableOpacity>
        </View>

        {devices.map(device => (
          <View key={device.id} style={styles.deviceCard}>
            <View style={styles.deviceInfo}>
              <View style={[styles.iconBox, { backgroundColor: device.isOn ? '#ECFDF5' : '#F1F5F9' }]}>
                <Ionicons name={device.isOn ? "flash" : "flash-off"} size={20} color={device.isOn ? "#059669" : "#94A3B8"} />
              </View>
              <View style={{ flex: 1, marginHorizontal: 10 }}>
                <Text style={styles.deviceName}>{device.name}</Text>
                <Text style={styles.deviceZone}>📍 {device.zone} • {device.type}</Text>
                <Text style={[styles.deviceStatus, { color: device.isOn ? '#059669' : '#64748B' }]}>{device.statusText}</Text>
              </View>
              <Switch
                value={device.isOn}
                onValueChange={() => toggleDevice(device.id)}
                trackColor={{ false: '#CBD5E1', true: '#A7F3D0' }}
                thumbColor={device.isOn ? '#059669' : '#F8FAFC'}
              />
              <TouchableOpacity onPress={() => openEditModal(device)} style={styles.editBtn}>
                <Ionicons name="create-outline" size={18} color="#059669" />
              </TouchableOpacity>
              <TouchableOpacity onPress={() => deleteDevice(device.id)} style={styles.deleteBtn}>
                <Ionicons name="trash-outline" size={18} color="#DC2626" />
              </TouchableOpacity>
            </View>
          </View>
        ))}
      </ScrollView>

      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>{editingId ? '✏️ แก้ไขข้อมูลอุปกรณ์' : '➕ เพิ่มอุปกรณ์รีเลย์ / เซนเซอร์ใหม่'}</Text>
            
            <Text style={styles.label}>ชื่ออุปกรณ์</Text>
            <TextInput style={styles.input} placeholder="เช่น ปั๊มน้ำแปลงผัก Zone B" placeholderTextColor="#94A3B8" value={newName} onChangeText={setNewName} />

            <Text style={styles.label}>เลือกโซน / พื้นที่</Text>
            <View style={styles.selectorRow}>
              {['แปลงเกษตรโซน A', 'โรงเรือนเพาะชำ'].map(z => (
                <TouchableOpacity key={z} style={[styles.selectBtn, selectedZone === z && styles.selectBtnActive]} onPress={() => setSelectedZone(z)}>
                  <Text style={[styles.selectTxt, selectedZone === z && styles.selectTxtActive]}>{z}</Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.label}>ประเภทฮาร์ดแวร์</Text>
            <View style={styles.selectorRow}>
              {['Relay ปั๊มน้ำ', 'ระบบพ่นหมอก', 'เซนเซอร์วัดดิน'].map(t => (
                <TouchableOpacity key={t} style={[styles.selectBtn, deviceType === t && styles.selectBtnActive]} onPress={() => setDeviceType(t)}>
                  <Text style={[styles.selectTxt, deviceType === t && styles.selectTxtActive]}>{t}</Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
                <Text style={styles.cancelText}>ยกเลิก</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.submitBtn} onPress={saveDevice}>
                <Text style={styles.submitText}>{editingId ? 'บันทึกการแก้ไข' : 'บันทึกอุปกรณ์'}</Text>
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
  editBtn: { marginLeft: 8, padding: 6 },
  deleteBtn: { marginLeft: 4, padding: 6 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#FFF', width: '100%', borderRadius: 20, padding: 20 },
  modalTitle: { fontSize: 16, fontWeight: 'bold', color: '#1E293B', marginBottom: 14 },
  label: { fontSize: 12, fontWeight: 'bold', color: '#475569', marginBottom: 6, marginTop: 8 },
  input: { borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 12, padding: 12, fontSize: 13, color: '#1E293B' },
  selectorRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  selectBtn: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, backgroundColor: '#F1F5F9', borderWidth: 1, borderColor: '#E2E8F0' },
  selectBtnActive: { backgroundColor: '#ECFDF5', borderColor: '#059669' },
  selectTxt: { fontSize: 11, color: '#64748B', fontWeight: '600' },
  selectTxtActive: { color: '#059669', fontWeight: 'bold' },
  modalActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, marginTop: 20 },
  cancelBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#F1F5F9' },
  cancelText: { color: '#64748B', fontWeight: 'bold', fontSize: 13 },
  submitBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#059669' },
  submitText: { color: '#FFF', fontWeight: 'bold', fontSize: 13 },
});
