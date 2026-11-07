'use client';

import React, { useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { Grid, Plus, Cpu, Building2, X, Layers, Edit3, Trash2, Image as ImageIcon, Gauge } from 'lucide-react';

interface ZoneTypeConfig {
  id: string;
  label: string;
  metrics: string[];
}

const ZONE_TYPES: ZoneTypeConfig[] = [
  { id: 'residential', label: '1. โซนที่อาศัย', metrics: ['แสดงข้อมูลทุกประเภท'] },
  { id: 'horticulture', label: '2. โซนพืชสวน', metrics: ['อุณหภูมิ', 'ความชื้น(อากาศ)', 'ความชื้น(ดิน)', 'ค่า NPK', 'ค่า pH (ดิน)', 'ค่า VPD', 'สถานะรีเลย์'] },
  { id: 'field-crops', label: '3. โซนพืชไร่', metrics: ['อุณหภูมิ', 'ความชื้น(อากาศ)', 'ความชื้น(ดิน)', 'ค่า NPK', 'ค่า pH (ดิน)', 'ค่า VPD', 'สถานะรีเลย์'] },
  { id: 'forestry', label: '4. โซนไม้ป่า', metrics: ['อุณหภูมิ', 'ความชื้น(อากาศ)', 'ความชื้น(ดิน)', 'ค่า NPK', 'ค่า pH (ดิน)', 'ค่า VPD', 'สถานะรีเลย์'] },
  { id: 'flowers', label: '5. โซนไม้ดอก', metrics: ['อุณหภูมิ', 'ความชื้น(อากาศ)', 'ความชื้น(ดิน)', 'ค่า NPK', 'ค่า pH (ดิน)', 'ค่า VPD', 'สถานะรีเลย์'] },
  { id: 'livestock', label: '6. โซนปศุสัตว์', metrics: ['อุณหภูมิ', 'ความชื้น(อากาศ)', 'สถานะรีเลย์'] },
  { id: 'fish-pond', label: '7. โซนบ่อปลา', metrics: ['อุณหภูมิ', 'ความชื้น(อากาศ)', 'ค่า pH (น้ำ)', 'ค่าออกซิเจน (น้ำ)', 'สถานะรีเลย์'] },
  { id: 'cctv', label: '8. โซน CCTV', metrics: ['แสดงข้อมูล CCTV'] },
  { id: 'lighting', label: '9. โซนแสงสว่าง', metrics: ['สถานะรีเลย์'] },
];

interface RoomItem {
  id: number;
  name: string;
  zoneTypeId: string;
  workspace: string;
  devicesCount: number;
  image?: string;
  npkValue?: string;
  phValue?: string;
}

export default function RoomsPage() {
  const [rooms, setRooms] = useState<RoomItem[]>([
    { id: 1, name: 'แปลงเกษตรโซน A', zoneTypeId: 'horticulture', workspace: 'ฟาร์มตัวอย่าง', devicesCount: 2, image: '', npkValue: 'N: 40, P: 25, K: 60 mg/kg', phValue: '6.5' },
    { id: 2, name: 'โรงเรือนเพาะชำ', zoneTypeId: 'flowers', workspace: 'ฟาร์มตัวอย่าง', devicesCount: 1, image: '', npkValue: 'N: 35, P: 30, K: 50 mg/kg', phValue: '6.8' },
    { id: 3, name: 'บ่อเลี้ยงปลาโซน 1', zoneTypeId: 'fish-pond', workspace: 'ฟาร์มตัวอย่าง', devicesCount: 2, image: '', npkValue: '-', phValue: '7.2' },
  ]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<RoomItem | null>(null);
  const [newRoomName, setNewRoomName] = useState('');
  const [selectedZoneType, setSelectedZoneType] = useState('horticulture');
  const [workspaceName, setWorkspaceName] = useState('ฟาร์มตัวอย่าง');
  const [roomImage, setRoomImage] = useState('');
  const [inputNpk, setInputNpk] = useState('');
  const [inputPh, setInputPh] = useState('');

  const handleOpenCreate = () => {
    setEditingRoom(null);
    setNewRoomName('');
    setSelectedZoneType('horticulture');
    setWorkspaceName('ฟาร์มตัวอย่าง');
    setRoomImage('');
    setInputNpk('');
    setInputPh('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (room: RoomItem) => {
    setEditingRoom(room);
    setNewRoomName(room.name);
    setSelectedZoneType(room.zoneTypeId);
    setWorkspaceName(room.workspace);
    setRoomImage(room.image || '');
    setInputNpk(room.npkValue || '');
    setInputPh(room.phValue || '');
    setIsModalOpen(true);
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setRoomImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSaveRoom = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRoomName.trim()) return;

    if (editingRoom) {
      setRooms(
        rooms.map((r) =>
          r.id === editingRoom.id
            ? { 
                ...r, 
                name: newRoomName.trim(), 
                zoneTypeId: selectedZoneType, 
                workspace: workspaceName.trim() || 'ฟาร์มตัวอย่าง', 
                image: roomImage,
                npkValue: inputNpk.trim() || '-',
                phValue: inputPh.trim() || '-'
              }
            : r
        )
      );
    } else {
      const newRoom: RoomItem = {
        id: Date.now(),
        name: newRoomName.trim(),
        zoneTypeId: selectedZoneType,
        workspace: workspaceName.trim() || 'ฟาร์มตัวอย่าง',
        devicesCount: 0,
        image: roomImage,
        npkValue: inputNpk.trim() || '-',
        phValue: inputPh.trim() || '-'
      };
      setRooms([newRoom, ...rooms]);
    }

    setIsModalOpen(false);
  };

  const handleDelete = (id: number) => {
    if (confirm('คุณต้องการลบโซนนี้ใช่หรือไม่?')) {
      setRooms(rooms.filter((r) => r.id !== id));
    }
  };

  const getZoneConfig = (typeId: string) => {
    return ZONE_TYPES.find((z) => z.id === typeId) || ZONE_TYPES[0];
  };

  const activePreviewConfig = getZoneConfig(selectedZoneType);

  return (
    <AppLayout title="จัดการโซน (Rooms)">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-800 tracking-tight">
            จัดการโซนและห้อง (Rooms & Zones)
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            บันทึกค่า NPK, ค่า pH และจัดการข้อมูลโซนในฟาร์มของคุณ
          </p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-2xl text-xs font-bold shadow-sm transition-colors flex items-center justify-center gap-2 self-start sm:self-auto shrink-0 cursor-pointer"
        >
          <Plus size={16} />
          เพิ่มโซนใหม่
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {rooms.map((room) => {
          const config = getZoneConfig(room.zoneTypeId);
          return (
            <div
              key={room.id}
              className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm hover:border-emerald-200 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 overflow-hidden border border-emerald-100">
                      {room.image ? (
                        <img src={room.image} alt={room.name} className="w-full h-full object-cover" />
                      ) : (
                        <Grid size={22} />
                      )}
                    </div>
                    <div className="min-w-0">
                      <h2 className="text-sm font-bold text-slate-800 truncate">{room.name}</h2>
                      <p className="text-[11px] font-semibold text-emerald-700 mt-0.5 flex items-center gap-1">
                        <Layers size={12} className="shrink-0" /> {config.label}
                      </p>
                      <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                        <Building2 size={13} className="shrink-0" /> พื้นที่: {room.workspace}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button 
                      onClick={() => handleOpenEdit(room)}
                      className="p-1.5 rounded-xl bg-slate-50 hover:bg-emerald-50 text-slate-600 hover:text-emerald-600 transition-colors cursor-pointer"
                      title="แก้ไขโซน"
                    >
                      <Edit3 size={15} />
                    </button>
                    <button 
                      onClick={() => handleDelete(room.id)}
                      className="p-1.5 rounded-xl bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-rose-600 transition-colors cursor-pointer"
                      title="ลบโซน"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>

                {/* แสดงค่า NPK และ pH ที่ผู้ใช้กรอก */}
                <div className="mt-4 pt-3 border-t border-slate-50 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500 font-semibold flex items-center gap-1">
                      <Gauge size={13} className="text-emerald-600" /> ค่า NPK (ดิน):
                    </span>
                    <span className="font-bold text-slate-800">{room.npkValue || '-'}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500 font-semibold flex items-center gap-1">
                      <Gauge size={13} className="text-amber-500" /> ค่า pH:
                    </span>
                    <span className="font-bold text-slate-800">{room.phValue || '-'}</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-50 flex items-center justify-between text-xs">
                <span className="text-slate-500 flex items-center gap-1">
                  <Cpu size={14} className="text-emerald-600" /> จำนวนอุปกรณ์
                </span>
                <span className="font-bold text-slate-800 bg-slate-100 px-2.5 py-1 rounded-xl">
                  {room.devicesCount} ตัว
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal เพิ่ม/แก้ไขโซน พร้อมช่องกรอก NPK และ pH */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-800">
                {editingRoom ? 'แก้ไขข้อมูลโซน' : 'เพิ่มโซนใหม่ (Add New Zone)'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveRoom} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">รูปภาพ / ไอคอนประจำโซน</label>
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center overflow-hidden shrink-0">
                    {roomImage ? (
                      <img src={roomImage} alt="Preview" className="w-full h-full object-cover" />
                    ) : (
                      <ImageIcon size={24} className="text-slate-400" />
                    )}
                  </div>
                  <div className="flex-1">
                    <input 
                      type="file" 
                      accept="image/*"
                      onChange={handleImageChange}
                      className="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100 cursor-pointer"
                    />
                    <p className="text-[10px] text-slate-400 mt-1">รองรับไฟล์ PNG, JPG ขนาดไม่เกิน 2MB</p>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">ชื่อโซน</label>
                <input
                  type="text"
                  value={newRoomName}
                  onChange={(e) => setNewRoomName(e.target.value)}
                  placeholder="เช่น แปลงผักไฮโดรโปนิกส์ 1"
                  required
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">ประเภทโซนหลัก</label>
                <select
                  value={selectedZoneType}
                  onChange={(e) => setSelectedZoneType(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                >
                  {ZONE_TYPES.map((type) => (
                    <option key={type.id} value={type.id}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* ช่องกรอกข้อมูล NPK (ผู้ใช้กรอก) */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">ค่าธาตุอาหาร NPK ในดิน (ผู้ใช้กรอก)</label>
                <input
                  type="text"
                  value={inputNpk}
                  onChange={(e) => setInputNpk(e.target.value)}
                  placeholder="เช่น N: 40, P: 25, K: 60 mg/kg"
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                />
              </div>

              {/* ช่องกรอกข้อมูล pH (ผู้ใช้กรอก) */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">ค่าความเป็นกรด-ด่าง pH (ผู้ใช้กรอก)</label>
                <input
                  type="text"
                  value={inputPh}
                  onChange={(e) => setInputPh(e.target.value)}
                  placeholder="เช่น 6.5 หรือ 7.0"
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">พื้นที่ (Workspace)</label>
                <input
                  type="text"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  placeholder="เช่น ฟาร์มตัวอย่าง"
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
                  {editingRoom ? 'บันทึกการแก้ไข' : 'บันทึกโซนใหม่'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
