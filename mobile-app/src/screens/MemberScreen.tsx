import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Modal } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface MemberItem {
  id: string;
  email: string;
  role: 'Owner' | 'Manager' | 'Viewer';
  status: string;
}

export default function MemberScreen() {
  const [members, setMembers] = useState<MemberItem[]>([
    { id: '1', email: 'parkphum@smartiot.local', role: 'Owner', status: 'ใช้งานอยู่' },
    { id: '2', email: 'somchai.farm@smartiot.local', role: 'Manager', status: 'ใช้งานอยู่' },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'Owner' | 'Manager' | 'Viewer'>('Manager');

  const inviteMember = () => {
    if (!email.trim()) return;
    setMembers([...members, { id: Date.now().toString(), email, role, status: 'รอตอบรับ' }]);
    setEmail('');
    setModalVisible(false);
  };

  const removeMember = (id: string) => {
    setMembers(members.filter(m => m.id !== id));
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.contentContainer}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.pageTitle}>จัดการสมาชิก (RBAC)</Text>
            <Text style={styles.pageSub}>เชิญผู้ใช้งานและกำหนดสิทธิ์ใน Workspace</Text>
          </View>
          <TouchableOpacity style={styles.addButton} onPress={() => setModalVisible(true)}>
            <Ionicons name="person-add" size={16} color="#FFF" />
            <Text style={styles.addButtonText}>เชิญสมาชิก</Text>
          </TouchableOpacity>
        </View>

        {members.map(member => (
          <View key={member.id} style={styles.card}>
            <View style={styles.row}>
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>{member.email.charAt(0).toUpperCase()}</Text>
              </View>
              <View style={{ flex: 1, marginHorizontal: 12 }}>
                <Text style={styles.email}>{member.email}</Text>
                <Text style={styles.meta}>สิทธิ์: {member.role} • {member.status}</Text>
              </View>
              {member.role !== 'Owner' && (
                <TouchableOpacity onPress={() => removeMember(member.id)} style={styles.deleteBtn}>
                  <Ionicons name="trash-outline" size={18} color="#DC2626" />
                </TouchableOpacity>
              )}
            </View>
          </View>
        ))}
      </ScrollView>

      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>👥 เชิญสมาชิกเข้า Workspace</Text>
            <Text style={styles.label}>อีเมลผู้ใช้งาน</Text>
            <TextInput style={styles.input} placeholder="example@smartiot.local" placeholderTextColor="#94A3B8" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />
            <Text style={styles.label}>กำหนดสิทธิ์ (Role)</Text>
            <View style={styles.selectorRow}>
              {(['Manager', 'Viewer'] as const).map(r => (
                <TouchableOpacity key={r} style={[styles.selectBtn, role === r && styles.selectBtnActive]} onPress={() => setRole(r)}>
                  <Text style={[styles.selectTxt, role === r && styles.selectTxtActive]}>{r}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
                <Text style={styles.cancelText}>ยกเลิก</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.submitBtn} onPress={inviteMember}>
                <Text style={styles.submitText}>ส่งคำเชิญ</Text>
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
  addButton: { flexDirection: 'row', backgroundColor: '#059669', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 12, alignItems: 'center', gap: 6 },
  addButtonText: { color: '#FFF', fontSize: 12, fontWeight: 'bold' },
  card: { backgroundColor: '#FFF', borderRadius: 16, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: '#F1F5F9' },
  row: { flexDirection: 'row', alignItems: 'center' },
  avatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#D1FAE5', alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: 16, fontWeight: 'bold', color: '#059669' },
  email: { fontSize: 13, fontWeight: 'bold', color: '#1E293B' },
  meta: { fontSize: 11, color: '#64748B', marginTop: 2 },
  deleteBtn: { padding: 6 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#FFF', width: '100%', borderRadius: 20, padding: 20 },
  modalTitle: { fontSize: 16, fontWeight: 'bold', color: '#1E293B', marginBottom: 14 },
  label: { fontSize: 11, fontWeight: 'bold', color: '#475569', marginBottom: 6, marginTop: 8 },
  input: { borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 12, padding: 10, fontSize: 13, color: '#1E293B' },
  selectorRow: { flexDirection: 'row', gap: 8 },
  selectBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8, backgroundColor: '#F1F5F9', borderWidth: 1, borderColor: '#E2E8F0' },
  selectBtnActive: { backgroundColor: '#ECFDF5', borderColor: '#059669' },
  selectTxt: { fontSize: 12, color: '#64748B', fontWeight: '600' },
  selectTxtActive: { color: '#059669', fontWeight: 'bold' },
  modalActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, marginTop: 18 },
  cancelBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#F1F5F9' },
  cancelText: { color: '#64748B', fontWeight: 'bold', fontSize: 12 },
  submitBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#059669' },
  submitText: { color: '#FFF', fontWeight: 'bold', fontSize: 12 },
});
