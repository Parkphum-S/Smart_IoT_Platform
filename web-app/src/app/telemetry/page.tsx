'use client';

import React, { useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { LineChart as LineChartIcon, CloudSun, Droplets, Wind, Grid } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

// ข้อมูลจำลองแยกตามแต่ละโซน
const telemetryDataByZone: Record<string, { name: string; temp: number; humidity: number; wind: string; chart: Array<{ time: string; temp: number; humidity: number }> }> = {
  'zone-a': {
    name: 'แปลงเกษตรโซน A',
    temp: 28.5,
    humidity: 78,
    wind: '1.84 m/s',
    chart: [
      { time: '00:00', temp: 24.5, humidity: 82 },
      { time: '03:00', temp: 23.8, humidity: 85 },
      { time: '06:00', temp: 25.0, humidity: 80 },
      { time: '09:00', temp: 27.2, humidity: 72 },
      { time: '12:00', temp: 30.5, humidity: 65 },
      { time: '15:00', temp: 29.8, humidity: 68 },
      { time: '18:00', temp: 27.0, humidity: 75 },
      { time: '21:00', temp: 25.5, humidity: 79 },
    ]
  },
  'greenhouse': {
    name: 'โรงเรือนเพาะชำ',
    temp: 31.2,
    humidity: 88,
    wind: '0.92 m/s',
    chart: [
      { time: '00:00', temp: 27.0, humidity: 90 },
      { time: '03:00', temp: 26.5, humidity: 92 },
      { time: '06:00', temp: 28.0, humidity: 89 },
      { time: '09:00', temp: 31.0, humidity: 82 },
      { time: '12:00', temp: 35.5, humidity: 75 },
      { time: '15:00', temp: 34.0, humidity: 78 },
      { time: '18:00', temp: 30.2, humidity: 85 },
      { time: '21:00', temp: 28.5, humidity: 88 },
    ]
  },
  'zone-b': {
    name: 'แปลงเกษตรโซน B',
    temp: 27.8,
    humidity: 75,
    wind: '2.10 m/s',
    chart: [
      { time: '00:00', temp: 23.9, humidity: 78 },
      { time: '03:00', temp: 23.2, humidity: 80 },
      { time: '06:00', temp: 24.5, humidity: 76 },
      { time: '09:00', temp: 26.8, humidity: 69 },
      { time: '12:00', temp: 29.8, humidity: 62 },
      { time: '15:00', temp: 28.9, humidity: 65 },
      { time: '18:00', temp: 26.5, humidity: 72 },
      { time: '21:00', temp: 25.0, humidity: 75 },
    ]
  }
};

export default function TelemetryPage() {
  const [selectedZone, setSelectedZone] = useState<string>('zone-a');
  const currentData = telemetryDataByZone[selectedZone];

  return (
    <AppLayout title="กราฟเซนเซอร์ (Telemetry)">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-800 tracking-tight">กราฟและข้อมูลเซนเซอร์ย้อนหลัง</h1>
          <p className="text-xs text-slate-500 mt-1">วิเคราะห์สถิติตัวแปรสภาพแวดล้อมตามพื้นที่โซนในแปลงเกษตร</p>
        </div>

        {/* Zone Selector Dropdown */}
        <div className="flex items-center gap-2 bg-white px-3.5 py-2 rounded-2xl border border-slate-200 shadow-sm self-start sm:self-auto">
          <Grid size={16} className="text-emerald-600" />
          <span className="text-xs font-bold text-slate-600">เลือกโซน:</span>
          <select 
            value={selectedZone}
            onChange={(e) => setSelectedZone(e.target.value)}
            className="text-xs font-bold text-slate-800 bg-transparent focus:outline-none cursor-pointer"
          >
            <option value="zone-a">แปลงเกษตรโซน A</option>
            <option value="greenhouse">โรงเรือนเพาะชำ</option>
            <option value="zone-b">แปลงเกษตรโซน B</option>
          </select>
        </div>
      </div>

      {/* Summary Cards for Selected Zone */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold text-slate-500">อุณหภูมิ ({currentData.name})</span>
            <CloudSun size={20} className="text-amber-500" />
          </div>
          <div className="text-2xl font-black text-slate-800">{currentData.temp} <span className="text-sm font-normal text-slate-500">°C</span></div>
          <p className="text-[11px] text-emerald-600 mt-2">● อัปเดตแบบเรียลไทม์จากโซน</p>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold text-slate-500">ความชื้นสัมพัทธ์ ({currentData.name})</span>
            <Droplets size={20} className="text-blue-500" />
          </div>
          <div className="text-2xl font-black text-slate-800">{currentData.humidity} <span className="text-sm font-normal text-slate-500">%</span></div>
          <p className="text-[11px] text-emerald-600 mt-2">● อยู่ในเกณฑ์มาตรฐาน</p>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold text-slate-500">ความเร็วลม ({currentData.name})</span>
            <Wind size={20} className="text-teal-500" />
          </div>
          <div className="text-2xl font-black text-slate-800">{currentData.wind}</div>
          <p className="text-[11px] text-emerald-600 mt-2">● สภาวะปกติ</p>
        </div>
      </div>

      {/* Interactive Chart for Selected Zone */}
      <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-5 sm:p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <LineChartIcon size={18} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-800">กราฟแสดงแนวโน้มอุณหภูมิและความชื้น: {currentData.name}</h2>
            <p className="text-[11px] text-slate-400">ข้อมูลย้อนหลัง 24 ชั่วโมงประจำโซน</p>
          </div>
        </div>
        
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={currentData.chart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0', fontSize: '12px' }}
              />
              <Line type="monotone" dataKey="temp" name="อุณหภูมิ (°C)" stroke="#f59e0b" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              <Line type="monotone" dataKey="humidity" name="ความชื้น (%)" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </AppLayout>
  );
}
