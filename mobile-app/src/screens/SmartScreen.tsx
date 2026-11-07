import React, { useState } from 'react';
import { StyleSheet, Text, View, ScrollView, Switch, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function SmartScreen() {
  const [scenes] = useState([
    { id: 'sc-1', name: 'โหมดรดน้ำเร่งด่วน', desc: 'เปิดปั๊มน้ำหลักและวาล์วโซน A พร้อมกัน 15 นาที', active: true },
    { id: 'sc-2', name: 'โหมดกลางคืน (ประหยัดพลังงาน)', desc: 'ปิดระบบพ่นหมอกและหรี่ไฟโรงเรือน', active: false },
  ]);

  const [automations] = useState([
    { id: 'auto-1', name: 'รดน้ำอัตโนมัติ (ความชื้นดิน < 30%)', condition: 'Soil Moisture < 30%', enabled: true },
    { id: 'auto-2', name: 'พ่นหมอกลดความร้อน', condition: 'Temperature > 35°C', enabled: false },
  ]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>ฉากและระบบอัตโนมัติ</Text>
        <Text style={styles.headerSubtitle}>จัดการฉากสำเร็จรูปและเงื่อนไข IoT ภายในฟาร์ม</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.sectionTitle}>ฉากสำเร็จรูป (Scenes)</Text>
        {scenes.map(scene => (
          <TouchableOpacity key={scene.id} style={styles.card}>
            <View style={styles.cardIconBox}>
              <Ionicons name="flash" size={20} color="#D97706" />
            </View>
            <View style={styles.cardInfo}>
              <Text style={styles.cardTitle}>{scene.name}</Text>
              <Text style={styles.cardDesc}>{scene.desc}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#94A3B8" />
          </TouchableOpacity>
        ))}

        <Text style={[styles.sectionTitle, { marginTop: 24 }]}>เงื่อนไขอัตโนมัติ (Automations)</Text>
        {automations.map(auto => (
          <View key={auto.id} style={styles.card}>
            <View style={[styles.cardIconBox, { backgroundColor: '#ECFDF5' }]}>
              <Ionicons name="git-branch" size={20} color="#059669" />
            </View>
            <View style={styles.cardInfo}>
              <Text style={styles.cardTitle}>{auto.name}</Text>
              <Text style={styles.cardDesc}>เงื่อนไข: {auto.condition}</Text>
            </View>
            <Switch
              trackColor={{ false: '#CBD5E1', true: '#6EE7B7' }}
              thumbColor={auto.enabled ? '#059669' : '#F8FAFC'}
              value={auto.enabled}
              onValueChange={() => {}}
            />
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC', paddingTop: 40 },
  header: { padding: 20, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  headerTitle: { fontSize: 18, fontWeight: 'bold', color: '#0F172A' },
  headerSubtitle: { fontSize: 12, color: '#64748B', marginTop: 2 },
  scrollContent: { padding: 20 },
  sectionTitle: { fontSize: 13, fontWeight: 'bold', color: '#64748B', marginBottom: 12, textTransform: 'uppercase' },
  card: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFFFFF', padding: 16, borderRadius: 20, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 2 },
  cardIconBox: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#FEF3C7', justifyContent: 'center', alignItems: 'center', marginRight: 14 },
  cardInfo: { flex: 1, marginRight: 10 },
  cardTitle: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  cardDesc: { fontSize: 12, color: '#64748B', marginTop: 2 },
});
