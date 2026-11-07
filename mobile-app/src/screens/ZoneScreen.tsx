import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Modal } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface ZoneItem {
  id: string;
  name: string;
  crop: string;
  area: string;
  npk: string;
  ph: string;
  status: string;
}

export default function ZoneScreen() {
  const [zones, setZones] = useState<ZoneItem[]>([
    { id: '1', name: 'แปลงเกษตรโซน A', crop: 'เมล่อนญี่ปุ่น', area: '200 ตร.ม.', npk: 'N:40, P:25, K:60', ph: '6.5', status: 'ปกติ' },
    { id: '2', name: 'โรงเรือนเพาะชำ', crop: 'ผักสลัดไฮโดรโปนิกส์', area: '120 ตร.ม.', npk: 'N:50, P:30, K:70', ph: '6.8', status: 'ปกติ' },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [crop, setCrop] = useState('');
  const [area, setArea] = useState('');
  const [npk, setNpk] = useState('N:40, P:25, K:60');
  const [ph, setPh] = useState('6.5');

  const openAddModal = () => {
    setEditingId(null);
    setName('');
    setCrop('');
    setArea('');
    setNpk('N:40, P:25, K:60');
    setPh('6.5');
    setModalVisible(true);
  };

  const openEditModal = (zone: ZoneItem) => {
    setEditingId(zone.id);
    setName(zone.name);
    setCrop(zone.crop);
    setArea(zone.area);
    setNpk(zone.npk);
    setPh(zone.ph);
    setModalVisible(true);
  };

  const saveZone = () => {
    if (!name.trim()) return;
    if (editingId) {
      setZones(zones.map(z => z.id === editingId ? {
        ...z,
        name,
        crop: crop || 'พืชผักทั่วไป',
        area: area || '100 ตร.ม.',
        npk,
        ph,
      } : z));
    } else {
      const newZone: ZoneItem = {
        id: Date.now().toString(),
        name,
        crop: crop || 'พืชผักทั่วไป',
        area: area || '100 ตร.ม.',
        npk,
        ph,
        status: 'พร้อมใช้งาน',
      };
      setZones([...zones, newZone]);
    }
    setModalVisible(false);
  };

  const deleteZone = (id: string) => {
    setZones(zones.filter(z => z.id !== id));
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.contentContainer}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.pageTitle}>จัดการโซนแปลงเกษตร</Text>
            <Text style={styles.pageSub}>เพิ่ม แก้ไข และกำหนดค่า NPK & pH ประจำโซน</Text>
          </View>
          <TouchableOpacity style={styles.addButton} onPress={openAddModal}>
            <Ionicons name="add" size={18} color="#FFF" />
            <Text style={styles.addButtonText}>เพิ่มโซน</Text>
          </TouchableOpacity>
        </View>

        {zones.map(zone => (
          <View key={zone.id} style={styles.card}>
            <View style={styles.row}>
              <View style={styles.iconBox}>
                <Ionicons name="map" size={20} color="#059669" />
              </View>
              <View style={{ flex: 1, marginHorizontal: 12 }}>
                <Text style={styles.zoneName}>{zone.name}</Text>
                <Text style={styles.zoneMeta}>🌱 พืช: {zone.crop} • 📐 {zone.area}</Text>
                <Text style={styles.zoneSoil}>🧪 NPK: {zone.npk} | pH: {zone.ph}</Text>
              </View>
              <TouchableOpacity onPress={() => openEditModal(zone)} style={styles.editBtn}>
                <Ionicons name="create-outline" size={18} color="#059669" />
              </TouchableOpacity>
              <TouchableOpacity onPress={() => deleteZone(zone.id)} style={styles.deleteBtn}>
                <Ionicons name="trash-outline" size={18} color="#DC2626" />
              </TouchableOpacity>
            </View>
          </View>
        ))}
      </ScrollView>

      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>{editingId ? '✏️ แก้ไขข้อมูลโซนแปลงเกษตร' : '🗺️ เพิ่มโซนแปลงเกษตรใหม่'}</Text>
            
            <Text style={styles.label}>ชื่อโซน / โรงเรือน</Text>
            <TextInput style={styles.input} placeholder="เช่น แปลงเกษตรโซน B" placeholderTextColor="#94A3B8" value={name} onChangeText={setName} />

            <Text style={styles.label}>ชนิดพืชที่ปลูก</Text>
            <TextInput style={styles.input} placeholder="เช่น มะเขือเทศราชินี" placeholderTextColor="#94A3B8" value={crop} onChangeText={setCrop} />

            <Text style={styles.label}>ขนาดพื้นที่</Text>
            <TextInput style={styles.input} placeholder="เช่น 150 ตร.ม." placeholderTextColor="#94A3B8" value={area} onChangeText={setArea} />

            <Text style={styles.label}>ค่า NPK เบื้องต้น</Text>
            <TextInput style={styles.input} placeholder="เช่น N:40, P:25, K:60" placeholderTextColor="#94A3B8" value={npk} onChangeText={setNpk} />

            <Text style={styles.label}>ค่า pH ดิน</Text>
            <TextInput style={styles.input} placeholder="เช่น 6.5" placeholderTextColor="#94A3B8" value={ph} onChangeText={setPh} keyboardType="numeric" />

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
                <Text style={styles.cancelText}>ยกเลิก</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.submitBtn} onPress={saveZone}>
                <Text style={styles.submitText}>{editingId ? 'บันทึกการแก้ไข' : 'บันทึกโซน'}</Text>
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
  card: { backgroundColor: '#FFF', borderRadius: 16, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: '#F1F5F9' },
  row: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 42, height: 42, borderRadius: 12, backgroundColor: '#ECFDF5', alignItems: 'center', justifyContent: 'center' },
  zoneName: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  zoneMeta: { fontSize: 11, color: '#475569', marginTop: 2 },
  zoneSoil: { fontSize: 11, color: '#059669', fontWeight: 'bold', marginTop: 2 },
  editBtn: { padding: 6, marginRight: 4 },
  deleteBtn: { padding: 6 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#FFF', width: '100%', borderRadius: 20, padding: 20 },
  modalTitle: { fontSize: 15, fontWeight: 'bold', color: '#1E293B', marginBottom: 14 },
  label: { fontSize: 11, fontWeight: 'bold', color: '#475569', marginBottom: 4, marginTop: 6 },
  input: { borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 12, padding: 10, fontSize: 12, color: '#1E293B' },
  modalActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, marginTop: 16 },
  cancelBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#F1F5F9' },
  cancelText: { color: '#64748B', fontWeight: 'bold', fontSize: 12 },
  submitBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#059669' },
  submitText: { color: '#FFF', fontWeight: 'bold', fontSize: 12 },
});
