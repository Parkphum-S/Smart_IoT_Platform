'use client';

import React, { useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { Building2, Plus, MapPin, Shield, Cpu, X, Edit3, Trash2 } from 'lucide-react';

interface WorkspaceItem {
  id: number;
  name: string;
  location: string;
  devices: number;
  role: string;
}

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([
    { id: 1, name: 'ฟาร์มตัวอย่าง (Smart Agri-IoT)', location: 'นนทบุรี, ประเทศไทย', devices: 3, role: 'Owner' },
    { id: 2, name: 'โรงเรือนทดลองแปลง B', location: 'ปทุมธานี, ประเทศไทย', devices: 5, role: 'Admin' },
  ]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingWorkspace, setEditingWorkspace] = useState<WorkspaceItem | null>(null);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newLocation, setNewLocation] = useState('');

  const handleOpenCreate = () => {
    setEditingWorkspace(null);
    setNewWorkspaceName('');
    setNewLocation('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (ws: WorkspaceItem) => {
    setEditingWorkspace(ws);
    setNewWorkspaceName(ws.name);
    setNewLocation(ws.location);
    setIsModalOpen(true);
  };

  const handleSaveWorkspace = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;

    if (editingWorkspace) {
      // แก้ไขข้อมูลเดิม
      setWorkspaces(
        workspaces.map((item) =>
          item.id === editingWorkspace.id
            ? { ...item, name: newWorkspaceName.trim(), location: newLocation.trim() || 'ประเทศไทย' }
            : item
        )
      );
    } else {
      // สร้างใหม่
      const newItem: WorkspaceItem = {
        id: Date.now(),
        name: newWorkspaceName.trim(),
        location: newLocation.trim() || 'ประเทศไทย',
        devices: 0,
        role: 'Owner',
      };
      setWorkspaces([newItem, ...workspaces]);
    }

    setIsModalOpen(false);
  };

  const handleDelete = (id: number) => {
    if (confirm('คุณต้องการลบพื้นที่นี้ใช่หรือไม่?')) {
      setWorkspaces(workspaces.filter((item) => item.id !== id));
    }
  };

  return (
    <AppLayout title="จัดการพื้นที่ (Workspaces)">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-800 tracking-tight">
            จัดการพื้นที่โครงการ / ฟาร์ม (Workspaces)
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            เลือก เพิ่ม หรือแก้ไขพื้นที่การจัดการระบบ IoT ของคุณ
          </p>
        </div>
        <button 
          onClick={handleOpenCreate}
          className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-2xl text-xs font-bold shadow-sm transition-colors flex items-center justify-center gap-2 self-start sm:self-auto shrink-0 cursor-pointer"
        >
          <Plus size={16} />
          สร้าง Workspace ใหม่
        </button>
      </div>

      <div className="space-y-4">
        {workspaces.map((ws) => (
          <div key={ws.id} className="bg-white p-5 sm:p-6 rounded-3xl border border-slate-100 shadow-sm hover:border-emerald-200 transition-all">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                  <Building2 size={24} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-800">{ws.name}</h2>
                  <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                    <MapPin size={13} className="text-slate-400" />
                    {ws.location}
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold bg-slate-100 text-slate-600 px-3 py-1.5 rounded-xl flex items-center gap-1.5">
                    <Cpu size={14} className="text-slate-500" /> อุปกรณ์: {ws.devices} ตัว
                  </span>
                  <span className="text-xs font-semibold bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-xl flex items-center gap-1.5">
                    <Shield size={14} className="text-emerald-600" /> สิทธิ์: {ws.role}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button 
                    onClick={() => handleOpenEdit(ws)}
                    className="p-2 rounded-xl bg-slate-50 hover:bg-emerald-50 text-slate-600 hover:text-emerald-600 transition-colors cursor-pointer"
                    title="แก้ไข Workspace"
                  >
                    <Edit3 size={16} />
                  </button>
                  <button 
                    onClick={() => handleDelete(ws.id)}
                    className="p-2 rounded-xl bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-rose-600 transition-colors cursor-pointer"
                    title="ลบ Workspace"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modal สร้าง/แก้ไข Workspace */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-800">
                {editingWorkspace ? 'แก้ไขข้อมูล Workspace' : 'สร้างพื้นที่ฟาร์มใหม่ (Workspace)'}
              </h3>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveWorkspace} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">ชื่อโครงการ / ฟาร์ม</label>
                <input 
                  type="text" 
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  placeholder="เช่น ฟาร์มผักออร์แกนิก โซน 2"
                  required
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">พิกัด / สถานที่</label>
                <input 
                  type="text" 
                  value={newLocation}
                  onChange={(e) => setNewLocation(e.target.value)}
                  placeholder="เช่น เชียงใหม่, ประเทศไทย"
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                />
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
                  {editingWorkspace ? 'บันทึกการแก้ไข' : 'บันทึก Workspace'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
