'use client';

import React, { useState, useEffect } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { Menu } from 'lucide-react';

interface AppLayoutProps {
  children: React.ReactNode;
  title?: string;
}

export function AppLayout({ children, title = 'Smart Agri-IoT' }: AppLayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-slate-50/50 flex font-sans leading-relaxed">
      {/* Sidebar พร้อมสถานะ Responsive */}
      <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile Header พร้อมปุ่ม Hamburger Menu สำหรับทุกหน้า */}
        <header className="bg-white border-b border-slate-100 h-16 flex items-center px-4 md:hidden justify-between shrink-0 shadow-sm">
          <button 
            onClick={() => setMobileOpen(true)}
            className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors shrink-0"
            aria-label="Open Menu"
          >
            <Menu size={20} />
          </button>
          <span className="font-bold text-slate-800 text-xs truncate px-2">{title}</span>
          <div className="w-8 shrink-0" />
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
