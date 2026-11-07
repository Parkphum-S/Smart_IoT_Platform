'use client';

import React, { useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { GitBranch, Plus, X, ArrowRight, Edit3, Trash2, Mail } from 'lucide-react';

interface AutomationItem {
  id: number;
  name: string;
  condition: string;
  action: string;
  status: string;
}

const TRIGGER_TYPES = [
  { id: 'temp', label: 'อุณหภูมิ (°C)' },
  { id: 'soil_moisture', label: 'ความชื้นในดิน (%)' },
  { id: 'soil_ph', label: 'ค่า pH ดิน' },
  { id: 'schedule', label: 'ตั้งเวลา (Schedule)' },
  { id: 'motion', label: 'ตรวจพบการเคลื่อนไหว (CCTV / Security)' },
];

const TARGET_DEVICES = [
  'ปั๊มน้ำหลัก (โซน A)',
  'ระบบพ่นหมอกโรงเรือน',
  'วาล์วน้ำหยด (โซน B)',
  'ระบบไฟแสงสว่าง (โซนแสงสว่าง)',
  'ระบบแจ้งเตือนผ่านอีเมล (Email)',
  'ไซเรนแจ้งเตือนความปลอดภัย',
];

const DEVICE_ACTIONS = [
  'เปิดใช้งาน (Turn ON)',
  'ปิดใช้งาน (Turn OFF)',
  'ส่งการแจ้งเตือน (Send Alert)',
];

export default function AutomationsPage() {
  const [automations, setAutomations] = useState<AutomationItem[]>([
    {
      id: 1,
      name: 'รดน้ำแปลงโซน A อัตโนมัติ',
      condition: 'ตั้งเวลา: 06:00 น.',
      action: 'เปิดใช้งาน (Turn ON) → ปั๊มน้ำหลัก (โซน A)',
      status: 'เปิดใช้งาน',
    },
    {
      id: 2,
      name: 'พ่นหมอกลดความร้อน',
      condition: 'อุณหภูมิ > 35°C',
      action: 'เปิดใช้งาน (Turn ON) → ระบบพ่นหมอกโรงเรือน',
      status: 'ปิดอยู่',
    },
  ]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAuto, setEditingAuto] = useState<AutomationItem | null>(null);
  const [ruleName, setRuleName] = useState('');
  const [triggerType, setTriggerType] = useState('temp');
  const [operator, setOperator] = useState('>');
  const [thresholdValue, setThresholdValue] = useState('35');
  const [phMin, setPhMin] = useState('5.5');
  const [phMax, setPhMax] = useState('7.5');
  const [scheduleTime, setScheduleTime] = useState('06:00');
  const [targetDevice, setTargetDevice] = useState(TARGET_DEVICES[0]);
  const [deviceAction, setDeviceAction] = useState(DEVICE_ACTIONS[0]);
  const [recipientEmail, setRecipientEmail] = useState('parkphum@smartiot.com');
  const [ruleStatus, setRuleStatus] = useState('เปิดใช้งาน');

  const handleOpenCreate = () => {
    setEditingAuto(null);
    setRuleName('');
    setTriggerType('temp');
    setOperator('>');
    setThresholdValue('35');
    setScheduleTime('06:00');
    setTargetDevice(TARGET_DEVICES[0]);
    setDeviceAction(DEVICE_ACTIONS[0]);
    setRecipientEmail('parkphum@smartiot.com');
    setRuleStatus('เปิดใช้งาน');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (auto: AutomationItem) => {
    setEditingAuto(auto);
    setRuleName(auto.name);
    setRuleStatus(auto.status);
    setIsModalOpen(true);
  };

  const handleTriggerTypeChange = (type: string) => {
    setTriggerType(type);
    if (type === 'temp') {
      setOperator('>');
      setThresholdValue('35');
    } else if (type === 'soil_moisture') {
      setOperator('<');
      setThresholdValue('30');
    } else if (type === 'soil_ph') {
      setOperator('outside');
      setPhMin('5.5');
      setPhMax('7.5');
    }
  };

  const buildConditionText = () => {
    switch (triggerType) {
      case 'temp':
        return `อุณหภูมิ ${operator} ${thresholdValue}°C`;
      case 'soil_moisture':
        return `ความชื้นในดิน ${operator} ${thresholdValue}%`;
      case 'soil_ph':
        if (operator === 'outside') {
          return `ค่า pH ดิน < ${phMin} หรือ > ${phMax}`;
        }
        return `ค่า pH ดิน ${operator} ${thresholdValue}`;
      case 'schedule':
        return `ตั้งเวลา: ${scheduleTime} น.`;
      case 'motion':
        return 'ตรวจพบการเคลื่อนไหว (CCTV / Security)';
      default:
        return 'เงื่อนไขกำหนดเอง';
    }
  };

  const handleSaveAutomation = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleName.trim()) return;

    const conditionText = buildConditionText();
    const isEmailAlert = targetDevice.includes('อีเมล (Email)');
    const actionText = isEmailAlert 
      ? `${deviceAction} → ส่งอีเมลไปที่ (${recipientEmail || 'owner@smartiot.com'})`
      : `${deviceAction} → ${targetDevice}`;

    if (editingAuto) {
      setAutomations(
        automations.map((item) =>
          item.id === editingAuto.id
            ? { ...item, name: ruleName.trim(), condition: conditionText, action: actionText, status: ruleStatus }
            : item
        )
      );
    } else {
      const newAuto: AutomationItem = {
        id: Date.now(),
        name: ruleName.trim(),
        condition: conditionText,
        action: actionText,
        status: ruleStatus,
      };
      setAutomations([newAuto, ...automations]);
    }

    setIsModalOpen(false);
  };

  const handleDelete = (id: number) => {
    if (confirm('คุณต้องการลบเงื่อนไขอัตโนมัตินี้ใช่หรือไม่?')) {
      setAutomations(automations.filter((item) => item.id !== id));
    }
  };

  const toggleStatus = (id: number) => {
    setAutomations(
      automations.map((item) =>
        item.id === id
          ? { ...item, status: item.status === 'เปิดใช้งาน' ? 'ปิดอยู่' : 'เปิดใช้งาน' }
          : item
      )
    );
  };

  return (
    <AppLayout title="ระบบอัตโนมัติ (Automations)">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-800 tracking-tight">
            ระบบอัตโนมัติ (Automations)
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            ตั้งค่า แก้ไขเงื่อนไขการทำงานและฉากอัตโนมัติในฟาร์ม
          </p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-2xl text-xs font-bold shadow-sm transition-colors flex items-center justify-center gap-2 self-start sm:self-auto shrink-0 cursor-pointer"
        >
          <Plus size={16} />
          สร้างเงื่อนไขใหม่
        </button>
      </div>

      <div className="space-y-3">
        {automations.map((auto) => (
          <div
            key={auto.id}
            className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4"
          >
            <div className="flex items-start sm:items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                <GitBranch size={20} />
              </div>
              <div>
                <h2 className="text-xs font-bold text-slate-800">{auto.name}</h2>
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500 mt-1">
                  <span className="bg-slate-100 text-slate-700 font-semibold px-2 py-0.5 rounded-lg">
                    ถ้า: {auto.condition}
                  </span>
                  <ArrowRight size={12} className="text-slate-400" />
                  <span className="bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded-lg">
                    สั่งงาน: {auto.action}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
              <button
                onClick={() => toggleStatus(auto.id)}
                className={`text-xs font-semibold px-3 py-1.5 rounded-xl cursor-pointer transition-colors ${
                  auto.status === 'เปิดใช้งาน'
                    ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {auto.status}
              </button>
              <div className="flex items-center gap-1 ml-2">
                <button 
                  onClick={() => handleOpenEdit(auto)}
                  className="p-1.5 rounded-xl bg-slate-50 hover:bg-emerald-50 text-slate-600 hover:text-emerald-600 transition-colors cursor-pointer"
                  title="แก้ไขเงื่อนไข"
                >
                  <Edit3 size={15} />
                </button>
                <button 
                  onClick={() => handleDelete(auto.id)}
                  className="p-1.5 rounded-xl bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-rose-600 transition-colors cursor-pointer"
                  title="ลบเงื่อนไข"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modal สร้าง/แก้ไขเงื่อนไข */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-800">
                {editingAuto ? 'แก้ไขเงื่อนไขอัตโนมัติ' : 'สร้างเงื่อนไขอัตโนมัติใหม่ (New Smart Rule)'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveAutomation} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  ชื่อกฎเงื่อนไข
                </label>
                <input
                  type="text"
                  value={ruleName}
                  onChange={(e) => setRuleName(e.target.value)}
                  placeholder="เช่น ควบคุมอุณหภูมิโรงเรือน"
                  required
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-3">
                <label className="block text-xs font-bold text-slate-700">
                  1. เงื่อนไขทริกเกอร์ (IF)
                </label>
                <select
                  value={triggerType}
                  onChange={(e) => handleTriggerTypeChange(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                >
                  {TRIGGER_TYPES.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.label}
                    </option>
                  ))}
                </select>

                {(triggerType === 'temp' || triggerType === 'soil_moisture') && (
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={operator}
                      onChange={(e) => setOperator(e.target.value)}
                      className="px-3 py-2.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                    >
                      <option value=">">มากกว่า (&gt;)</option>
                      <option value="<">น้อยกว่า (&lt;)</option>
                    </select>
                    <div className="relative">
                      <input
                        type="number"
                        step="0.1"
                        value={thresholdValue}
                        onChange={(e) => setThresholdValue(e.target.value)}
                        required
                        className="w-full px-3 py-2.5 pr-8 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] font-bold text-slate-400">
                        {triggerType === 'temp' ? '°C' : '%'}
                      </span>
                    </div>
                  </div>
                )}

                {triggerType === 'soil_ph' && (
                  <div className="space-y-2">
                    <select
                      value={operator}
                      onChange={(e) => setOperator(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                    >
                      <option value="outside">อยู่นอกช่วงปกติ (&lt; ต่ำสุด หรือ &gt; สูงสุด)</option>
                      <option value="<">น้อยกว่า (&lt;)</option>
                      <option value=">">มากกว่า (&gt;)</option>
                    </select>

                    {operator === 'outside' ? (
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <span className="block text-[10px] text-slate-500 mb-1">ต่ำกว่า (&lt;)</span>
                          <input
                            type="number"
                            step="0.1"
                            value={phMin}
                            onChange={(e) => setPhMin(e.target.value)}
                            required
                            className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                          />
                        </div>
                        <div>
                          <span className="block text-[10px] text-slate-500 mb-1">สูงกว่า (&gt;)</span>
                          <input
                            type="number"
                            step="0.1"
                            value={phMax}
                            onChange={(e) => setPhMax(e.target.value)}
                            required
                            className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                          />
                        </div>
                      </div>
                    ) : (
                      <input
                        type="number"
                        step="0.1"
                        value={thresholdValue}
                        onChange={(e) => setThresholdValue(e.target.value)}
                        placeholder="ระบุค่า pH"
                        required
                        className="w-full px-3 py-2.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                      />
                    )}
                  </div>
                )}

                {triggerType === 'schedule' && (
                  <div>
                    <span className="block text-[10px] text-slate-500 mb-1">ระบุเวลาทำงาน</span>
                    <input
                      type="time"
                      value={scheduleTime}
                      onChange={(e) => setScheduleTime(e.target.value)}
                      required
                      className="w-full px-3 py-2.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                    />
                  </div>
                )}

                {triggerType === 'motion' && (
                  <p className="text-[11px] text-slate-500">
                    ระบบจะทำงานทันทีเมื่อกล้อง CCTV หรือเซนเซอร์ตรวจจับความเคลื่อนไหวได้
                  </p>
                )}
              </div>

              <div className="p-4 rounded-2xl bg-emerald-50/60 border border-emerald-100 space-y-3">
                <label className="block text-xs font-bold text-emerald-900">
                  2. สั่งงานอุปกรณ์ (THEN)
                </label>
                <div>
                  <span className="block text-[10px] text-emerald-700 mb-1">เลือกอุปกรณ์ปลายทาง</span>
                  <select
                    value={targetDevice}
                    onChange={(e) => setTargetDevice(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-emerald-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                  >
                    {TARGET_DEVICES.map((dev, idx) => (
                      <option key={idx} value={dev}>
                        {dev}
                      </option>
                    ))}
                  </select>
                </div>

                {/* ช่องกรอกอีเมลจะแสดงขึ้นมาก็ต่อเมื่อเลือกอุปกรณ์ปลายทางเป็นระบบแจ้งเตือนผ่านอีเมล */}
                {targetDevice.includes('อีเมล (Email)') && (
                  <div>
                    <span className="block text-[10px] text-emerald-700 mb-1">ระบุอีเมลผู้รับแจ้งเตือน</span>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-400">
                        <Mail size={15} />
                      </span>
                      <input
                        type="email"
                        value={recipientEmail}
                        onChange={(e) => setRecipientEmail(e.target.value)}
                        placeholder="example@smartiot.com"
                        required
                        className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-white border border-emerald-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600"
                      />
                    </div>
                  </div>
                )}

                <div>
                  <span className="block text-[10px] text-emerald-700 mb-1">รูปแบบการสั่งงาน</span>
                  <select
                    value={deviceAction}
                    onChange={(e) => setDeviceAction(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-emerald-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                  >
                    {DEVICE_ACTIONS.map((act, idx) => (
                      <option key={idx} value={act}>
                        {act}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  สถานะเริ่มต้น
                </label>
                <select
                  value={ruleStatus}
                  onChange={(e) => setRuleStatus(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 cursor-pointer"
                >
                  <option value="เปิดใช้งาน">เปิดใช้งาน</option>
                  <option value="ปิดอยู่">ปิดอยู่</option>
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
                  {editingAuto ? 'บันทึกการแก้ไข' : 'บันทึกกฎอัตโนมัติ'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
