import React, { useState } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, TextInput, Modal } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function ProfileScreen({ navigation }: any) {
  const [userName, setUserName] = useState('Parkphum (Owner)');
  const [userEmail, setUserEmail] = useState('parkphum@smartiot.local');
  const [modalVisible, setModalVisible] = useState(false);
  const [tempName, setTempName] = useState(userName);
  const [tempEmail, setTempEmail] = useState(userEmail);

  const saveProfile = () => {
    setUserName(tempName);
    setUserEmail(tempEmail);
    setModalVisible(false);
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>โปรไฟล์และการตั้งค่า</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.userCard}>
          <View style={styles.avatarBox}>
            <Text style={styles.avatarText}>{userName.charAt(0)}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.userName}>{userName}</Text>
            <Text style={styles.userEmail}>{userEmail}</Text>
          </View>
          <TouchableOpacity onPress={() => setModalVisible(true)} style={styles.editBtn}>
            <Ionicons name="create-outline" size={18} color="#059669" />
          </TouchableOpacity>
        </View>

        <View style={styles.menuGroup}>
          <TouchableOpacity style={styles.menuItem} onPress={() => alert('เปิดใช้งานแจ้งเตือนผ่าน Mobile Push เรียบร้อย')}>
            <Ionicons name="notifications-outline" size={20} color="#059669" style={styles.menuIcon} />
            <Text style={styles.menuText}>การตั้งค่าการแจ้งเตือน Push</Text>
            <Ionicons name="chevron-forward" size={16} color="#94A3B8"/>
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem} onPress={() => alert('ระบบความปลอดภัยสิทธิ์ RBAC เปิดใช้งานอยู่')}>
            <Ionicons name="shield-outline" size={20} color="#059669" style={styles.menuIcon} />
            <Text style={styles.menuText}>ความปลอดภัยและสิทธิ์การใช้งาน (RBAC)</Text>
            <Ionicons name="chevron-forward" size={16} color="#94A3B8"/>
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.logoutButton} onPress={() => alert('ออกจากระบบเรียบร้อย')}>
          <Ionicons name="log-out-outline" size={18} color="#DC2626" style={{ marginRight: 8 }} />
          <Text style={styles.logoutText}>ออกจากระบบ</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* Modal แก้ไขโปรไฟล์ */}
      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>✏️ แก้ไขข้อมูลโปรไฟล์</Text>
            <TextInput style={styles.input} placeholder="ชื่อ-นามสกุล" placeholderTextColor="#94A3B8" value={tempName} onChangeText={setTempName} />
            <TextInput style={styles.input} placeholder="อีเมลใช้งาน" placeholderTextColor="#94A3B8" value={tempEmail} onChangeText={setTempEmail} />
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
                <Text style={styles.cancelText}>ยกเลิก</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.submitBtn} onPress={saveProfile}>
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
  header: { padding: 16, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  headerTitle: { fontSize: 18, fontWeight: 'bold', color: '#0F172A' },
  content: { padding: 16 },
  userCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFFFFF', padding: 16, borderRadius: 20, marginBottom: 16, borderWidth: 1, borderColor: '#F1F5F9' },
  avatarBox: { width: 48, height: 48, borderRadius: 24, backgroundColor: '#D1FAE5', justifyContent: 'center', alignItems: 'center', marginRight: 14 },
  avatarText: { fontSize: 18, fontWeight: 'bold', color: '#059669' },
  userName: { fontSize: 15, fontWeight: 'bold', color: '#1E293B' },
  userEmail: { fontSize: 12, color: '#64748B', marginTop: 2 },
  editBtn: { padding: 8, backgroundColor: '#ECFDF5', borderRadius: 10 },
  menuGroup: { backgroundColor: '#FFFFFF', borderRadius: 20, paddingHorizontal: 16, marginBottom: 16, borderWidth: 1, borderColor: '#F1F5F9' },
  menuItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  menuIcon: { marginRight: 14 },
  menuText: { flex: 1, fontSize: 14, color: '#334155', fontWeight: '500' },
  logoutButton: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', backgroundColor: '#FEF2F2', padding: 16, borderRadius: 16, borderWidth: 1, borderColor: '#FEE2E2' },
  logoutText: { color: '#DC2626', fontWeight: 'bold', fontSize: 14 },
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
