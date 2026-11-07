import React, { useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView, StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import HomeScreen from './src/screens/HomeScreen';
import DeviceScreen from './src/screens/DeviceScreen';
import ChartScreen from './src/screens/ChartScreen';
import AutomationScreen from './src/screens/AutomationScreen';
import NotificationScreen from './src/screens/NotificationScreen';
import ProfileScreen from './src/screens/ProfileScreen';

export default function App() {
  const [currentTab, setCurrentTab] = useState<'home' | 'devices' | 'charts' | 'automation' | 'notifications' | 'profile'>('home');

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      
      <View style={styles.contentArea}>
        {currentTab === 'home' && <HomeScreen />}
        {currentTab === 'devices' && <DeviceScreen />}
        {currentTab === 'charts' && <ChartScreen />}
        {currentTab === 'automation' && <AutomationScreen />}
        {currentTab === 'notifications' && <NotificationScreen />}
        {currentTab === 'profile' && <ProfileScreen />}
      </View>

      <View style={styles.tabBar}>
        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('home')}>
          <Ionicons name={currentTab === 'home' ? 'home' : 'home-outline'} size={18} color={currentTab === 'home' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'home' && styles.tabTextActive]}>หน้าแรก</Text>
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
          <Ionicons name={currentTab === 'profile' ? 'person' : 'person-outline'} size={18} color={currentTab === 'profile' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'profile' && styles.tabTextActive]}>โปรไฟล์</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  contentArea: { flex: 1 },
  tabBar: { flexDirection: 'row', backgroundColor: '#FFF', borderTopWidth: 1, borderTopColor: '#F1F5F9', paddingVertical: 6, paddingHorizontal: 2 },
  tabItem: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  tabText: { fontSize: 8.5, color: '#94A3B8', fontWeight: '600', marginTop: 2 },
  tabTextActive: { color: '#059669', fontWeight: 'bold' },
});
