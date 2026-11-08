'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { 
  Radio, 
  Server, 
  Cpu, 
  Save,
  Activity,
  ArrowLeft,
  Sliders
} from 'lucide-react';

export default function ZigbeeSettingsPage() {
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState({
    connected: true,
    version: '1.35.3',
    devicesCount: 12
  });

  const [formData, setFormData] = useState({
    brokerUrl: 'mqtt://localhost:1883',
    port: '8080',
    baseTopic: 'zigbee2mqtt',
    panId: '0x1A2B',
    channel: '11',
    permitJoin: false,
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      alert('บันทึกการตั้งค่า Zigbee2MQTT เรียบร้อยแล้ว!');
    }, 800);
  };

  const handleTogglePermitJoin = () => {
    setFormData(prev => ({ ...prev, permitJoin: !prev.permitJoin }));
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Back Button & Header */}
      <div className="space-y-4 border-b border-slate-100 pb-5">
        <Link 
          href="/settings"
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-emerald-600 transition-colors bg-white px-3 py-1.5 rounded-xl border border-slate-100 shadow-sm w-fit"
        >
          <ArrowLeft size={16} />
          กลับสู่หน้าตั้งค่าระบบ
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-black text-slate-800 flex items-center gap-2">
              <Radio className="text-emerald-600" size={24} />
              ตั้งค่า Zigbee2MQTT
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              จัดการการเชื่อมต่อ MQTT Broker, พอร์ตเครือข่าย และสถานะการอนุญาตเชื่อมต่ออุปกรณ์ Zigbee
            </p>
          </div>
          
          <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-2xl border border-slate-100 shadow-sm">
            <div className="flex items-center gap-2">
              {status.connected ? (
                <span className="flex h-2.5 w-2.5 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                </span>
              ) : (
                <span className="h-2.5 w-2.5 rounded-full bg-rose-500"></span>
              )}
              <span className="text-xs font-semibold text-slate-700">
                {status.connected ? 'เชื่อมต่อ Zigbee2MQTT แล้ว' : 'ตัดการเชื่อมต่อ'}
              </span>
            </div>
            <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-lg font-mono">
              v{status.version}
            </span>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm space-y-5">
            <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <Server size={18} className="text-slate-400" />
              การตั้งค่า Broker & พอร์ตเครือข่าย
            </h2>

            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">MQTT Broker URL</label>
                <input 
                  type="text" 
                  value={formData.brokerUrl}
                  onChange={(e) => setFormData({ ...formData, brokerUrl: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">Zigbee2MQTT Web UI Port</label>
                  <input 
                    type="text" 
                    value={formData.port}
                    onChange={(e) => setFormData({ ...formData, port: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">Base Topic</label>
                  <input 
                    type="text" 
                    value={formData.baseTopic}
                    onChange={(e) => setFormData({ ...formData, baseTopic: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="pt-3 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-5 py-2.5 rounded-xl text-xs transition-all shadow-sm shadow-emerald-600/20 disabled:opacity-50"
                >
                  <Save size={16} />
                  {saving ? 'กำลังบันทึก...' : 'บันทึกการตั้งค่า'}
                </button>
              </div>
            </form>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <Sliders size={16} className="text-emerald-600" />
              โหมดจับคู่อุปกรณ์ (Permit Join)
            </h3>
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs font-semibold text-slate-700">
                {formData.permitJoin ? 'เปิดรับอุปกรณ์ใหม่อยู่' : 'ปิดการรับอุปกรณ์'}
              </span>
              <button
                type="button"
                onClick={handleTogglePermitJoin}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  formData.permitJoin ? 'bg-emerald-600' : 'bg-slate-200'
                }`}
              >
                <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${formData.permitJoin ? 'translate-x-5' : 'translate-x-0'}`} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
