import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Modal } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function HomeScreen() {
  const [selectedZone, setSelectedZone] = useState('ZoneA');
  const [zoneData, setZoneData] = useState<any>({
    ZoneA: {
      name: 'แปลงเกษตรโซน A',
      desc: 'พื้นที่: ฟาร์มตัวอย่างหลัก',
      temp: '-- °C',
      humidity: '-- %',
      vpd: '1.56 kPa',
      soilMoisture: '-- %',
      npk: 'N: 40, P: 25, K: 60 mg/kg',
      ph: '6.5',
      relayStatus: 'เปิดใช้งาน (ปั๊มน้ำหลัก)',
    }
  });

  const [modalVisible, setModalVisible] = useState(false);
  const [nitrogen, setNitrogen] = useState('40');
  const [phosphorus, setPhosphorus] = useState('25');
  const [potassium, setPotassium] = useState('60');
  const [phVal, setPhVal] = useState('6.5');

  // ดึงข้อมูลสดจาก Backend ทุกๆ 3 วินาที
  useEffect(() => {
    const fetchSensors = async () => {
      try {
        const response = await fetch('http://192.168.1.98:5000/api/sensors'); // เปลี่ยนเป็น IP เซิร์ฟเวอร์จริง
        const data = await response.json();
        if (data && data.ZoneA) {
          setZoneData((prev: any) => ({
            ...prev,
            ZoneA: {
              ...prev.ZoneA,
              temp: data.ZoneA.temp,
              humidity: data.ZoneA.humidity,
              soilMoisture: data.ZoneA.soilMoisture,
            }
          }));
        }
      } catch (error) {
        console.log('Error fetching live sensors:', error);
      }
    };

    fetchSensors();
    const interval = setInterval(fetchSensors, 3000);
    return () => clearInterval(interval);
  }, []);

  const current = zoneData[selectedZone] || zoneData.ZoneA;

  const saveNpckAndPh = async () => {
    const newNpk = `N: ${nitrogen}, P: ${phosphorus}, K: ${potassium} mg/kg`;
    try {
      await fetch('http://192.168.1.98:5000/api/sensors/soil', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone: selectedZone, npk: newNpk, ph: phVal })
      });
      
      setZoneData({
        ...zoneData,
        [selectedZone]: {
          ...current,
          npk: newNpk,
          ph: phVal,
        }
      });
    } catch (e) {
      console.log('Failed to save soil data:', e);
    }
    setModalVisible(false);
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.contentContainer}>
        <View style={styles.weatherCard}>
          <View style={styles.rowBetween}>
            <Text style={styles.weatherBadge}>Live MQTT / API</Text>
            <Text style={styles.locationText}>📍 นนทบุรี, ประเทศไทย</Text>
          </View>
          <Text style={styles.tempText}>31°C • เชื่อมต่อเซนเซอร์สด</Text>
          <Text style={styles.weatherSub}> ESP32 Hardware & Cloud Synchronized</Text>
        </View>

        <View style={styles.rowBetween}>
          <Text style={styles.sectionTitle}>รายงานสถานะเซนเซอร์สด</Text>
          <TouchableOpacity style={styles.editNpGBtn} onPress={() => setModalVisible(true)}>
            <Ionicons name="create-outline" size={14} color="#059669" />
            <Text style={styles.editNpGText}>กรอก/แก้ไข NPK & pH</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.sensorCard}>
          <Text style={styles.zoneCategory}>โซนพืชสวน (Real-time)</Text>
          <Text style={styles.zoneTitle}>{current.name}</Text>
          <Text style={styles.zoneDesc}>{current.desc}</Text>

          <View style={styles.sensorGrid}>
            <View style={styles.sensorBox}>
              <Ionicons name="thermometer-outline" size={18} color="#EF4444" />
              <Text style={styles.sLabel}>อุณหภูมิ (ESP32)</Text>
              <Text style={styles.sVal}>{current.temp}</Text>
            </View>
            <View style={styles.sensorBox}>
              <Ionicons name="water-outline" size={18} color="#3B82F6" />
              <Text style={styles.sLabel}>ความชื้นอากาศ</Text>
              <Text style={styles.sVal}>{current.humidity}</Text>
            </View>
            <View style={styles.sensorBox}>
              <Ionicons name="ellipse-outline" size={18} color="#8B5CF6" />
              <Text style={styles.sLabel}>ความชื้นดิน</Text>
              <Text style={styles.sVal}>{current.soilMoisture}</Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="leaf-outline" size={16} color="#059669" />
            <Text style={styles.infoText}>ค่า NPK (ดิน): {current.npk}</Text>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="flask-outline" size={16} color="#059669" />
            <Text style={styles.infoText}>ค่า pH ดิน: {current.ph}</Text>
          </View>
        </View>
      </ScrollView>

      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>🧪 บันทึก/อัปเดตค่า NPK และ pH</Text>
            <TextInput style={styles.input} placeholder="ไนโตรเจน (N)" keyboardType="numeric" value={nitrogen} onChangeText={setNitrogen} />
            <TextInput style={styles.input} placeholder="ฟอสฟอรัส (P)" keyboardType="numeric" value={phosphorus} onChangeText={setPhosphorus} />
            <TextInput style={styles.input} placeholder="โพแทสเซียม (K)" keyboardType="numeric" value={potassium} onChangeText={setPotassium} />
            <TextInput style={styles.input} placeholder="ค่า pH" keyboardType="numeric" value={phVal} onChangeText={setPhVal} />
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}><Text style={styles.cancelText}>ยกเลิก</Text></TouchableOpacity>
              <TouchableOpacity style={styles.submitBtn} onPress={saveNpckAndPh}><Text style={styles.submitText}>บันทึก</Text></TouchableOpacity>
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
  weatherCard: { backgroundColor: '#059669', borderRadius: 20, padding: 16, marginBottom: 16 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  weatherBadge: { backgroundColor: 'rgba(255,255,255,0.2)', color: '#FFF', fontSize: 10, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6, fontWeight: 'bold' },
  locationText: { color: '#FFF', fontSize: 12, fontWeight: '600' },
  tempText: { color: '#FFF', fontSize: 20, fontWeight: '900', marginBottom: 2 },
  weatherSub: { color: '#E2E8F0', fontSize: 11 },
  sectionTitle: { fontSize: 15, fontWeight: 'bold', color: '#1E293B' },
  editNpGBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ECFDF5', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 10, borderWidth: 1, borderColor: '#A7F3D0', gap: 4 },
  editNpGText: { fontSize: 11, fontWeight: 'bold', color: '#059669' },
  sensorCard: { backgroundColor: '#FFF', borderRadius: 20, padding: 16, borderWidth: 1, borderColor: '#F1F5F9', marginTop: 12 },
  zoneCategory: { fontSize: 11, color: '#64748B', fontWeight: 'bold' },
  zoneTitle: { fontSize: 18, fontWeight: '900', color: '#1E293B', marginVertical: 2 },
  zoneDesc: { fontSize: 11, color: '#94A3B8', marginBottom: 14 },
  sensorGrid: { flexDirection: 'row', gap: 8, marginBottom: 14 },
  sensorBox: { flex: 1, backgroundColor: '#F8FAFC', borderRadius: 12, padding: 10, alignItems: 'center', borderWidth: 1, borderColor: '#F1F5F9' },
  sLabel: { fontSize: 9, color: '#64748B', marginTop: 4, textAlign: 'center' },
  sVal: { fontSize: 12, fontWeight: 'bold', color: '#1E293B', marginTop: 2 },
  infoRow: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#F8FAFC', padding: 10, borderRadius: 10, marginBottom: 8, borderWidth: 1, borderColor: '#F1F5F9' },
  infoText: { fontSize: 12, color: '#334155', fontWeight: '600' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#FFF', width: '100%', borderRadius: 20, padding: 20 },
  modalTitle: { fontSize: 15, fontWeight: 'bold', color: '#1E293B', marginBottom: 14 },
  input: { borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 12, padding: 10, fontSize: 12, color: '#1E293B', marginBottom: 10 },
  modalActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, marginTop: 10 },
  cancelBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#F1F5F9' },
  cancelText: { color: '#64748B', fontWeight: 'bold', fontSize: 12 },
  submitBtn: { paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, backgroundColor: '#059669' },
  submitText: { color: '#FFF', fontWeight: 'bold', fontSize: 12 },
});
