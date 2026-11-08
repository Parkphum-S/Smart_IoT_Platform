const express = require('express');
const cors = require('cors');
const mqtt = require('mqtt');
const bodyParser = require('body-parser');

const app = express();
app.use(cors());
app.use(bodyParser.json());

const PORT = 5000;
const MQTT_BROKER = 'mqtt://localhost:1883';

// ตัวแปรเก็บสถานะเซนเซอร์ล่าสุดจาก ESP32
let liveSensorData = {
  ZoneA: {
    name: 'แปลงเกษตรโซน A',
    temp: '32.5 °C',
    humidity: '68 %',
    vpd: '1.56 kPa',
    soilMoisture: '45 %',
    npk: 'N: 40, P: 25, K: 60 mg/kg',
    ph: '6.5',
    relayStatus: 'เปิดใช้งาน (ปั๊มน้ำหลัก)'
  }
};

// เชื่อมต่อ MQTT Broker (Mosquitto)
const mqttClient = mqtt.connect(MQTT_BROKER);

mqttClient.on('connect', () => {
  console.log('Backend connected to MQTT Broker successfully');
  mqttClient.subscribe('farm/+/sensors', (err) => {
    if (!err) {
      console.log('Subscribed to farm/+/sensors');
    }
  });
});

// รับข้อมูลจาก ESP32 ที่ส่งมาทาง MQTT
mqttClient.on('message', (topic, payload) => {
  try {
    const data = JSON.parse(payload.toString());
    console.log(`Received MQTT from [${topic}]:`, data);
    
    // อัปเดตข้อมูลสด
    liveSensorData.ZoneA.temp = `${data.temperature} °C`;
    liveSensorData.ZoneA.humidity = `${data.humidity} %`;
    liveSensorData.ZoneA.soilMoisture = `${data.soil_moisture} %`;
  } catch (e) {
    console.error('Failed to parse MQTT payload:', e);
  }
});

// REST API ให้ Web App และ Mobile App ดึงข้อมูลสด
app.get('/api/sensors', (req, res) => {
  res.json(liveSensorData);
});

// API สำหรับรับค่า NPK / pH ที่ผู้ใช้กรอกผ่านเว็บหรือมือถือแล้วซิงค์กัน
app.post('/api/sensors/soil', (req, res) => {
  const { zone, npk, ph } = req.body;
  if (liveSensorData[zone]) {
    if (npk) liveSensorData[zone].npk = npk;
    if (ph) liveSensorData[zone].ph = ph;
    return res.json({ success: true, message: 'Updated soil data successfully', data: liveSensorData[zone] });
  }
  res.status(404).json({ success: false, message: 'Zone not found' });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`IoT Backend API is running on port ${PORT}`);
});
