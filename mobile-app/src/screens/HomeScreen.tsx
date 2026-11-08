import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function HomeScreen() {
  const [sensorData, setSensorData] = useState({
    temp: "กำลังโหลด...",
    humidity: "กำลังโหลด...",
    soilMoisture: "กำลังโหลด...",
    npk: "N: 40, P: 25, K: 60 mg/kg",
    ph: "6.5"
  });

  useEffect(() => {
    const fetchLiveData = async () => {
      try {
        const response = await fetch("http://192.168.1.98:5000/api/sensors");
        const data = await response.json();
        if (data && data.ZoneA) {
          setSensorData({
            temp: data.ZoneA.temp,
            humidity: data.ZoneA.humidity,
            soilMoisture: data.ZoneA.soilMoisture || "45 %",
            npk: data.ZoneA.npk,
            ph: data.ZoneA.ph,
          });
        }
      } catch (error) {
        console.log("Error fetching live sensors:", error);
      }
    };
    fetchLiveData();
    const interval = setInterval(fetchLiveData, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <ScrollView style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>แปลงเกษตรโซน A (ESP32 Live)</Text>
        <Text style={styles.val}>🌡️ อุณหภูมิ: {sensorData.temp}</Text>
        <Text style={styles.val}>💧 ความชื้นอากาศ: {sensorData.humidity}</Text>
        <Text style={styles.val}>🌱 ความชื้นดิน: {sensorData.soilMoisture}</Text>
        <Text style={styles.val}>🌿 NPK: {sensorData.npk}</Text>
        <Text style={styles.val}>🧪 pH: {sensorData.ph}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8FAFC", padding: 16 },
  card: { backgroundColor: "#FFF", padding: 20, borderRadius: 16, marginBottom: 16, borderWidth: 1, borderColor: "#E2E8F0" },
  title: { fontSize: 18, fontWeight: "bold", color: "#1E293B", marginBottom: 12 },
  val: { fontSize: 14, color: "#334155", marginBottom: 8, fontWeight: "600" }
});
