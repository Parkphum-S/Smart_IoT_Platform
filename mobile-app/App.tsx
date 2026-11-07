import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

// นำเข้าหน้าจอต่างๆ
import HomeScreen from './src/screens/HomeScreen';
import DeviceScreen from './src/screens/DeviceScreen';
import AutomationScreen from './src/screens/AutomationScreen';
import ProfileScreen from './src/screens/ProfileScreen';

export default function App() {
  const [currentTab, setCurrentTab] = React.useState<'home' | 'devices' | 'automation' | 'profile'>('home');

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      
      {/* ส่วนแสดงผลหน้าจอตาม Tab ที่เลือก */}
      <div style={{ flex: 1 }}>
        {currentTab === 'home' && <HomeScreen />}
        {currentTab === 'devices' && <DeviceScreen />}
        {currentTab === 'automation' && <AutomationScreen />}
        {currentTab === 'profile' && <ProfileScreen />}
      </div>

      {/* Bottom Navigation Bar */}
      <View style={styles.tabBar}>
        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('home')}>
          <Ionicons name={currentTab === 'home' ? 'home' : 'home-outline'} size={20} color={currentTab === 'home' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'home' && styles.tabTextActive]}>หน้าแรก</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('devices')}>
          <Ionicons name={currentTab === 'devices' ? 'hardware-chip' : 'hardware-chip-outline'} size={20} color={currentTab === 'devices' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'devices' && styles.tabTextActive]}>อุปกรณ์</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('automation')}>
          <Ionicons name={currentTab === 'automation' ? 'git-branch' : 'git-branch-outline'} size={20} color={currentTab === 'automation' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'automation' && styles.tabTextActive]}>อัตโนมัติ</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentTab('profile')}>
          <Ionicons name={currentTab === 'profile' ? 'person' : 'person-outline'} size={20} color={currentTab === 'profile' ? '#059669' : '#94A3B8'} />
          <Text style={[styles.tabText, currentTab === 'profile' && styles.tabTextActive]}>โปรไฟล์</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  tabBar: { flexDirection: 'row', backgroundColor: '#FFF', borderTopWidth: 1, borderTopColor: '#F1F5F9', paddingVertical: 8, paddingHorizontal: 12 },
  tabItem: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  tabText: { fontSize: 10, color: '#94A3B8', fontWeight: '600', marginTop: 2 },
  tabTextActive: { color: '#059669', fontWeight: 'bold' },
});
