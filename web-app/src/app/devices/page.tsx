'use client';

import React, { useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { Cpu, Plus, X, Edit3, Trash2 } from 'lucide-react';

interface DeviceItem {
  id: string;
  name: string;
  type: string;
  room: string;
  status: string;
  state: string;
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<DeviceItem[]>([
    { id: 'DEV-01', name: 'ปั๊มน้ำหลัก (โซน A)', type: 'Water Pump', room: 'แปลงเกษตรโซน A', status: 'online', state: 'เปิดใช้งาน' },
    { id: 'DEV-02', name: 'ระบบพ่นหมอกโรงเรือน', type: 'Mist Sprayer', room: 'โรงเรือนเพาะชำ', status: 'online', state: 'ปิดใช้งาน' },
    { id: 'DEV-03', name: 'วาล์วน้ำหยด (โซน B)', type: 'Drip Valve', room: 'แปลงเกษตรโซน B', status: 'online', state: 'เปิดใช้งาน' },
  ]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDevice, setEditingDevice] = useState<DeviceItem | null>(null);
  const [deviceName, setDeviceName] = useState('');
  const [deviceType, setDeviceType] = useState('Water Pump');
  const [deviceRoom, setDeviceRoom] = useState('แปลงเกษตรโซน A');
  const [deviceState, setDeviceState] = useState('เปิดใช้งาน');

  const handleOpenCreate = () => {
    setEditingDevice(null);
    setDeviceName('');
    setDeviceType('Water Pump');
    setDeviceRoom('แปลงเกษตรโซน A');
    setDeviceState('เปิดใช้งาน');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (dev: DeviceItem) => {
    setEditingDevice(dev);
    setDeviceName(dev.name);
    setDeviceType(dev.type);
    setDeviceRoom(dev.room);
    setDeviceState(dev.state);
    setIsModalOpen(true);
  };

  const handleSaveDevice = (e: React.FormEvent) => {
    e.preventDefault();
    if (!deviceName.trim()) return;

    if (editingDevice) {
      setDevices(
        devices.map((d) =>
          d.id === editingDevice.id
            ? { ...d, name: deviceName.trim(), type: deviceType, room: deviceRoom, state: deviceState }
            : d
        )
      );
    } else {
      const newDevice: DeviceItem = {
        id: `DEV-0${devices.length + 1}`,
        name: deviceName.trim(),
        type: deviceType,
        room: deviceRoom,
        status: 'online',
        state: deviceState,
      };
      setDevices([newDevice, ...devices]);
    }

    setIsModalOpen(false);
  };

  const handleDelete = (id: string) => {
    if (confirm('คุณต้องการลบอุปกรณ์นี้ใช่หรือไม่?')) {
      setDevices(devices.filter((d) => d.id !== id));
    }
  };

  return (
    <AppLayout title="จัดการอุปกรณ์ (Devices)">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-800 tracking-tight">จัดการอุปกรณ์ทั้งหมด (Devices)</h1>
          <p className="text-xs text-slate-500 mt-1">เพิ่ม แก้ไข และตรวจสอบสถานะฮาร์ดแวร์ในฟาร์ม</p>
        </div>
        <button 
          onClick={handleOpenCreate}
          className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-2xl text-xs font-bold shadow-sm transition-colors flex items-center justify-center gap-2 self-start sm:self-auto shrink-0 cursor-pointer"
        >
          <Plus size={16} />
          เพิ่มอุปกรณ์ใหม่
        </button>
      </div>

      <div className="bg-white rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Cpu size={18} />
            </div>
            <h2 className="text-sm font-bold text-slate-800">รายการฮาร์ดแวร์ IoT ทั้งหมด</h2>
          </div>
          <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-xl">ทั้งหมด {devices.length} อุปกรณ์</span>
        </div>

        <div className="divide-y divide-slate-100">
          {devices.map((dev) => (
            <div key={dev.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-slate-100 text-slate-700 font-bold text-xs flex items-center justify-center shrink-0">
                  {dev.id}
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-800">{dev.name}</h3>
                  <p className="text-[11px] text-slate-400">{dev.type} • {dev.room}</p>
                </div>
              </div>
              <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                <span className="text-[11px] font-semibold bg-emerald-50 text-emerald-700 px-3 py-1 rounded-lg">ออนไลน์</span>
                <span className="text-xs font-bold text-slate-700">สถานะ: {dev.state}</span>
                <div className="flex items-center gap-1 ml-2">
                  <button 
                    onClick={() => handleOpenEdit(dev)}
                    className="p-1.5 rounded-xl bg-slate-50 hover:bg-emerald-50 text-slate-600 hover:text-emerald-600 transition-colors cursor-pointer"
                    title="แก้ไขอุปกรณ์"
                  >
                    <Edit3 size={15} />
                  </button>
                  <button 
                    onClick={() => handleDelete(dev.id)}
                    className="p-1.5 rounded-xl bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-rose-600 transition-colors cursor-pointer"
                    title="ลบอุปกรณ์"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Modal เพิ่ม/แก้ไขอุปกรณ์ */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-800">
                {editingDevice ? 'แก้ไขข้อมูลอุปกรณ์' : 'เพิ่มอุปกรณ์ฮาร์ดแวร์ใหม่ (Add Device)'}
              </h3>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveDevice} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">ชื่ออุปกรณ์</label>
                <input 
                  type="text" 
                  value={deviceName}
                  onChange={(e) => setDeviceName(e.target.value)}
                  placeholder="เช่น ปั๊มน้ำแปลง 2, เซนเซอร์วัดดิน"
                  required
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">ประเภทอุปกรณ์</label>
                <select 
                  value={deviceType}
                  onChange={(e) => setDeviceType(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                >
                  <option value="Water Pump">Water Pump (ปั๊มน้ำ)</option>
                  <option value="Mist Sprayer">Mist Sprayer (ระบบพ่นหมอก)</option>
                  <option value="Drip Valve">Drip Valve (วาล์วน้ำหยด)</option>
                  <option value="Sensor Node">Sensor Node (โหนดเซนเซอร์)</option>
                  <option value="CCTV Camera">CCTV Camera (กล้องวงจรปิด)</option>
                  <option value="Lighting Relay">Lighting Relay (สวิตช์ไฟ)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">ประจำโซน (Room / Zone)</label>
                <select 
                  value={deviceRoom}
                  onChange={(e) => setDeviceRoom(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                >
                  <option value="แปลงเกษตรโซน A">แปลงเกษตรโซน A</option>
                  <option value="โรงเรือนเพาะชำ">โรงเรือนเพาะชำ</option>
                  <option value="แปลงเกษตรโซน B">แปลงเกษตรโซน B</option>
                  <option value="โซนที่อาศัย">โซนที่อาศัย</option>
                  <option value="โซนปศุสัตว์">โซนปศุสัตว์</option>
                  <option value="โซนบ่อปลา">โซนบ่อปลา</option>
                  <option value="โซน CCTV">โซน CCTV</option>
                  <option value="โซนแสงสว่าง">โซนแสงสว่าง</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">สถานะการทำงาน</label>
                <select 
                  value={deviceState}
                  onChange={(e) => setDeviceState(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                >
                  <option value="เปิดใช้งาน">เปิดใช้งาน</option>
                  <option value="ปิดใช้งาน">ปิดใช้งาน</option>
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
                  {editingDevice ? 'บันทึกการแก้ไข' : 'บันทึกอุปกรณ์'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
