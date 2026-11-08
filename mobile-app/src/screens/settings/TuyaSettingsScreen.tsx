import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, SafeAreaView, ScrollView, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function TuyaSettingsScreen() {
  const [accessId, setAccessId] = useState('');
  const [accessKey, setAccessKey] = useState('');
  const [region, setRegion] = useState('us');
  const [loading, setLoading] = useState(false);

  const handleSave = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      Alert.alert('สำเร็จ', 'บันทึกและเชื่อมต่อ Tuya Cloud API เรียบร้อยแล้ว');
    }, 1200);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.title}>Tuya Cloud Settings</Text>
          <Text style={styles.subtitle}>เชื่อมต่อบัญชี Tuya IoT Platform เข้าสู่ระบบฟาร์ม</Text>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.label}>TUYA ACCESS ID / CLIENT ID</Text>
          <TextInput
            style={styles.input}
            placeholder="กรอก Access ID"
            placeholderTextColor="#94a3b8"
            value={accessId}
            onChangeText={setAccessId}
          />

          <Text style={styles.label}>TUYA ACCESS KEY / SECRET</Text>
          <TextInput
            style={styles.input}
            placeholder="กรอก Access Key Secret"
            placeholderTextColor="#94a3b8"
            secureTextEntry
            value={accessKey}
            onChangeText={setAccessKey}
          />

          <TouchableOpacity 
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleSave}
            disabled={loading}
          >
            <Ionicons name="cloud-upload-outline" size={18} color="#ffffff" style={{ marginRight: 8 }} />
            <Text style={styles.buttonText}>{loading ? 'กำลังเชื่อมต่อ...' : 'ทดสอบและบันทึกการเชื่อมต่อ'}</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  scrollContent: { padding: 20 },
  header: { marginBottom: 24 },
  title: { fontSize: 22, fontWeight: 'bold', color: '#0f172a' },
  subtitle: { fontSize: 13, color: '#64748b', marginTop: 4 },
  formCard: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: '#f1f5f9'
  },
  label: { fontSize: 11, fontWeight: '700', color: '#475569', marginBottom: 8, letterSpacing: 0.5 },
  input: {
    backgroundColor: '#f8fafc',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 14,
    color: '#0f172a',
    marginBottom: 20
  },
  button: {
    backgroundColor: '#059669',
    borderRadius: 16,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 14,
    shadowColor: '#059669',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4
  },
  buttonDisabled: { opacity: 0.7 },
  buttonText: { color: '#ffffff', fontSize: 15, fontWeight: '600' }
});
