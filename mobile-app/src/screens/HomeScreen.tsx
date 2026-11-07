import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, Switch, ScrollView, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Location from 'expo-location';

export default function HomeScreen({ navigation }: any) {
  const [selectedRoom, setSelectedRoom] = useState('ทั้งหมด');
  const rooms = ['ทั้งหมด', 'แปลงเกษตรโซน A', 'โรงเรือนเพาะชำ', 'แปลงเกษตรโซน B'];

  const [weather, setWeather] = useState({
    temp: '--',
    humidity: '--',
    description: 'กำลังโหลดอากาศ...',
    locationName: 'กำลังระบุพิกัดฟาร์ม...',
  });

  const [devices, setDevices] = useState([
    { id: 'dev-1', name: 'ปั๊มน้ำหลัก (โซน A)', room: 'แปลงเกษตรโซน A', isOn: true },
    { id: 'dev-2', name: 'ระบบพ่นหมอกโรงเรือน', room: 'โรงเรือนเพาะชำ', isOn: false },
    { id: 'dev-3', name: 'วาล์วน้ำหยด (โซน B)', room: 'แปลงเกษตรโซน B', isOn: true },
  ]);

  useEffect(() => {
    const fetchWeather = async (lat: number, lon: number, locName: string) => {
      const apiKey = 'c88ea29af43110c4475edc723102b950';
      try {
        const res = await fetch(
          `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&units=metric&lang=th&appid=${apiKey}`
        );
        const data = await res.json();
        if (data.main) {
          setWeather({
            temp: data.main.temp.toFixed(1),
            humidity: data.main.humidity,
            description: data.weather[0].description,
            locationName: `${data.name || locName}, ${data.sys?.country || 'TH'}`,
          });
        }
      } catch (e) {
        console.error('Failed to fetch OpenWeather:', e);
        setWeather(prev => ({ ...prev, description: 'ไม่สามารถโหลดข้อมูลอากาศได้' }));
      }
    };

    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        fetchWeather(13.8621, 100.5140, 'นนทบุรี (พิกัดฟาร์มหลัก)');
        return;
      }

      try {
        let location = await Location.getCurrentPositionAsync({});
        fetchWeather(location.coords.latitude, location.coords.longitude, 'ตำแหน่งปัจจุบัน');
      } catch (error) {
        fetchWeather(13.8621, 100.5140, 'นนทบุรี (พิกัดฟาร์มหลัก)');
      }
    })();
  }, []);

  const toggleDevice = (id: string) => {
    setDevices(prev =>
      prev.map(dev => (dev.id === id ? { ...dev, isOn: !dev.isOn } : dev))
    );
  };

  const filteredDevices = selectedRoom === 'ทั้งหมด' 
    ? devices 
    : devices.filter(d => d.room === selectedRoom);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Smart Agri-IoT</Text>
          <Text style={styles.headerSubtitle}>{weather.locationName}</Text>
        </View>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={() => navigation.navigate('RoomManagement')} style={styles.iconBtn}>
            <Ionicons name="grid-outline" size={20} color="#059669" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => navigation.navigate('AddDevice')} style={[styles.iconBtn, { marginLeft: 8 }]}>
            <Ionicons name="add" size={22} color="#059669" />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.weatherCard}>
          <View style={{ flex: 1 }}>
            <Text style={styles.weatherTitle}>สภาพอากาศจริง (OpenWeather Live)</Text>
            <Text style={styles.weatherTemp}>
              {weather.temp} °C | ความชื้น {weather.humidity}%
            </Text>
            <Text style={styles.weatherDesc}>{weather.description}</Text>
          </View>
          <Ionicons name="partly-sunny" size={38} color="#D97706" />
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabScroll}>
          {rooms.map(room => (
            <TouchableOpacity 
              key={room} 
              style={[styles.roomTab, selectedRoom === room && styles.roomTabActive]}
              onPress={() => setSelectedRoom(room)}
            >
              <Text style={[styles.roomTabText, selectedRoom === room && styles.roomTabTextActive]}>{room}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <Text style={styles.sectionTitle}>อุปกรณ์ควบคุมในฟาร์ม ({filteredDevices.length})</Text>
        
        {filteredDevices.map(device => (
          <TouchableOpacity 
            key={device.id} 
            style={styles.deviceCard}
            onPress={() => navigation.navigate('DeviceDetail', { deviceId: device.id, deviceName: device.name })}
          >
            <View style={styles.deviceInfo}>
              <View style={[styles.iconBox, { backgroundColor: device.isOn ? '#D1FAE5' : '#F1F5F9' }]}>
                <Ionicons name="power" size={20} color={device.isOn ? '#059669' : '#94A3B8'} />
              </View>
              <View>
                <Text style={styles.deviceName}>{device.name}</Text>
                <Text style={styles.deviceRoom}>{device.room}</Text>
              </View>
            </View>

            <Switch
              trackColor={{ false: '#CBD5E1', true: '#6EE7B7' }}
              thumbColor={device.isOn ? '#059669' : '#F8FAFC'}
              onValueChange={() => toggleDevice(device.id)}
              value={device.isOn}
            />
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC', paddingTop: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  headerTitle: { fontSize: 18, fontWeight: 'bold', color: '#0F172A' },
  headerSubtitle: { fontSize: 12, color: '#64748B', marginTop: 2 },
  headerActions: { flexDirection: 'row' },
  iconBtn: { width: 36, height: 36, borderRadius: 10, backgroundColor: '#ECFDF5', justifyContent: 'center', alignItems: 'center' },
  scrollContent: { padding: 20 },
  weatherCard: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#FFFFFF', padding: 20, borderRadius: 20, marginBottom: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 2 },
  weatherTitle: { fontSize: 11, fontWeight: '600', color: '#64748B', textTransform: 'uppercase' },
  weatherTemp: { fontSize: 18, fontWeight: 'bold', color: '#1E293B', marginTop: 4 },
  weatherDesc: { fontSize: 12, color: '#059669', marginTop: 4, textTransform: 'capitalize', fontWeight: '500' },
  tabScroll: { marginBottom: 16 },
  roomTab: { paddingHorizontal: 16, paddingVertical: 8, backgroundColor: '#FFFFFF', borderRadius: 20, marginRight: 8, borderWidth: 1, borderColor: '#E2E8F0' },
  roomTabActive: { backgroundColor: '#059669', borderColor: '#059669' },
  roomTabText: { fontSize: 13, color: '#64748B', fontWeight: '500' },
  roomTabTextActive: { color: '#FFFFFF', fontWeight: 'bold' },
  sectionTitle: { fontSize: 13, fontWeight: 'bold', color: '#64748B', marginBottom: 12, textTransform: 'uppercase' },
  deviceCard: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#FFFFFF', padding: 16, borderRadius: 20, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 2 },
  deviceInfo: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center', marginRight: 14 },
  deviceName: { fontSize: 14, fontWeight: 'bold', color: '#1E293B' },
  deviceRoom: { fontSize: 12, color: '#94A3B8', marginTop: 2 },
});
