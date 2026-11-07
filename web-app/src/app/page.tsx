'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowRight, Wifi } from 'lucide-react';

export default function SplashScreen() {
  return (
    <div className="relative min-h-screen flex items-center justify-center font-sans overflow-hidden">
      {/* Background Image with Overlay */}
      <div 
        className="absolute inset-0 bg-cover bg-center z-0 scale-105 transition-transform duration-1000"
        style={{ backgroundImage: `url('/images/Gemini_Generated_Image.jpeg')` }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/50 to-slate-900/40 z-10" />

      {/* Content Container */}
      <div className="relative z-20 max-w-lg w-full mx-4 text-center p-8 sm:p-10 rounded-3xl bg-slate-900/40 backdrop-blur-md border border-white/10 shadow-2xl">
        {/* Logo */}
        <div className="w-20 h-20 rounded-3xl bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center mx-auto mb-6 overflow-hidden shadow-lg">
          <img 
            src="/images/logo.png" 
            alt="Smart IoT Platform Logo" 
            className="w-full h-full object-cover"
          />
        </div>

        {/* Title & Badge */}
        <div className="inline-flex items-center gap-2 bg-emerald-500/20 border border-emerald-500/30 px-3 py-1 rounded-full text-[11px] font-semibold text-emerald-300 mb-4">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          IoT Farm Connected
        </div>

        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mb-2">
          Smart IoT Platform
        </h1>
        <p className="text-xs sm:text-sm text-slate-300 mb-8 leading-relaxed">
          ระบบแพลตฟอร์มบริหารจัดการและควบคุมฟาร์มอัจฉริยะผ่านเทคโนโลยี IoT เชื่อมต่อฉับไว เรียลไทม์
        </p>

        {/* Action Buttons */}
        <div className="space-y-3">
          <Link 
            href="/dashboard"
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white py-3.5 rounded-2xl text-xs font-bold shadow-lg transition-all flex items-center justify-center gap-2"
          >
            เข้าสู่ระบบแดชบอร์ด
            <ArrowRight size={16} />
          </Link>
          <Link 
            href="/login"
            className="w-full bg-white/10 hover:bg-white/20 text-white border border-white/10 py-3.5 rounded-2xl text-xs font-bold transition-all flex items-center justify-center gap-2"
          >
            ลงชื่อเข้าใช้งานระบบ (Login)
          </Link>
        </div>

        <div className="mt-8 text-[11px] text-slate-400">
          Smart IoT Platform Solution © 2026
        </div>
      </div>
    </div>
  );
}
