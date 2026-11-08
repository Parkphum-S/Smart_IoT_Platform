'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Sidebar } from '@/components/Sidebar';
import { 
  Settings as SettingsIcon, 
  Radio, 
  Cloud, 
  ShieldCheck, 
  Lock, 
  ChevronRight,
  Menu
} from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  
  // กำหนดสิทธิ์: 'Owner' | 'Admin' | 'User'
  const [userRole, setUserRole] = useState<'Owner' | 'Admin' | 'User'>('Admin');

  // ตรวจสอบสิทธิ์: อนุญาตเฉพาะ Owner และ Admin เท่านั้น
  const isAuthorized = userRole === 'Owner' || userRole === 'Admin';

  if (!isAuthorized) {
    return (
      <div className="flex h-screen bg-slate-50">
        <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-white p-8 rounded-3xl border border-slate-100 shadow-sm text-center space-y-4">
            <div className="w-12 h-12 bg-rose-50 text-rose-500 rounded-2xl flex items-center justify-center mx-auto">
              <Lock size={24} />
            </div>
            <h1 className="text-base font-bold text-slate-800">ไม่มีสิทธิ์เข้าถึงหน้านี้</h1>
            <p className="text-xs text-slate-500">
              หน้าการตั้งค่าระบบสงวนสิทธิ์เฉพาะ **เจ้าของระบบ (Owner)** และ **ผู้ดูแลระบบ (Admin)** เท่านั้น
            </p>
            <button
              onClick={() => router.push('/dashboard')}
              className="w-full bg-slate-900 text-white font-semibold py-2.5 rounded-xl text-xs transition-all hover:bg-slate-800"
            >
              กลับสู่หน้าแดชบอร์ด
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar เมนูด้านซ้าย */}
      <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Mobile Header Bar */}
        <div className="md:hidden flex items-center justify-between p-4 bg-white border-b border-slate-100">
          <button 
            onClick={() => setMobileOpen(true)}
            className="p-2 rounded-xl hover:bg-slate-100 text-slate-600"
          >
            <Menu size={20} />
          </button>
          <span className="text-xs font-bold text-slate-800">ตั้งค่าระบบ</span>
          <div className="w-8" />
        </div>

        <div className="p-6 max-w-4xl mx-auto w-full space-y-6">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-5">
            <div>
              <h1 className="text-xl font-black text-slate-800 flex items-center gap-2">
                <SettingsIcon className="text-emerald-600" size={24} />
                ตั้งค่าระบบ (Settings)
              </h1>
              <p className="text-xs text-slate-500 mt-1">
                จัดการการเชื่อมต่อฮาร์ดแวร์คลาวด์และโปรโตคอลอุปกรณ์ภายในฟาร์ม (จำกัดสิทธิ์เฉพาะ Owner และ Admin)
              </p>
            </div>
            <span className="text-xs font-semibold bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-xl border border-emerald-100 flex items-center gap-1.5 w-fit">
              <ShieldCheck size={14} />
              สิทธิ์ของคุณ: {userRole}
            </span>
          </div>

          {/* Settings Navigation Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Tuya Cloud Settings Link */}
            <Link 
              href="/settings/tuya"
              className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm hover:border-emerald-500/50 hover:shadow-md transition-all flex items-center justify-between group"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                  <Cloud size={24} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-800 group-hover:text-emerald-600 transition-colors">
                    ตั้งค่า Tuya Cloud API
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    จัดการ Client ID, Secret และการซิงค์อุปกรณ์ Tuya
                  </p>
                </div>
              </div>
              <ChevronRight size={18} className="text-slate-300 group-hover:text-emerald-600 group-hover:translate-x-1 transition-all" />
            </Link>

            {/* Zigbee2MQTT Settings Link */}
            <Link 
              href="/settings/zigbee"
              className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm hover:border-emerald-500/50 hover:shadow-md transition-all flex items-center justify-between group"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                  <Radio size={24} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-800 group-hover:text-emerald-600 transition-colors">
                    ตั้งค่า Zigbee2MQTT
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    จัดการ MQTT Broker, พอร์ตเครือข่าย และโหมดจับคู่
                  </p>
                </div>
              </div>
              <ChevronRight size={18} className="text-slate-300 group-hover:text-emerald-600 group-hover:translate-x-1 transition-all" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
