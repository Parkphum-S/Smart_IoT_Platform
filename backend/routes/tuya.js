const express = require('express');
const router = express.Router();
const axios = require('axios');
const crypto = require('crypto');

// เก็บค่า Config ชั่วคราวในหน่วยความจำ
let tuyaConfig = {
  clientId: '',
  clientSecret: '',
  region: 'ay',
  endpoint: 'https://openapi.tuyasg.com'
};

// 1. API สำหรับบันทึกค่า Config Tuya
router.post('/config', (req, res) => {
  const { clientId, clientSecret, region, endpoint } = req.body;
  
  if (!clientId || !clientSecret) {
    return res.status(400).json({ success: false, message: 'กรุณากรอก Client ID และ Client Secret' });
  }

  tuyaConfig = { clientId, clientSecret, region, endpoint };
  console.log('Tuya Config Updated:', tuyaConfig);
  
  return res.json({ success: true, message: 'บันทึกการตั้งค่า Tuya สำเร็จ' });
});

// 2. API สำหรับดึงค่า Config ปัจจุบัน
router.get('/config', (req, res) => {
  return res.json({ success: true, data: tuyaConfig });
});

// 3. API สำหรับซิงค์อุปกรณ์จริงจาก Tuya Cloud
router.post('/sync-devices', async (req, res) => {
  try {
    const { clientId, clientSecret, endpoint } = tuyaConfig;

    if (!clientId || !clientSecret) {
      return res.status(400).json({ success: false, message: 'ยังไม่ได้ตั้งค่า Tuya API Credentials' });
    }

    const t = Date.now().toString();
    const signStr = clientId + t + 'GET\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n\n/v1.0/token?grant_type=1';
    const signature = crypto.createHmac('sha256', clientSecret).update(signStr).digest('hex').toUpperCase();

    const tokenRes = await axios.get(`${endpoint}/v1.0/token?grant_type=1`, {
      headers: {
        'client_id': clientId,
        'sign': signature,
        't': t,
        'sign_method': 'HMAC-SHA256'
      }
    });

    if (!tokenRes.data.success) {
      return res.status(400).json({ success: false, message: 'ไม่สามารถเชื่อมต่อ Tuya Token API ได้: ' + tokenRes.data.msg });
    }

    const accessToken = tokenRes.data.result.access_token;

    const tDevices = Date.now().toString();
    const signDevicesStr = clientId + accessToken + tDevices + 'GET\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n\n/v1.0/iot-01/associated-users/devices';
    const signDevices = crypto.createHmac('sha256', clientSecret).update(signDevicesStr).digest('hex').toUpperCase();

    const devicesRes = await axios.get(`${endpoint}/v1.0/iot-01/associated-users/devices`, {
      headers: {
        'client_id': clientId,
        'access_token': accessToken,
        'sign': signDevices,
        't': tDevices,
        'sign_method': 'HMAC-SHA256'
      }
    });

    if (devicesRes.data.success) {
      const devices = devicesRes.data.result || [];
      return res.json({ 
        success: true, 
        message: `ซิงค์อุปกรณ์สำเร็จ พบอุปกรณ์ทั้งหมด ${devices.length} ตัว`,
        devices: devices 
      });
    } else {
      return res.status(400).json({ success: false, message: 'ดึงข้อมูลอุปกรณ์ไม่สำเร็จ: ' + devicesRes.data.msg });
    }

  } catch (error) {
    console.error('Tuya Sync Error:', error.response?.data || error.message);
    return res.status(500).json({ success: false, message: 'เกิดข้อผิดพลาดในการเชื่อมต่อ Tuya Cloud API' });
  }
});

module.exports = router;
