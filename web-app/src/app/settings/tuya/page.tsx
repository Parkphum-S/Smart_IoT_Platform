'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Cloud, 
  Key, 
  ShieldCheck, 
  Save, 
  RefreshCw, 
  ArrowLeft,
  CheckCircle2
} from 'lucide-react';

export default function TuyaSettingsPage() {
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const [formData, setFormData] = useState({
    clientId: '',
    clientSecret: '',
    region: 'sg', // Singapore Region
    endpoint: 'https://openapi.tuyasg.com',
  });

  // โหลดข้อมูลการตั้งค่าเดิมจาก Backend เมื่อเปิดหน้าเว็บ
  useEffect(() => {
    async function fetchConfig() {
      try {
        const res = await fetch('/api/tuya/config');
        const json = await res.json();
        if (json.success && json.data) {
          setFormData({
            clientId: json.data.clientId || '',
            clientSecret: json.data.clientSecret || '',
            region: json.data.region || 'sg',
            endpoint: json.data.endpoint || 'https://openapi.tuyasg.com',
          });
        }
      } catch (error) {
        console.error('Failed to load Tuya config:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchConfig();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch('/api/tuya/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      const json = await res.json();
      if (res.ok && json.success) {
        alert(json.message || 'บันทึกการตั้งค่า Tuya Cloud API เรียบร้อยแล้ว!');
      } else {
        alert(json.detail || 'เกิดข้อผิดพลาดในการบันทึกข้อมูล');
      }
    } catch (error) {
      console.error('Error saving config:', error);
      alert('ไม่สามารถเชื่อมต่อกับ Server ได้');
    } finally {
      setSaving(false);
    }
  };

  const handleSyncDevices = async () => {
    setSyncing(true);
    try {
      const res = await fetch('/api/tuya/sync-devices', {
        method: 'POST',
      });
      const json = await res.json();
      if (res.ok && json.success) {
        alert(json.message || 'ซิงค์อุปกรณ์จาก Tuya Cloud สำเร็จ!');
      } else {
        alert(json.detail || 'ซิงค์อุปกรณ์ไม่สำเร็จ โปรดตรวจสอบ Credentials');
      }
    } catch (error) {
      console.error('Error syncing devices:', error);
      alert('เกิดข้อผิดพลาดในการเชื่อมต่อเครือข่าย');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto text-center text-slate-500 text-xs">
        กำลังโหลดข้อมูลการตั้งค่า...
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
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
              <Cloud className="text-blue-600" size={24} />
              ตั้งค่า Tuya Cloud API
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              จัดการข้อมูลการเชื่อมต่อ API ของ Tuya Cloud เพื่อดึงข้อมูลและควบคุมอุปกรณ์สมาร์ทโฮม
            </p>
          </div>

          <button
            type="button"
            onClick={handleSyncDevices}
            disabled={syncing}
            className="flex items-center gap-2 bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold px-4 py-2 rounded-xl text-xs transition-all border border-blue-100 disabled:opacity-50 w-fit"
          >
            <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'กำลังซิงค์ข้อมูล...' : 'ซิงค์อุปกรณ์จาก Tuya'}
          </button>
        </div>
      </div>

      {/* Main Settings Form */}
      <div className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm space-y-5">
        <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
          <Key size={18} className="text-slate-400" />
          ข้อมูลการรับรอง (API Credentials)
        </h2>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Access ID / Client ID
            </label>
            <input 
              type="text" 
              value={formData.clientId}
              onChange={(e) => setFormData({ ...formData, clientId: e.target.value })}
              placeholder="กรอก Tuya Client ID ของคุณ"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Access Secret / Client Secret
            </label>
            <input 
              type="password" 
              value={formData.clientSecret}
              onChange={(e) => setFormData({ ...formData, clientSecret: e.target.value })}
              placeholder="กรอก Tuya Client Secret ของคุณ"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Data Center Region
              </label>
              <select
                value={formData.region}
                onChange={(e) => {
                  const val = e.target.value;
                  let ep = 'https://openapi.tuyasg.com';
                  if (val === 'ay') ep = 'https://openapi.tuyaay.com';
                  else if (val === 'eu') ep = 'https://openapi.tuyaeu.com';
                  else if (val === 'us') ep = 'https://openapi.tuyaus.com';
                  else if (val === 'cn') ep = 'https://openapi.tuyacn.com';
                  else if (val === 'sg') ep = 'https://openapi.tuyasg.com';
                  setFormData({ ...formData, region: val, endpoint: ep });
                }}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
              >
                <option value="sg">Singapore Data Center (SG)</option>
                <option value="ay">Asia Data Center (AY)</option>
                <option value="eu">Europe Data Center (EU)</option>
                <option value="us">America Data Center (US)</option>
                <option value="cn">China Data Center (CN)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                API Endpoint URL
              </label>
              <input 
                type="text" 
                value={formData.endpoint}
                onChange={(e) => setFormData({ ...formData, endpoint: e.target.value})}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono"
              />
            </div>
          </div>

          <div className="pt-3 flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2.5 rounded-xl text-xs transition-all shadow-sm shadow-blue-600/20 disabled:opacity-50"
            >
              <Save size={16} />
              {saving ? 'กำลังบันทึก...' : 'บันทึกการตั้งค่า Tuya'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
