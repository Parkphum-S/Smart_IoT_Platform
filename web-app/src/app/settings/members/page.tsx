'use client';

import React, { useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { Shield, UserPlus, Trash2 } from 'lucide-react';

export default function MembersPage() {
  const [members, setMembers] = useState([
    { id: 'usr-1', name: 'Parkphum', email: 'parkphum@smartiot.local', role: 'Owner' },
    { id: 'usr-2', name: 'Agronomist Somchai', email: 'somchai@farm.local', role: 'Admin' },
    { id: 'usr-3', name: 'Worker Bee', email: 'worker@farm.local', role: 'Operator' },
  ]);

  return (
    <div className="min-h-screen bg-slate-50/50 flex">
      <Sidebar />

      <main className="flex-1 p-10 overflow-y-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">จัดการสมาชิกและสิทธิ์ (RBAC)</h2>
            <p className="text-sm text-slate-500 mt-0.5">กำหนดบทบาทและสิทธิ์การเข้าถึงระบบภายในฟาร์ม</p>
          </div>
          <button className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-2xl text-sm font-semibold flex items-center space-x-2 shadow-lg shadow-emerald-600/20 transition-all">
            <UserPlus size={18} />
            <span>เชิญสมาชิกใหม่</span>
          </button>
        </div>

        <div className="bg-white rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <th className="p-5">ชื่อผู้ใช้งาน</th>
                <th className="p-5">อีเมล</th>
                <th className="p-5">บทบาท (Role)</th>
                <th className="p-5 text-right">จัดการ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {members.map(member => (
                <tr key={member.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="p-5 font-semibold text-slate-800 flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs">
                      {member.name.charAt(0)}
                    </div>
                    <span>{member.name}</span>
                  </td>
                  <td className="p-5 text-slate-500">{member.email}</td>
                  <td className="p-5">
                    <span className={`inline-flex items-center space-x-1 text-xs px-3 py-1 rounded-full font-medium ${
                      member.role === 'Owner' ? 'bg-purple-50 text-purple-700' :
                      member.role === 'Admin' ? 'bg-blue-50 text-blue-700' : 'bg-emerald-50 text-emerald-700'
                    }`}>
                      <Shield size={12} className="mr-1" />
                      <span>{member.role}</span>
                    </span>
                  </td>
                  <td className="p-5 text-right">
                    {member.role !== 'Owner' && (
                      <button className="p-2 hover:bg-rose-50 text-rose-500 rounded-xl transition-colors">
                        <Trash2 size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
