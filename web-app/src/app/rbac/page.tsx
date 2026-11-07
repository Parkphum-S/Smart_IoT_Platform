'use client';

import React, { useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { Users, Plus, Shield, X, Mail, Edit3, Trash2 } from 'lucide-react';

interface MemberItem {
  id: number;
  name: string;
  email: string;
  role: string;
  initials: string;
}

export default function RbacPage() {
  // จำลองสถานะผู้ใช้งานปัจจุบันเป็น Owner เพื่อให้สามารถทดสอบจัดการสิทธิ์ได้
  const [currentUserRole] = useState<'Owner' | 'Admin' | 'Viewer'>('Owner');

  const [members, setMembers] = useState<MemberItem[]>([
    { id: 1, name: 'Parkphum', email: 'parkphum@smartiot.com', role: 'Owner', initials: 'PP' },
    { id: 2, name: 'Agronomist Staff', email: 'staff.agri@smartiot.com', role: 'Admin', initials: 'AS' },
  ]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<MemberItem | null>(null);
  const [memberName, setMemberName] = useState('');
  const [memberEmail, setMemberEmail] = useState('');
  const [memberRole, setMemberRole] = useState('Admin');

  // ตรวจสอบสิทธิ์ว่าเป็น Owner เท่านั้น
  const isOwner = currentUserRole === 'Owner';

  const handleOpenCreate = () => {
    if (!isOwner) return;
    setEditingMember(null);
    setMemberName('');
    setMemberEmail('');
    setMemberRole('Admin');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (member: MemberItem) => {
    if (!isOwner) return;
    setEditingMember(member);
    setMemberName(member.name);
    setMemberEmail(member.email);
    setMemberRole(member.role);
    setIsModalOpen(true);
  };

  const handleSaveMember = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isOwner || !memberName.trim() || !memberEmail.trim()) return;

    const initials = memberName
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .substring(0, 2);

    if (editingMember) {
      setMembers(
        members.map((m) =>
          m.id === editingMember.id
            ? { ...m, name: memberName.trim(), email: memberEmail.trim(), role: memberRole, initials: initials || 'US' }
            : m
        )
      );
    } else {
      const newMember: MemberItem = {
        id: Date.now(),
        name: memberName.trim(),
        email: memberEmail.trim(),
        role: memberRole,
        initials: initials || 'US',
      };
      setMembers([newMember, ...members]);
    }

    setIsModalOpen(false);
  };

  const handleDelete = (id: number) => {
    if (!isOwner) return;
    if (confirm('คุณต้องการลบสิทธิ์สมาชิกนี้ใช่หรือไม่?')) {
      setMembers(members.filter((m) => m.id !== id));
    }
  };

  return (
    <AppLayout title="จัดการสมาชิก (RBAC)">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-800 tracking-tight">
            จัดการสมาชิกและสิทธิ์การใช้งาน (RBAC)
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            ควบคุมสิทธิ์การเข้าถึงระบบของผู้ใช้งานในฟาร์ม (สถานะปัจจุบันของคุณ: {currentUserRole} {isOwner ? '- มีสิทธิ์จัดการสูงสุด' : ''})
          </p>
        </div>

        {/* แสดงปุ่มเพิ่มสมาชิกใหม่เฉพาะระดับ Owner เท่านั้น */}
        {isOwner && (
          <button
            onClick={handleOpenCreate}
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-2xl text-xs font-bold shadow-sm transition-colors flex items-center justify-center gap-2 self-start sm:self-auto shrink-0 cursor-pointer"
          >
            <Plus size={16} />
            เพิ่มสมาชิกใหม่
          </button>
        )}
      </div>

      <div className="bg-white rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Users size={18} />
            </div>
            <h2 className="text-sm font-bold text-slate-800">รายชื่อผู้มีสิทธิ์ใช้งานแปลงเกษตร</h2>
          </div>
          <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-xl">
            ทั้งหมด {members.length} บัญชี
          </span>
        </div>

        <div className="divide-y divide-slate-100">
          {members.map((member) => (
            <div
              key={member.id}
              className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center shrink-0">
                  {member.initials}
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-800">{member.name}</h3>
                  <p className="text-[11px] text-slate-400">{member.email}</p>
                </div>
              </div>
              <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                <span
                  className={`text-xs font-semibold px-3 py-1.5 rounded-xl flex items-center gap-1.5 ${
                    member.role === 'Owner'
                      ? 'bg-emerald-50 text-emerald-700'
                      : member.role === 'Admin'
                      ? 'bg-blue-50 text-blue-700'
                      : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  <Shield size={14} /> {member.role === 'Owner' ? 'เจ้าของระบบ (Owner)' : member.role === 'Admin' ? 'ผู้ดูแลระบบ (Admin)' : 'ผู้เข้าชม (Viewer)'}
                </span>

                {/* แสดงปุ่มแก้ไขและลบเฉพาะเมื่อเป็น Owner เท่านั้น */}
                {isOwner && (
                  <div className="flex items-center gap-1 ml-2">
                    <button
                      onClick={() => handleOpenEdit(member)}
                      className="p-1.5 rounded-xl bg-slate-50 hover:bg-emerald-50 text-slate-600 hover:text-emerald-600 transition-colors cursor-pointer"
                      title="แก้ไขสมาชิก"
                    >
                      <Edit3 size={15} />
                    </button>
                    {member.role !== 'Owner' && (
                      <button
                        onClick={() => handleDelete(member.id)}
                        className="p-1.5 rounded-xl bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-rose-600 transition-colors cursor-pointer"
                        title="ลบสมาชิก"
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Modal เพิ่ม/แก้ไขสมาชิก (เฉพาะ Owner) */}
      {isModalOpen && isOwner && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-800">
                {editingMember ? 'แก้ไขข้อมูลสมาชิกและสิทธิ์' : 'เพิ่มสมาชิกใหม่ (Add New Member)'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveMember} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">ชื่อ-นามสกุล / นามเรียกขาน</label>
                <input
                  type="text"
                  value={memberName}
                  onChange={(e) => setMemberName(e.target.value)}
                  placeholder="เช่น สมชาย ใจดี"
                  required
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">อีเมลผู้ใช้งาน</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-400">
                    <Mail size={16} />
                  </span>
                  <input
                    type="email"
                    value={memberEmail}
                    onChange={(e) => setMemberEmail(e.target.value)}
                    placeholder="somchai@smartiot.com"
                    required
                    className="w-full pl-10 pr-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">กำหนดสิทธิ์การใช้งาน (Role)</label>
                <select
                  value={memberRole}
                  onChange={(e) => setMemberRole(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                >
                  <option value="Admin">ผู้ดูแลระบบ (Admin)</option>
                  <option value="Viewer">ผู้เข้าชม / ตรวจสอบ (Viewer)</option>
                  <option value="Owner">เจ้าของระบบ (Owner)</option>
                </select>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 py-3 rounded-2xl text-xs font-bold transition-colors cursor-pointer"
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white py-3 rounded-2xl text-xs font-bold shadow-md transition-colors cursor-pointer"
                >
                  {editingMember ? 'บันทึกการแก้ไข' : 'บันทึกเพิ่มสมาชิก'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
