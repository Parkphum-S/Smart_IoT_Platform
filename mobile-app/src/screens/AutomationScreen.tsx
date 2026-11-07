import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Switch, TouchableOpacity, TextInput, Modal } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface RuleItem {
  id: string;
  title: string;
  condition: string;
  action: string;
  isActive: boolean;
}

export default function AutomationScreen() {
  const [rules, setRules] = useState<RuleItem[]>([
    { id: '1', title: 'ควบคุมความชื้นโรงเรือน', condition: 'ความชื้นดิน < 40%', action: 'เปิดรีเลย์ปั๊มน้ำ (Zone A)', isActive: true },
    { id: '2', title: 'ลดอุณหภูมิแปลงเกษตร', condition: 'อุณหภูมิ > 33°C', action: 'เปิดระบบพ่นหมอก', isActive: false },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [title, setTitle] = useState('');
  const [condition, setCondition] = useState('');
  const [action, setAction] = useState('');

  const toggleRule = (id: string) => {
    setRules(rules.map(r => r.id === id ? { ...r, isActive: !r.isActive } : r));
  };

  const addRule = () => {
    if (!title.trim()) return;
    const newRule: RuleItem = {
      id: Date.now().toString(),
      title,
      condition: condition || 'กำหนดเอง',
      action: action || 'สั่งการรีเลย์',
      isActive: true,
    };
    setRules([...rules, newRule]);
    setTitle('');
    setCondition('');
    setAction('');
    setModalVisible(false);
  };

  const deleteRule = (id: string) => {
    setRules(rules.filter(r => r.id !== id));
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.contentContainer}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.pageTitle}>ระบบอัตโนมัติ (Automation)</Text>
            <Text style={styles.pageSub}>ตั้งค่าเงื่อนไขควบคุมฮาร์ดแวร์อัจฉริยะ</Text>
          </View>
          <TouchableOpacity style={styles.addButton} onPress={() => setModalVisible(true)}>
            <Ionicons name="add" size={20} color="#FFF" />
            <Text style={styles.addButtonText}>เพิ่มกฎ</Text>
          </TouchableOpacity>
        </View>

        {rules.map(rule => (
          <View key={rule.id} style={styles.card}>
            <View style={styles.row}>
              <View style={[styles.iconBox, { backgroundColor: rule.isActive ? '#ECFDF5' : '#F1F5F9' }]}>
                <Ionicons name="git-branch" size={20} color={rule.isActive ? "#059669" : "#94A3B8"} />
              </View>
              <View style={{ flex: 1, marginHorizontal: 12 }}>
                <Text style={styles.ruleTitle}>{rule.title}</Text>
                <Text style={styles.ruleDesc}>เงื่อนไข: {rule.condition}</Text>
                <Text style={styles.ruleAction}>การทำงาน: {rule.action}</Text>
              </View>
              <Switch
                value={rule.isActive}
                onValueChange={() => toggleRule(rule.id)}
                trackColor={{ false: '#CBD5E1', true: '#A7F3D0' }}
                thumbColor={rule.isActive ? '#059669' : '#F8FAFC'}
              />
              <TouchableOpacity onPress={() => deleteRule(rule.id)} style={styles.deleteBtn}>
                <Ionicons name="trash-outline" size={18} color="#DC2626" />
              </TouchableOpacity>
            </View>
          </View>
        ))}
      </ScrollView>

      {/* Modal เพิ่มกฎ */}
      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>⚡ สร้างเงื่อนไขอัตโนมัติใหม่</Text>
            <TextInput style={styles.input} placeholder="ชื่อกฎ (เช่น รดน้ำอัตโนมัติยามเช้า)" placeholderTextColor="#94A3B8" value={title} onChangeText={setTitle} />
            <TextInput style={styles.input} placeholder="เงื่อนไข (เช่น ความชื้น < 50%)" placeholderTextColor="#94A3B8" value={condition} onChangeText={setCondition} />
            <TextInput style={styles.input} placeholder="การทำงาน (เช่น เปิดปั๊มน้ำ Zone A)" placeholderTextColor="#94A3B8" value={action} onChangeText={setAction} />
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
                <Text style={styles.cancelText}>ยกเลิก</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.submitBtn} onPress={addRule}>
                <Text style={styles.submitText}>บันทึกกฎ</Text>
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
  iconBox: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  ruleTitle: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  ruleDesc: { fontSize: 11, color: '#475569', marginTop: 2 },
  ruleAction: { fontSize: 11, fontWeight: '600', color: '#059669', marginTop: 2 },
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
