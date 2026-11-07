import React from 'react';
import { Power, Wifi, WifiOff } from 'lucide-react';

interface DeviceCardProps {
  id: string;
  name: string;
  deviceName: string;
  room: string;
  isOnline: boolean;
  isOn: boolean;
  onToggle: (id: string, currentState: boolean) => void;
}

export const DeviceSwitchCard: React.FC<DeviceCardProps> = ({
  id,
  name,
  deviceName,
  room,
  isOnline,
  isOn,
  onToggle,
}) => {
  return (
    <div className="bg-white/90 backdrop-blur-xl p-5 rounded-3xl shadow-lg shadow-emerald-950/5 border border-emerald-100 flex flex-col justify-between transition-all hover:shadow-xl hover:border-emerald-200">
      <div className="flex items-center justify-between">
        <div className={`p-3.5 rounded-2xl ${isOn ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-400'}`}>
          <Power size={22} />
        </div>
        
        {/* Toggle Switch */}
        <button
          onClick={() => onToggle(id, isOn)}
          disabled={!isOnline}
          className={`w-14 h-8 flex items-center rounded-full p-1 duration-300 cursor-pointer ${
            !isOnline ? 'opacity-50 cursor-not-allowed bg-slate-200' : isOn ? 'bg-emerald-600 shadow-md shadow-emerald-600/30' : 'bg-slate-300'
          }`}
        >
          <div className={`bg-white w-6 h-6 rounded-full shadow-md transform duration-300 ${isOn ? 'translate-x-6' : 'translate-x-0'}`} />
        </button>
      </div>

      <div className="mt-5">
        <h3 className="font-bold text-slate-800 text-base">{name}</h3>
        <p className="text-xs text-slate-400 mt-0.5">{room} • {deviceName}</p>
        
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100">
          <span className={`inline-flex items-center space-x-1 text-xs px-2.5 py-1 rounded-full font-medium ${
            isOnline ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-600'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
            <span>{isOnline ? 'ออนไลน์' : 'ออฟไลน์'}</span>
          </span>

          <span className="text-xs font-semibold text-slate-500">
            {isOn ? 'กำลังทำงาน' : 'ปิดอยู่'}
          </span>
        </div>
      </div>
    </div>
  );
};
