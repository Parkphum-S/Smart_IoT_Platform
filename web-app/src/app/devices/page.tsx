'use client';

import React, { useState } from 'react';
import { LayoutDashboard, Cpu, Plus, Trash2, X, RefreshCw, CheckCircle2, LogOut } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function DevicesPage() {
  const router = useRouter();
  const [devices, setDevices] = useState([
    { id: 'dev-1', name: 'ปั๊มน้ำหลัก (โซน A)', protocol: 'ESP32 MQTT', room: 'แปลงเกษตรโซน A', targetId: 'farm/zoneA/sensors', isOnline: true, isOn: true },
    { id: 'dev-2', name: 'เซนเซอร์วัดความชื้นดิน Tuya', protocol: 'Zigbee Hub', room: 'โรงเรือนเพาะชำ', targetId: 'zigbee-sensor-02', isOnline: true, isOn: false },
  ]);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState<'idle' | 'scanning' | 'success'>('idle');

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    protocol: 'ESP32 / ESP8266 (MQTT)',
    room: 'แปลงเกษตรโซน A',
    targetId: '',
    pinConfig: 'Relay: GPIO 23, DHT22: GPIO 4',
    threshold: 'ความชื้น < 30%'
  });

  const handleScan = () => {
    setIsScanning(true);
    setScanStatus('scanning');
    setTimeout(() => {
      setIsScanning(false);
      setScanStatus('success');
      setFormData(prev => ({ ...prev, targetId: 'ESP32_DEV_98A4BC' }));
    }, 2000);
  };

  const handleAddDevice = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name) return;
    
    const newDev = {
      id: `dev-${Date.now()}`,
      name: formData.name,
      protocol: formData.protocol,
      room: formData.room,
      targetId: formData.targetId || 'farm/device/control',
      isOnline: true,
      isOn: false
    };

    setDevices([...devices, newDev]);
    setIsModalOpen(false);
    setFormData({ name: '', protocol: 'ESP32 / ESP8266 (MQTT)', room: 'แปลงเกษตรโซน A', targetId: '', pinConfig: '', threshold: '' });
    setScanStatus('idle');
  };

  return (
    <div className="min-h-screen bg-slate-50/50 flex text-slate-900">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-white border-r border-slate-100 hidden md:flex flex-col justify-between p-6 shadow-sm">
        <div>
          <div className="flex items-center space-x-3 mb-10">
            {/* โลโก้จริงจาก /images/logo.png */}
            <div className="w-10 h-10 rounded-2xl overflow-hidden border border-slate-200 shadow-sm bg-white flex-shrink-0 flex items-center justify-center">
              <img 
                src="/images/logo.png" 
                alt="Smart IoT Logo" 
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <h1 className="font-bold text-slate-900 text-sm tracking-tight">Smart IoT Platform</h1>
              <p className="text-[10px] text-slate-400 font-medium">Farm IoT Solution</p>
            </div>
          </div>
          <nav className="space-y-1">
            <button onClick={() => router.push('/dashboard')} className="w-full flex items-center space-x-3 px-4 py-3 rounded-2xl text-slate-600 hover:bg-slate-50 font-medium text-sm transition-colors text-left cursor-pointer">
              <LayoutDashboard size={18} />
              <span>แดชบอร์ดภาพรวม</span>
            </button>
            <button onClick={() => router.push('/devices')} className="w-full flex items-center space-x-3 px-4 py-3 rounded-2xl bg-emerald-50 text-emerald-700 font-semibold text-sm text-left cursor-pointer">
              <Cpu size={18} />
              <span>จัดการอุปกรณ์ (Devices)</span>
            </button>
          </nav>
        </div>

        <div className="pt-6 border-t border-slate-100">
          <button 
            onClick={() => router.push('/login')}
            className="w-full flex items-center space-x-3 px-4 py-3 rounded-2xl text-rose-600 hover:bg-rose-50 font-medium text-sm transition-colors cursor-pointer"
          >
            <LogOut size={18} />
            <span>ออกจากระบบ</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-6 md:p-10 overflow-y-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">จัดการอุปกรณ์ฮาร์ดแวร์ทั้งหมด</h2>
            <p className="text-sm text-slate-500 mt-0.5">รองรับอุปกรณ์ ESP32, ESP8266, Tuya และ Zigbee Gateway</p>
          </div>
          <button 
            onClick={() => setIsModalOpen(true)}
            className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white px-5 py-2.5 rounded-2xl text-sm font-semibold flex items-center space-x-2 shadow-lg shadow-emerald-600/20 transition-all cursor-pointer"
          >
            <Plus size={18} />
            <span>เพิ่มอุปกรณ์ใหม่ (Advanced)</span>
          </button>
        </div>

        {/* Devices Table Card */}
        <div className="bg-white rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50 text-xs font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-4 px-6">ชื่ออุปกรณ์</th>
                  <th className="py-4 px-6">โปรโตคอล / การเชื่อมต่อ</th>
                  <th className="py-4 px-6">โซน / ห้อง</th>
                  <th className="py-4 px-6">MQTT Topic / ID</th>
                  <th className="py-4 px-6">สถานะเครือข่าย</th>
                  <th className="py-4 px-6 text-right">จัดการ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
                {devices.map(dev => (
                  <tr key={dev.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-4 px-6 font-semibold text-slate-900">{dev.name}</td>
                    <td className="py-4 px-6 text-emerald-600 font-semibold">{dev.protocol}</td>
                    <td className="py-4 px-6 text-slate-500">{dev.room}</td>
                    <td className="py-4 px-6 text-slate-400 font-mono text-xs">{dev.targetId}</td>
                    <td className="py-4 px-6">
                      <span className="inline-flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded-full font-medium bg-emerald-50 text-emerald-700">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                        <span>ออนไลน์</span>
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <button 
                        onClick={() => setDevices(devices.filter(d => d.id !== dev.id))}
                        className="p-2 hover:bg-rose-50 text-rose-500 rounded-xl transition-colors cursor-pointer"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal เพิ่มอุปกรณ์ขั้นสูง (Advanced Add Device) */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
            <div className="bg-white border border-slate-100 rounded-3xl w-full max-w-xl p-6 md:p-8 shadow-2xl relative overflow-y-auto max-h-[90vh]">
              
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                  <Cpu className="text-emerald-600" size={24} />
                  เพิ่มอุปกรณ์ฮาร์ดแวร์ใหม่ (Advanced Setup)
                </h3>
                <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-700 p-1 rounded-lg cursor-pointer">
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleAddDevice} className="space-y-5">
                
                {/* ชื่ออุปกรณ์ */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-2">ชื่ออุปกรณ์ (Device Name)</label>
                  <input 
                    type="text" 
                    required
                    placeholder="เช่น ปั๊มน้ำแปลง 2, เซนเซอร์วัดดิน"
                    value={formData.name}
                    onChange={e => setFormData({...formData, name: e.target.value})}
                    className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-emerald-600"
                  />
                </div>

                {/* Protocol & Gateway Selector */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-2">เลือกโปรโตคอลและการเชื่อมต่อ</label>
                  <select 
                    value={formData.protocol}
                    onChange={e => setFormData({...formData, protocol: e.target.value})}
                    className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-emerald-600"
                  >
                    <option value="ESP32 / ESP8266 (MQTT)">Wi-Fi / Direct MQTT (สำหรับ ESP32 / ESP8266)</option>
                    <option value="Zigbee Hub">Zigbee Gateway / Hub (สำหรับเซนเซอร์ Tuya Zigbee)</option>
                    <option value="Tuya Cloud API">Tuya Cloud / API Integration (สมาร์ทโฮมสำเร็จรูป)</option>
                  </select>
                </div>

                {/* Auto-Discovery & Pairing Mode */}
                <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-semibold text-slate-600 uppercase">สแกนหาอุปกรณ์อัตโนมัติ (Auto-Discovery)</span>
                    <button 
                      type="button" 
                      onClick={handleScan}
                      disabled={isScanning}
                      className="bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 text-emerald-700 px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer"
                    >
                      <RefreshCw size={14} className={isScanning ? "animate-spin" : ""} />
                      {isScanning ? "กำลังสแกนหาฮาร์ดแวร์..." : "สแกนในวงแลน / Pairing"}
                    </button>
                  </div>
                  {scanStatus === 'success' && (
                    <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 p-2.5 rounded-xl border border-emerald-200">
                      <CheckCircle2 size={16} />
                      พบอุปกรณ์ ESP32 ใหม่ในระบบ (MAC: 98:A4:BC:...)
                    </div>
                  )}
                </div>

                {/* Topic / MAC Address */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-2">MQTT Topic / Device ID / MAC Address</label>
                  <input 
                    type="text" 
                    placeholder="เช่น farm/zoneA/sensors หรือ MAC Address"
                    value={formData.targetId}
                    onChange={e => setFormData({...formData, targetId: e.target.value})}
                    className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-sm text-slate-900 font-mono focus:outline-none focus:border-emerald-600"
                  />
                </div>

                {/* Pin Mapping & Telemetry Threshold */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 uppercase mb-2">กำหนดพินฮาร์ดแวร์ (Pin Configuration)</label>
                    <input 
                      type="text" 
                      placeholder="เช่น Relay: GPIO 23"
                      value={formData.pinConfig}
                      onChange={e => setFormData({...formData, pinConfig: e.target.value})}
                      className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-emerald-600"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 uppercase mb-2">ค่าขีดจำกัดแจ้งเตือน (Telemetry Thresholds)</label>
                    <input 
                      type="text" 
                      placeholder="เช่น ความชื้น < 30%"
                      value={formData.threshold}
                      onChange={e => setFormData({...formData, threshold: e.target.value})}
                      className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-emerald-600"
                    />
                  </div>
                </div>

                {/* Submit Buttons */}
                <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
                  <button 
                    type="button" 
                    onClick={() => setIsModalOpen(false)}
                    className="px-5 py-2.5 rounded-2xl text-sm font-semibold bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors cursor-pointer"
                  >
                    ยกเลิก
                  </button>
                  <button 
                    type="submit"
                    className="px-6 py-2.5 rounded-2xl text-sm font-semibold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white shadow-lg shadow-emerald-600/20 transition-all cursor-pointer"
                  >
                    บันทึกและเชื่อมต่ออุปกรณ์
                  </button>
                </div>

              </form>

            </div>
          </div>
        )}

      </main>
    </div>
  );
}
