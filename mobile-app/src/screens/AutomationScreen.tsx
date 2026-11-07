import React, { useState } from 'react';
import { StyleSheet, Text, View, Switch, ScrollView, SafeAreaView, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function AutomationScreen() {
  const [scenes, setScenes] = useState([
    { id: 'scene-1', name: 'รดน้ำแปลงโซน A (อัตโนมัติเช้า)', condition: 'ทุกวัน เวลา 06:00 น.', isActive: true },
    { id: 'scene-2', name: 'พ่นหมอกลดความร้อนโรงเรือน', condition: 'อุณหภูมิ > 35°C', isActive: false },
    { id: 'scene-3', name: 'ปิดระบบน้ำทั้งหมด (โหมดกลางคืน)', condition: 'ทุกวัน เวลา 20:00 น.', isActive: true },
  ]);

  const toggleScene = (id: string) => {
    setScenes(prev =>
      prev.map(scene => (scene.id === id ? { ...scene, isActive: !scene.isActive } : scene))
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>ฉากและระบบอัตโนมัติ</Text>
          <Text style={styles.headerSubtitle}>ตั้งค่าเงื่อนไขการทำงานอัจฉริยะ</Text>
        </View>
        <Ionicons name="flash-outline" size={24} color="#047857" />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.sectionTitle}>รายการ Automation ทั้งหมด</Text>
        
        {scenes.map(scene => (
          <View key={scene.id} style={styles.sceneCard}>
            <View style={styles.sceneInfo}>
              <View style={[styles.iconBox, { backgroundColor: scene.isActive ? '#D1FAE5' : '#F1F5F9' }]}>
                <Ionicons name="git-branch-outline" size={20} color={scene.isActive ? '#059669' : '#94A3B8'} />
              </View>
              <View style={{ flex: 1, marginRight: 10 }}>
                <Text style={styles.sceneName}>{scene.name}</Text>
                <Text style={styles.sceneCondition}>{scene.condition}</Text>
              </View>
            </View>

            <Switch
              trackColor={{ false: '#CBD5E1', true: '#6EE7B7' }}
              thumbColor={scene.isActive ? '#059669' : '#F8FAFC'}
              ios_backgroundColor="#CBD5E1"
              onValueChange={() => toggleScene(scene.id)}
              value={scene.isActive}
            />
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  headerTitle: { fontSize: 18, fontWeight: 'bold', color: '#0F172A' },
  headerSubtitle: { fontSize: 12, color: '#64748B', marginTop: 2 },
  scrollContent: { padding: 20 },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#1E293B', marginBottom: 15 },
  sceneCard: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#FFFFFF', padding: 16, borderRadius: 20, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 2 },
  sceneInfo: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  iconBox: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  sceneName: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  sceneCondition: { fontSize: 12, color: '#64748B', marginTop: 3 },
});
