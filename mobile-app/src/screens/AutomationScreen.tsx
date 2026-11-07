import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Switch, TouchableOpacity, TextInput, Modal } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface RuleItem {
  id: string;
  title: string;
  sensorType: string;
  operator: string;
  threshold: string;
  actionDevice: string;
  zone: string;
  isActive: boolean;
}

export default function AutomationScreen() {
  const [rules, setRules] = useState<RuleItem[]>([
    { id: '1', title: 'ควบคุมความชื้นโรงเรือน', sensorType: 'ความชื้นดิน (%)', operator: 'น้อยกว่า (<)', threshold: '40', actionDevice: 'รีเลย์ปั๊มน้ำหลัก', zone: 'แปลงเกษตรโซน A', isActive: true },
    { id: '2', title: 'ระบายความร้อนแปลง', sensorType: 'อุณหภูมิ (°C)', operator: 'มากกว่า (>)', threshold: '33', actionDevice: 'ระบบพ่นหมอกความชื้น', zone: 'โรงเรือนเพาะชำ', isActive: false },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [sensorType, setSensorType] = useState('ความชื้นดิน (%)');
  const [operator, setOperator] = useState('น้อยกว่า (<)');
  const [threshold, setThreshold] = useState('');
  const [actionDevice, setActionDevice] = useState('รีเลย์ปั๊มน้ำหลัก');
  const [zone, setZone] = useState('แปลงเกษตรโซน A');

  const toggleRule = (id: string) => {
    setRules(rules.map(r => r.id === id ? { ...r, isActive: !r.isActive } : r));
  };

  const openAddModal = () => {
    setEditingId(null);
    setTitle('');
    setSensorType('ความชื้นดิน (%)');
    setOperator('น้อยกว่า (<)');
    setThreshold('');
    setActionDevice('รีเลย์ปั๊มน้ำหลัก');
    setZone('แปลงเกษตรโซน A');
    setModalVisible(true);
  };

  const openEditModal = (rule: RuleItem) => {
    setEditingId(rule.id);
    setTitle(rule.title);
    setSensorType(rule.sensorType);
    setOperator(rule.operator);
    setThreshold(rule.threshold);
    setActionDevice(rule.actionDevice);
    setZone(rule.zone);
    setModalVisible(true);
  };

  const saveRule = () => {
    if (!title.trim() || !threshold.trim()) return;
    if (editingId) {
      setRules(rules.map(r => r.id === editingId ? {
        ...r,
        title,
        sensorType,
        operator,
        threshold,
        actionDevice,
        zone,
      } : r));
    } else {
      const newRule: RuleItem = {
        id: Date.now().toString(),
        title,
        sensorType,
        operator,
        threshold,
        actionDevice,
        zone,
        isActive: true,
      };
      setRules([...rules, newRule]);
    }
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
            <Text style={styles.pageTitle}>ระบบอัตโนมัติ (Automation Rules)</Text>
            <Text style={styles.pageSub}>ตั้งค่าเงื่อนไขควบคุมฮาร์ดแวร์อัจฉริยะตามหน้าเว็บ</Text>
          </View>
          <TouchableOpacity style={styles.addButton} onPress={openAddModal}>
            <Ionicons name="add" size={18} color="#FFF" />
            <Text style={styles.addButtonText}>เพิ่มกฎเงื่อนไข</Text>
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
                <Text style={styles.ruleDesc}>📍 โซน: {rule.zone}</Text>
                <Text style={styles.ruleCondition}>เงื่อนไข: {rule.sensorType} {rule.operator} {rule.threshold}</Text>
                <Text style={styles.ruleAction}>⚡ สั่งการ: {rule.actionDevice}</Text>
              </View>
              <Switch
                value={rule.isActive}
                onValueChange={() => toggleRule(rule.id)}
                trackColor={{ false: '#CBD5E1', true: '#A7F3D0' }}
                thumbColor={rule.isActive ? '#059669' : '#F8FAFC'}
              />
              <TouchableOpacity onPress={() => openEditModal(rule)} style={styles.editBtn}>
                <Ionicons name="create-outline" size={18} color="#059669" />
              </TouchableOpacity>
              <TouchableOpacity onPress={() => deleteRule(rule.id)} style={styles.deleteBtn}>
                <Ionicons name="trash-outline" size={18} color="#DC2626" />
              </TouchableOpacity>
            </View>
          </View>
        ))}
      </ScrollView>

      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>{editingId ? '✏️ แก้ไขเงื่อนไขอัตโนมัติ' : '⚡ สร้างเงื่อนไขอัตโนมัติ (Rule Engine)'}</Text>
            
            <Text style={styles.label}>ชื่อเงื่อนไข / กฎการทำงาน</Text>
            <TextInput style={styles.input} placeholder="เช่น รดน้ำอัตโนมัติยามเช้า" placeholderTextColor="#94A3B8" value={title} onChangeText={setTitle} />

            <Text style={styles.label}>เลือกโซนพื้นที่</Text>
            <View style={styles.selectorRow}>
              {['แปลงเกษตรโซน A', 'โรงเรือนเพาะชำ'].map(z => (
                <TouchableOpacity key={z} style={[styles.selectBtn, zone === z && styles.selectBtnActive]} onPress={() => setZone(z)}>
                  <Text style={[styles.selectTxt, zone === z && styles.selectTxtActive]}>{z}</Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.label}>ประเภทเซนเซอร์ตัวจับ</Text>
            <View style={styles.selectorRow}>
              {['ความชื้นดิน (%)', 'อุณหภูมิ (°C)', 'ค่า pH', 'ค่า VPD'].map(s => (
                <TouchableOpacity key={s} style={[styles.selectBtn, sensorType === s && styles.selectBtnActive]} onPress={() => setSensorType(s)}>
                  <Text style={[styles.selectTxt, sensorType === s && styles.selectTxtActive]}>{s}</Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.label}>เงื่อนไขเปรียบเทียบ & ค่า Threshold</Text>
            <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
              {['น้อยกว่า (<)', 'มากกว่า (>)'].map(op => (
                <TouchableOpacity key={op} style={[styles.selectBtn, operator === op && styles.selectBtnActive]} onPress={() => setOperator(op)}>
                  <Text style={[styles.selectTxt, operator === op && styles.selectTxtActive]}>{op}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <TextInput style={styles.input} placeholder="ระบุตัวเลขค่าเกณฑ์ (เช่น 40 หรือ 33)" placeholderTextColor="#94A3B8" keyboardType="numeric" value={threshold} onChangeText={setThreshold} />

            <Text style={styles.label}>อุปกรณ์รีเลย์ปลายทางที่จะสั่งการ</Text>
            <View style={styles.selectorRow}>
              {['รีเลย์ปั๊มน้ำหลัก', 'ระบบพ่นหมอกความชื้น', 'ไฟ LED ปลูกพืช'].map(d => (
                <TouchableOpacity key={d} style={[styles.selectBtn, actionDevice === d && styles.selectBtnActive]} onPress={() => setActionDevice(d)}>
                  <Text style={[styles.selectTxt, actionDevice === d && styles.selectTxtActive]}>{d}</Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
                <Text style={styles.cancelText}>ยกเลิก</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.submitBtn} onPress={saveRule}>
                <Text style={styles.submitText}>{editingId ? 'บันทึกการแก้ไข' : 'บันทึกเงื่อนไข'}</Text>
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
  ruleDesc: { fontSize: 11, color: '#64748B', marginTop: 2 },
  ruleCondition: { fontSize: 11, color: '#334155', fontWeight: '600', marginTop: 2 },
  ruleAction: { fontSize: 11, fontWeight: 'bold', color: '#059669', marginTop: 2 },
  editBtn: { marginLeft: 8, padding: 6 },
  deleteBtn: { marginLeft: 4, padding: 6 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#FFF', width: '100%', borderRadius: 20, padding: 20 },
  modalTitle: { fontSize: 15, fontWeight: 'bold', color: '#1E293B', marginBottom: 14 },
  label: { fontSize: 11, fontWeight: 'bold', color: '#475569', marginBottom: 6, marginTop: 8 },
  input: { borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 12, padding: 10, fontSize: 12, color: '#1E293B' },
  selectorRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  selectBtn: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, backgroundColor: '#F1F5F9', borderWidth: 1, borderColor: '#E2E8F0' },
  selectBtnActive: { backgroundColor: '#ECFDF5', borderColor: '#059669' },
  selectTxt: { fontSize: 11, color: '#64748B', fontWeight: '600' },
  selectTxtActive: { color: '#059669', fontWeight: 'bold' },
  modalActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, marginTop: 18 },
  cancelBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#F1F5F9' },
  cancelText: { color: '#64748B', fontWeight: 'bold', fontSize: 12 },
  submitBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#059669' },
  submitText: { color: '#FFF', fontWeight: 'bold', fontSize: 12 },
});
