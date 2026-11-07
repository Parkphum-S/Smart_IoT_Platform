'use client';

import React from 'react';
import { AppLayout } from '@/components/AppLayout';
import { Activity, ShieldCheck } from 'lucide-react';

export default function DiagnosticsPage() {
  return (
    <AppLayout title="สถานะอุปกรณ์ (Diagnostics)">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-800 tracking-tight">สถานะสุขภาพอุปกรณ์ (Diagnostics)</h1>
          <p className="text-xs text-slate-500 mt-1">ตรวจสอบความสมบูรณ์และการเชื่อมต่อเครือข่ายของเซนเซอร์</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-bold text-slate-400">ระบบเครือข่ายเซนเซอร์</span>
            <div className="text-lg font-black text-slate-800 mt-1">เชื่อมต่อสมบูรณ์ (MQTT Broker)</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <ShieldCheck size={24} />
          </div>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-bold text-slate-400">ความสมบูรณ์ฮาร์ดแวร์</span>
            <div className="text-lg font-black text-emerald-600 mt-1">ปกติ 100% (ไม่มีข้อผิดพลาด)</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Activity size={24} />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-6">
        <h2 className="text-sm font-bold text-slate-800 mb-4">บันทึกผลการวินิจฉัยอุปกรณ์ล่าสุด</h2>
        <div className="space-y-3">
          <div className="p-4 rounded-2xl bg-slate-50/70 border border-slate-100 flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-700">Node-ESP32-ZoneA (ปั๊มน้ำหลัก)</span>
            <span className="bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded-lg font-semibold">Ping: 14ms (Normal)</span>
          </div>
          <div className="p-4 rounded-2xl bg-slate-50/70 border border-slate-100 flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-700">Node-ESP32-Greenhouse (พ่นหมอก)</span>
            <span className="bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded-lg font-semibold">Ping: 18ms (Normal)</span>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
