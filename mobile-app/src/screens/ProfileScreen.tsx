import React from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function ProfileScreen({ navigation }: any) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>โปรไฟล์และการตั้งค่า</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.userCard}>
          <View style={styles.avatarBox}>
            <Text style={styles.avatarText}>P</Text>
          </View>
          <View>
            <Text style={styles.userName}>Parkphum (Owner)</Text>
            <Text style={styles.userEmail}>parkphum@smartiot.local</Text>
          </View>
        </View>

        <View style={styles.menuGroup}>
          <TouchableOpacity 
            style={styles.menuItem} 
            onPress={() => navigation.navigate('WorkspaceSwitcher')}
          >
            <Ionicons name="business-outline" size={20} color="#059669" style={styles.menuIcon} />
            <Text style={styles.menuText}>สลับ Workspace / ฟาร์ม</Text>
            <Ionicons name="chevron-forward" size={16} color="#94A3B8" />
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.menuItem}
            onPress={() => alert('การตั้งค่าการแจ้งเตือน')}
          >
            <Ionicons name="notifications-outline" size={20} color="#059669" style={styles.menuIcon} />
            <Text style={styles.menuText}>การตั้งค่าการแจ้งเตือน</Text>
            <Ionicons name="chevron-forward" size={16} color="#94A3B8" />
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.menuItem}
            onPress={() => alert('ความปลอดภัยและสิทธิ์การใช้งาน RBAC')}
          >
            <Ionicons name="shield-outline" size={20} color="#059669" style={styles.menuIcon} />
            <Text style={styles.menuText}>ความปลอดภัยและสิทธิ์การใช้งาน</Text>
            <Ionicons name="chevron-forward" size={16} color="#94A3B8" />
          </TouchableOpacity>
        </View>

        <TouchableOpacity 
          style={styles.logoutButton}
          onPress={() => navigation.navigate('MainTabs')}
        >
          <Ionicons name="log-out-outline" size={18} color="#DC2626" style={{ marginRight: 8 }} />
          <Text style={styles.logoutText}>ออกจากระบบ</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC', paddingTop: 40 },
  header: { padding: 20, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  headerTitle: { fontSize: 18, fontWeight: 'bold', color: '#0F172A' },
  content: { padding: 20 },
  userCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFFFFF', padding: 20, borderRadius: 20, marginBottom: 20, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 2 },
  avatarBox: { width: 50, height: 50, borderRadius: 25, backgroundColor: '#D1FAE5', justifyContent: 'center', alignItems: 'center', marginRight: 16 },
  avatarText: { fontSize: 20, fontWeight: 'bold', color: '#059669' },
  userName: { fontSize: 16, fontWeight: 'bold', color: '#1E293B' },
  userEmail: { fontSize: 12, color: '#64748B', marginTop: 2 },
  menuGroup: { backgroundColor: '#FFFFFF', borderRadius: 20, paddingHorizontal: 16, marginBottom: 20, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 2 },
  menuItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  menuIcon: { marginRight: 14 },
  menuText: { flex: 1, fontSize: 14, color: '#334155', fontWeight: '500' },
  logoutButton: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', backgroundColor: '#FEF2F2', padding: 16, borderRadius: 16, borderWidth: 1, borderColor: '#FEE2E2' },
  logoutText: { color: '#DC2626', fontWeight: 'bold', fontSize: 14 },
});
