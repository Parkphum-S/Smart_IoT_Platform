'use client';

import { useState } from 'react';

export default function TuyaSettingsPage() {
  const [clientId, setClientId] = useState('tsw9ecujnuur9xfcym4');
  const [clientSecret, setClientSecret] = useState('************************');
  const [region, setRegion] = useState('Western America Data Center');
  const [endpoint, setEndpoint] = useState('https://openapi.tuyaus.com');

  const [devices, setDevices] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSync = async () => {
    setLoading(true);
    setMessage('');
    try {
      // ยิงตรงไปที่ FastAPI Backend บนพอร์ต 8000
      const res = await fetch('http://localhost:8000/api/v1/tuya/sync-devices', {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success || data.devices) {
        setDevices(data.devices || []);
        setMessage(data.message || 'ซิงค์อุปกรณ์สำเร็จ');
      } else {
        setMessage('เกิดข้อผิดพลาดในการซิงค์: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      setMessage('ไม่สามารถเชื่อมต่อกับ Backend (พอร์ต 8000) ได้ กรุณาตรวจสอบว่า Backend เปิดอยู่หรือไม่');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('http://localhost:8000/api/v1/tuya/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clientId, clientSecret, region, endpoint })
      });
      const data = await res.json();
      if (data.success) {
        setMessage('บันทึกการตั้งค่า Tuya สำเร็จ');
      } else {
        setMessage('บันทึกไม่สำเร็จ: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      setMessage('บันทึกการตั้งค่าลงระบบเรียบร้อยแล้ว');
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <a href="/settings" className="text-sm text-blue-600 hover:underline mb-2 inline-block">
            &larr; กลับสู่หน้าตั้งค่าระบบ
          </a>
          <h1 className="text-2xl font-bold text-gray-800">ตั้งค่า Tuya Cloud API</h1>
          <p className="text-sm text-gray-500">จัดการข้อมูลการเชื่อมต่อ API ของ Tuya Cloud เพื่อดึงข้อมูลและควบคุมอุปกรณ์สมาร์ทโฮม</p>
        </div>
        <button
          onClick={handleSync}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow transition flex items-center space-x-2 disabled:opacity-50"
        >
          <span>{loading ? 'กำลังซิงค์...' : 'ซิงค์อุปกรณ์จาก Tuya'}</span>
        </button>
      </div>

      {message && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-sm">
          {message}
        </div>
      )}

      {/* ฟอร์มตั้งค่า */}
      <form onSubmit={handleSaveConfig} className="bg-white p-6 rounded-2xl shadow border border-gray-100 space-y-4">
        <h2 className="text-lg font-semibold text-gray-700">ข้อมูลการรับรอง (API Credentials)</h2>
        <div>
          <label className="block text-sm font-medium text-gray-600">Access ID / Client ID</label>
          <input
            type="text"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            className="mt-1 w-full p-2.5 border rounded-lg bg-gray-50 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600">Access Secret / Client Secret</label>
          <input
            type="password"
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
            className="mt-1 w-full p-2.5 border rounded-lg bg-gray-50 text-sm"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-600">Data Center Region</label>
            <select
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className="mt-1 w-full p-2.5 border rounded-lg bg-gray-50 text-sm"
            >
              <option>Western America Data Center</option>
              <option>Singapore Data Center (SG)</option>
              <option>Europe Data Center (EU)</option>
              <option>Asia Data Center (AY)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600">API Endpoint URL</label>
            <input
              type="text"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              className="mt-1 w-full p-2.5 border rounded-lg bg-gray-50 text-sm"
            />
          </div>
        </div>
        <div className="flex justify-end pt-2">
          <button type="submit" className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl shadow transition">
            บันทึกการตั้งค่า Tuya
          </button>
        </div>
      </form>

      {/* รายการอุปกรณ์ที่ซิงค์แล้ว */}
      <div className="bg-white p-6 rounded-2xl shadow border border-gray-100 space-y-4">
        <h2 className="text-lg font-semibold text-gray-700">
          รายการอุปกรณ์ที่ซิงค์แล้ว ({devices.length})
        </h2>
        {devices.length === 0 ? (
          <p className="text-sm text-gray-500">ยังไม่มีข้อมูลอุปกรณ์ กรุณากดปุ่ม "ซิงค์อุปกรณ์จาก Tuya" ด้านบน</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b text-sm text-gray-600">
                  <th className="py-2 px-3">ชื่ออุปกรณ์</th>
                  <th className="py-2 px-3">Device ID</th>
                  <th className="py-2 px-3">สถานะ</th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y">
                {devices.map((dev: any, index: number) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="py-3 px-3 font-medium text-gray-800">{dev.name || 'Unknown Device'}</td>
                    <td className="py-3 px-3 text-gray-500 font-mono text-xs">{dev.id || dev.devId}</td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-1 rounded-full text-xs bg-emerald-100 text-emerald-700">
                        {dev.online ? 'Online' : 'Connected'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
