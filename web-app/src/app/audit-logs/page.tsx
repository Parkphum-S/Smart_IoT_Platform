'use client';

import React from 'react';
import { AppLayout } from '@/components/AppLayout';
import { ShieldAlert } from 'lucide-react';

export default function AuditLogsPage() {
  const logs = [
    { id: 1, user: 'Parkphum (Owner)', action: 'สั่งเปิดปั๊มน้ำหลัก (โซน A)', time: 'วันนี้, 19:32 น.', type: 'success' },
    { id: 2, user: 'System Automation', action: 'ระบบตั้งเวลารดน้ำอัตโนมัติทำงาน', time: 'วันนี้, 06:00 น.', type: 'info' },
    { id: 3, user: 'Agronomist Staff', action: 'แก้ไขกฎเงื่อนไขอุณหภูมิโรงเรือน', time: 'เมื่อวาน, 14:15 น.', type: 'warning' },
  ];

  return (
    <AppLayout title="ประวัติระบบ (Audit Logs)">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-800 tracking-tight">ประวัติการใช้งานระบบ (Audit Logs)</h1>
          <p className="text-xs text-slate-500 mt-1">ตรวจสอบประวัติการทำรายการและเหตุการณ์ความปลอดภัยในระบบ</p>
        </div>
      </div>

      <div className="bg-white rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <ShieldAlert size={18} />
          </div>
          <h2 className="text-sm font-bold text-slate-800">บันทึกเหตุการณ์และประวัติคำสั่งระบบ (System Logs)</h2>
        </div>

        <div className="divide-y divide-slate-100">
          {logs.map((log) => (
            <div key={log.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition-colors">
              <div>
                <h3 className="text-xs font-bold text-slate-800">{log.action}</h3>
                <p className="text-[11px] text-slate-400 mt-0.5">ผู้ทำรายการ: {log.user}</p>
              </div>
              <span className="text-[11px] font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-lg w-fit">
                {log.time}
              </span>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
