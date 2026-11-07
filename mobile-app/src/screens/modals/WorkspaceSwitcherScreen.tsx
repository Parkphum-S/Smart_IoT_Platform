import React, { useState } from 'react';
import { StyleSheet, Text, View, SafeAreaView, TouchableOpacity, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function WorkspaceSwitcherScreen({ navigation }: any) {
  const [workspaces, setWorkspaces] = useState([
    { id: 'ws-1', name: 'ฟาร์มตัวอย่าง (Smart Agri-IoT)', role: 'Owner', active: true },
    { id: 'ws-2', name: 'โรงเรือนทดลองแปลง B', role: 'Admin', active: false },
  ]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={20} color="#0F172A" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>สลับ Workspace / ฟาร์ม</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {workspaces.map(ws => (
          <TouchableOpacity key={ws.id} style={[styles.wsCard, ws.active && styles.wsCardActive]}>
            <View>
              <Text style={styles.wsName}>{ws.name}</Text>
              <Text style={styles.wsRole}>บทบาทสิทธิ์: {ws.role}</Text>
            </View>
            {ws.active && <Ionicons name="checkmark-circle" size={22} color="#059669" />}
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  header: { flexDirection: 'row', alignItems: 'center', padding: 20, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  backButton: { marginRight: 16 },
  headerTitle: { fontSize: 16, fontWeight: 'bold', color: '#0F172A' },
  content: { padding: 20 },
  wsCard: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#FFFFFF', padding: 18, borderRadius: 16, marginBottom: 12, borderWidth: 1, borderColor: '#E2E8F0' },
  wsCardActive: { borderColor: '#059669', backgroundColor: '#ECFDF5' },
  wsName: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  wsRole: { fontSize: 12, color: '#64748B', marginTop: 2 },
});
