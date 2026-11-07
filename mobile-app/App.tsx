import React, { useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView, StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import HomeScreen from './src/screens/HomeScreen';
import ZoneScreen from './src/screens/ZoneScreen';
import DeviceScreen from './src/screens/DeviceScreen';
import ChartScreen from './src/screens/ChartScreen';
import AutomationScreen from './src/screens/AutomationScreen';
import NotificationScreen from './src/screens/NotificationScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import WorkspaceSwitcherScreen from './src/screens/WorkspaceSwitcherScreen';
import MemberScreen from './src/screens/MemberScreen';
import AuditLogScreen from './src/screens/AuditLogScreen';

type TabType = 'home' | 'zones' | 'devices' | 'charts' | 'automation' | 'notifications' | 'profile' | 'workspaces' | 'members' | 'audit';

export default function App() {
  const [currentTab, setCurrentTab] = useState<TabType>('home');

  const isSubScreen = ['workspaces', 'members', 'audit'].includes(currentTab);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />

      {isSubScreen && (
        <TouchableOpacity style={styles.backBar} onPress={() => setCurrentTab('profile')}>
          <Ionicons name="arrow-back" size={18} color="#059669" />
          <Text style={styles.backText}>กลับไปหน้าโปรไฟล์</Text>
        </TouchableOpacity>
      )}

      <View style={styles.contentArea}>
        {currentTab === 'home' && <HomeScreen />}
        {currentTab === 'zones' && <ZoneScreen />}
        {currentTab === 'devices' && <DeviceScreen />}
        {currentTab === 'charts' && <ChartScreen />}
        {currentTab === 'automation' && <AutomationScreen />}
        {currentTab === 'notifications' && <NotificationScreen />}
        {currentTab === 'profile' && <ProfileScreen onNavigate={(tab) => setCurrentTab(tab)} />}
        {currentTab === 'workspaces' && <WorkspaceSwitcherScreen />}
        {currentTab === 'members' && <MemberScreen />}
        {currentTab === 'audit' && <AuditLogScreen />}
      </View>

      <View style={styles.tabBar}>
        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('home')}>
          <Ionicons name={currentTab === 'home' ? 'home' : 'home-outline'} size={18} color={currentTab === 'home' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'home' && styles.tabTextActive]}>หน้าแรก</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('zones')}>
          <Ionicons name={currentTab === 'zones' ? 'map' : 'map-outline'} size={18} color={currentTab === 'zones' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'zones' && styles.tabTextActive]}>โซน</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('devices')}>
          <Ionicons name={currentTab === 'devices' ? 'hardware-chip' : 'hardware-chip-outline'} size={18} color={currentTab === 'devices' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'devices' && styles.tabTextActive]}>อุปกรณ์</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('charts')}>
          <Ionicons name={currentTab === 'charts' ? 'stats-chart' : 'stats-chart-outline'} size={18} color={currentTab === 'charts' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'charts' && styles.tabTextActive]}>กราฟ</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('automation')}>
          <Ionicons name={currentTab === 'automation' ? 'git-branch' : 'git-branch-outline'} size={18} color={currentTab === 'automation' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'automation' && styles.tabTextActive]}>อัตโนมัติ</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('notifications')}>
          <Ionicons name={currentTab === 'notifications' ? 'notifications' : 'notifications-outline'} size={18} color={currentTab === 'notifications' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'notifications' && styles.tabTextActive]}>แจ้งเตือน</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('profile')}>
          <Ionicons name={currentTab === 'profile' || isSubScreen ? 'person' : 'person-outline'} size={18} color={currentTab === 'profile' || isSubScreen ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, (currentTab === 'profile' || isSubScreen) && styles.tabTextActive]}>โปรไฟล์</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  contentArea: { flex: 1 },
  backBar: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, backgroundColor: '#FFF', borderBottomWidth: 1, borderBottomColor: '#F1F5F9', gap: 6 },
  backText: { fontSize: 13, fontWeight: 'bold', color: '#059669' },
  tabBar: { flexDirection: 'row', backgroundColor: '#FFF', borderTopWidth: 1, borderTopColor: '#F1F5F9', paddingVertical: 6, paddingHorizontal: 2 },
  tabItem: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  tabText: { fontSize: 8.5, color: '#94A3B8', fontWeight: '600', marginTop: 2 },
  tabTextActive: { color: '#059669', fontWeight: 'bold' },
});
