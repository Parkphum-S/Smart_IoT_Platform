'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Building2, 
  Grid, 
  Cpu, 
  GitBranch, 
  LineChart, 
  Activity, 
  Users, 
  ShieldAlert, 
  Settings,
  X
} from 'lucide-react';

interface SidebarProps {
  mobileOpen?: boolean;
  setMobileOpen?: (open: boolean) => void;
}

export function Sidebar({ mobileOpen = false, setMobileOpen }: SidebarProps) {
  const pathname = usePathname();

  const menuItems = [
    { name: 'แดชบอร์ดภาพรวม', href: '/dashboard', icon: LayoutDashboard },
    { name: 'จัดการพื้นที่ (Workspaces)', href: '/workspaces', icon: Building2 },
    { name: 'จัดการโซน (Rooms)', href: '/rooms', icon: Grid },
    { name: 'จัดการอุปกรณ์ (Devices)', href: '/devices', icon: Cpu },
    { name: 'ระบบอัตโนมัติ (Automations)', href: '/automations', icon: GitBranch },
    { name: 'กราฟเซนเซอร์ (Telemetry)', href: '/telemetry', icon: LineChart },
    { name: 'สถานะอุปกรณ์ (Diagnostics)', href: '/diagnostics', icon: Activity },
    { name: 'จัดการสมาชิก (RBAC)', href: '/rbac', icon: Users },
    { name: 'ประวัติระบบ (Audit Logs)', href: '/audit-logs', icon: ShieldAlert },
    { name: 'ตั้งค่าระบบ (Settings)', href: '/settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && setMobileOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden transition-opacity"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-100 flex flex-col h-screen shadow-sm transition-transform duration-300 ease-in-out
        md:translate-x-0 md:static md:h-screen md:sticky md:top-0
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Brand Header & Mobile Close Button */}
        <div className="p-5 flex items-center justify-between border-b border-slate-50">
          <div className="flex items-center space-x-3 min-w-0">
            <div className="w-10 h-10 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center overflow-hidden shrink-0 shadow-sm relative">
              <img 
                src="/images/logo.png" 
                alt="Smart IoT Platform Logo" 
                className="w-full h-full object-cover"
              />
            </div>
            <div className="min-w-0">
              <h1 className="text-xs font-black text-slate-800 leading-tight truncate">Smart IoT Platform</h1>
              <p className="text-[10px] text-slate-400 mt-0.5 truncate">Farm IoT Solution</p>
            </div>
          </div>
          {setMobileOpen && (
            <button 
              onClick={() => setMobileOpen(false)} 
              className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-500 md:hidden shrink-0"
              aria-label="Close Sidebar"
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* Navigation Menu */}
        <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen && setMobileOpen(false)}
                className={`w-full flex items-center space-x-3 px-3.5 py-3 rounded-2xl text-xs font-semibold transition-all text-left ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 shadow-sm'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <Icon size={18} className={isActive ? 'text-emerald-600' : 'text-slate-400'} />
                <span className="flex-1 text-left leading-snug">{item.name}</span>
              </Link>
            );
          })}
        </div>
      </aside>
    </>
  );
}
