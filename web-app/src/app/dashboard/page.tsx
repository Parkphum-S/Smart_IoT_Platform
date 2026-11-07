'use client';

import React, { useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { 
  Building2, 
  Grid, 
  Cpu, 
  Activity, 
  Thermometer, 
  Droplets, 
  Gauge, 
  Zap, 
  Video, 
  Waves,
  ChevronDown,
  CloudSun,
  Wind,
  Compass,
  Calculator
} from 'lucide-react';

interface ZoneData {
  id: number;
  name: string;
  typeLabel: string;
  workspace: string;
  devicesCount: number;
  rawTemp: number; // อุณหภูมิสำหรับคำนวณ VPD
  rawHumidity: number; // ความชื้นสำหรับคำนวณ VPD
  metrics: {
    soilMoisture?: string;
    npk?: string; // ผู้ใช้กรอก
    ph?: string; // ผู้ใช้กรอก
    oxygen?: string;
    relayStatus?: string;
    cctvActive?: boolean;
  };
}

const ZONES_DATA: ZoneData[] = [
  {
    id: 1,
    name: 'แปลงเกษตรโซน A',
    typeLabel: 'โซนพืชสวน',
    workspace: 'ฟาร์มตัวอย่าง',
    devicesCount: 2,
    rawTemp: 32.5,
    rawHumidity: 68,
    metrics: {
      soilMoisture: '45 %',
      npk: 'N: 40, P: 25, K: 60 mg/kg (บันทึกโดย: แอดมิน)',
      ph: '6.5 (บันทึกจากการตรวจวัดดิน)',
      relayStatus: 'เปิดใช้งาน (ปั๊มน้ำ/วาล์วหลัก)',
    }
  },
  {
    id: 2,
    name: 'โรงเรือนเพาะชำ',
    typeLabel: 'โซนไม้ดอก',
    workspace: 'ฟาร์มตัวอย่าง',
    devicesCount: 1,
    rawTemp: 29.0,
    rawHumidity: 75,
    metrics: {
      soilMoisture: '60 %',
      npk: 'N: 35, P: 30, K: 50 mg/kg (บันทึกโดย: แอดมิน)',
      ph: '6.8 (บันทึกจากการตรวจวัดดิน)',
      relayStatus: 'ปิดใช้งาน (ระบบพ่นหมอก)',
    }
  },
  {
    id: 3,
    name: 'บ่อเลี้ยงปลาโซน 1',
    typeLabel: 'โซนบ่อปลา',
    workspace: 'ฟาร์มตัวอย่าง',
    devicesCount: 2,
    rawTemp: 27.4,
    rawHumidity: 82,
    metrics: {
      ph: '7.2 (บันทึกค่า pH น้ำ)',
      oxygen: '6.8 mg/L (ออกซิเจน)',
      relayStatus: 'เปิดใช้งาน (เครื่องเติมอากาศ)',
    }
  },
  {
    id: 4,
    name: 'โซนรักษาความปลอดภัย',
    typeLabel: 'โซน CCTV',
    workspace: 'ฟาร์มตัวอย่าง',
    devicesCount: 3,
    rawTemp: 30.0,
    rawHumidity: 70,
    metrics: {
      cctvActive: true,
      relayStatus: 'ออนไลน์ (บันทึกภาพตลอด 24 ชม.)',
    }
  },
];

export default function DashboardPage() {
  const [selectedZoneId, setSelectedZoneId] = useState<number>(ZONES_DATA[0].id);
  const currentZone = ZONES_DATA.find((z) => z.id === selectedZoneId) || ZONES_DATA[0];

  // ฟังก์ชันคำนวณค่า VPD (Vapor Pressure Deficit) จาก อุณหภูมิ (°C) และความชื้นสัมพัทธ์ (%)
  const calculateVPD = (temp: number, humidity: number) => {
    // 1. คำนวณ Saturated Vapor Pressure (SVP) เป็น kPa
    const svp = 0.61078 * Math.exp((17.27 * temp) / (temp + 237.3));
    // 2. คำนวณ Actual Vapor Pressure (AVP)
    const avp = svp * (humidity / 100);
    // 3. VPD = SVP - AVP
    const vpd = svp - avp;
    return vpd.toFixed(2);
  };

  const calculatedVPD = calculateVPD(currentZone.rawTemp, currentZone.rawHumidity);

  return (
    <AppLayout title="แดชบอร์ดภาพรวม">
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-black text-slate-800 tracking-tight">
          แดชบอร์ดภาพรวมแปลงเกษตร (Dashboard)
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          ระบบพยากรณ์อากาศภายนอก คำนวณค่า VPD อัตโนมัติจากเซนเซอร์ และข้อมูล NPK/pH จากการบันทึกของผู้ใช้
        </p>
      </div>

      {/* OpenWeather API Widget */}
      <div className="bg-gradient-to-br from-emerald-500 via-emerald-600 to-teal-600 text-white p-6 sm:p-7 rounded-3xl shadow-sm mb-8 relative overflow-hidden border border-emerald-400/30">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="flex items-start sm:items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center shrink-0 border border-white/30 shadow-inner">
              <CloudSun size={30} className="text-white animate-pulse" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className="text-[10px] font-extrabold bg-white/25 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                  OpenWeather API
                </span>
                <span className="text-xs text-emerald-100 flex items-center gap-1 font-semibold">
                  <Compass size={12} /> นนทบุรี, ประเทศไทย
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight">31°C • มีเมฆบางส่วน</h2>
              <p className="text-xs text-emerald-50 mt-0.5 font-medium">
                ความรู้สึกเหมือน 34°C • เหมาะแก่การเปิดระบบพ่นหมอกช่วงบ่าย
              </p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 bg-black/10 backdrop-blur-md p-3 rounded-2xl border border-white/20 text-center shrink-0">
            <div className="px-2">
              <p className="text-[10px] text-emerald-100 font-bold">ความชื้นอากาศ</p>
              <p className="text-xs sm:text-sm font-black mt-0.5 flex items-center justify-center gap-1">
                <Droplets size={13} className="text-emerald-200" /> 65%
              </p>
            </div>
            <div className="border-x border-white/20 px-2">
              <p className="text-[10px] text-emerald-100 font-bold">ความเร็วลม</p>
              <p className="text-xs sm:text-sm font-black mt-0.5 flex items-center justify-center gap-1">
                <Wind size={13} className="text-emerald-200" /> 4.2 m/s
              </p>
            </div>
            <div className="px-2">
              <p className="text-[10px] text-emerald-100 font-bold">ดัชนี UV</p>
              <p className="text-xs sm:text-sm font-black mt-0.5 text-amber-200">ปานกลาง (5)</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <Building2 size={24} />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-semibold">พื้นที่ทั้งหมด</p>
            <h3 className="text-lg font-black text-slate-800 mt-0.5">2 โครงการ</h3>
          </div>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <Grid size={24} />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-semibold">โซนทั้งหมดในระบบ</p>
            <h3 className="text-lg font-black text-slate-800 mt-0.5">{ZONES_DATA.length} โซน</h3>
          </div>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <Cpu size={24} />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-semibold">อุปกรณ์โซนนี้ทำงานอยู่</p>
            <h3 className="text-lg font-black text-slate-800 mt-0.5">{currentZone.devicesCount} ตัว (ออนไลน์)</h3>
          </div>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <Activity size={24} />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-semibold">สถานะระบบเซนเซอร์</p>
            <h3 className="text-lg font-black text-emerald-600 mt-0.5">ปกติ / Active</h3>
          </div>
        </div>
      </div>

      {/* ส่วนแสดงข้อมูลโซนและเลือกโซน */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-100 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 mb-6 border-b border-slate-100 gap-4">
          <div>
            <span className="text-xs font-bold bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-xl">
              {currentZone.typeLabel}
            </span>
            <h2 className="text-lg sm:text-xl font-black text-slate-800 mt-2">
              รายงานสถานะเซนเซอร์: {currentZone.name}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">พื้นที่ (Workspace): {currentZone.workspace}</p>
          </div>

          <div className="relative min-w-[260px]">
            <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
              เลือกโซนเพื่อดูข้อมูล
            </label>
            <select
              value={selectedZoneId}
              onChange={(e) => setSelectedZoneId(Number(e.target.value))}
              className="w-full appearance-none bg-slate-50 border border-slate-200 hover:border-emerald-500 text-slate-800 text-xs font-bold px-4 py-3 pr-10 rounded-2xl shadow-sm focus:outline-none focus:border-emerald-600 cursor-pointer transition-colors"
            >
              {ZONES_DATA.map((zone) => (
                <option key={zone.id} value={zone.id}>
                  📍 {zone.name} ({zone.typeLabel})
                </option>
              ))}
            </select>
            <span className="absolute right-3 top-8 flex items-center pointer-events-none text-slate-400">
              <ChevronDown size={16} />
            </span>
          </div>
        </div>

        {/* Grid แสดงค่าเซนเซอร์และค่าคำนวณ VPD */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
              <Thermometer size={16} className="text-rose-500" /> อุณหภูมิ (จากเซนเซอร์)
            </div>
            <p className="text-lg font-black text-slate-800">{currentZone.rawTemp} °C</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
              <Droplets size={16} className="text-blue-500" /> ความชื้นในอากาศ (จากเซนเซอร์)
            </div>
            <p className="text-lg font-black text-slate-800">{currentZone.rawHumidity} %</p>
          </div>

          {/* ค่า VPD คำนวณอัตโนมัติจากเซนเซอร์ */}
          <div className="p-4 rounded-2xl bg-emerald-50/60 border border-emerald-100">
            <div className="flex items-center gap-2 text-emerald-800 text-xs mb-1 font-bold">
              <Calculator size={16} className="text-emerald-600" /> ค่า VPD (คำนวณจากเซนเซอร์)
            </div>
            <p className="text-lg font-black text-emerald-900">{calculatedVPD} kPa</p>
            <p className="text-[10px] text-emerald-700 mt-0.5">สถานะการคายน้ำพืช: เหมาะสม (Optimal)</p>
          </div>

          {currentZone.metrics.soilMoisture && (
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
              <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
                <Droplets size={16} className="text-emerald-600" /> ความชื้นในดิน
              </div>
              <p className="text-lg font-black text-slate-800">{currentZone.metrics.soilMoisture}</p>
            </div>
          )}

          {/* ค่า pH (ผู้ใช้กรอก) */}
          {currentZone.metrics.ph && (
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
              <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
                <Gauge size={16} className="text-amber-500" /> ค่า pH (ข้อมูลผู้ใช้กรอก)
              </div>
              <p className="text-sm font-bold text-slate-800">{currentZone.metrics.ph}</p>
            </div>
          )}

          {currentZone.metrics.oxygen && (
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
              <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
                <Waves size={16} className="text-cyan-500" /> ค่าออกซิเจนในน้ำ
              </div>
              <p className="text-lg font-black text-slate-800">{currentZone.metrics.oxygen}</p>
            </div>
          )}
        </div>

        {/* NPK ค่าธาตุอาหาร (ผู้ใช้กรอก) */}
        {currentZone.metrics.npk && (
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 mb-4">
            <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
              <Gauge size={16} className="text-emerald-600" /> ค่าธาตุอาหาร NPK ในดิน (ข้อมูลผู้ใช้กรอก)
            </div>
            <p className="text-sm font-bold text-slate-800">{currentZone.metrics.npk}</p>
          </div>
        )}

        {/* สถานะรีเลย์ */}
        {currentZone.metrics.relayStatus && (
          <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-100 mb-4">
            <div className="flex items-center gap-2 text-emerald-800 text-xs font-bold mb-1">
              <Zap size={16} className="text-emerald-600" /> สถานะรีเลย์ / อุปกรณ์ควบคุม
            </div>
            <p className="text-xs font-semibold text-emerald-900">{currentZone.metrics.relayStatus}</p>
          </div>
        )}

        {/* โซน CCTV */}
        {currentZone.metrics.cctvActive && (
          <div className="p-6 rounded-2xl bg-slate-900 text-white flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Video size={24} className="text-emerald-400 animate-pulse shrink-0" />
              <div>
                <p className="text-xs font-bold">กล้องวงจรปิด (CCTV Live Stream)</p>
                <p className="text-[11px] text-slate-400">สัญญาณภาพความละเอียดสูง 1080p จากแปลงเกษตร</p>
              </div>
            </div>
            <span className="text-xs bg-emerald-600 text-white px-3 py-1.5 rounded-xl font-bold">
              ● กำลังสตรีมมิ่ง
            </span>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
