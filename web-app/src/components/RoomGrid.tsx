import React from 'react';
import { DeviceSwitchCard } from './DeviceSwitchCard';

interface Device {
  id: string;
  name: string;
  deviceType: string;
  isOnline: boolean;
  isOn: boolean;
}

interface RoomGridProps {
  roomName: string;
  devices: Device[];
  onToggleDevice: (id: string, state: boolean) => void;
}

export const RoomGrid: React.FC<RoomGridProps> = ({ roomName, devices, onToggleDevice }) => {
  return (
    <div className="mb-8">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-gray-900">{roomName}</h2>
        <span className="text-xs text-gray-500">{devices.length} อุปกรณ์</span>
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {devices.map((device) => (
          <DeviceSwitchCard
            key={device.id}
            id={device.id}
            name={device.name}
            room={roomName}
            deviceName={device.deviceType}
            isOnline={device.isOnline}
            isOn={device.isOn}
            onToggle={onToggleDevice}
          />
        ))}
      </div>
    </div>
  );
};
