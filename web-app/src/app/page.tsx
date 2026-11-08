'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SplashPage() {
  const router = useRouter();

  // ตั้งเวลา 2.5 วินาที แล้วเปลี่ยนไปหน้า /login อัตโนมัติทันที
  useEffect(() => {
    const timer = setTimeout(() => {
      router.push('/login');
    }, 2500);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-slate-950">
      {/* Background Image ดั้งเดิม */}
      <div 
        className="absolute inset-0 z-0 opacity-40 bg-cover bg-center"
        style={{ backgroundImage: 'url("/images/Gemini_Generated_Image.jpeg")' }}
      />
      <div className="absolute inset-0 z-0 bg-gradient-to-t from-slate-950 via-slate-950/80 to-transparent" />

      {/* Main Container */}
      <div className="relative z-10 w-full max-w-md p-6 mx-4 text-center flex flex-col items-center">
        
        {/* Logo Image ดั้งเดิม */}
        <div className="w-28 h-28 relative mb-6 rounded-3xl overflow-hidden shadow-2xl border border-emerald-500/30 bg-slate-900/50">
          <img 
            src="/images/Generated_Image_logo.png" 
            alt="Smart IoT Logo" 
            className="w-full h-full object-cover"
          />
        </div>

        {/* Badge Status */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-4">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
          IoT Farm Connected
        </div>

        {/* Title & Description */}
        <h1 className="text-3xl font-black text-white tracking-tight mb-2">
          Smart IoT Platform
        </h1>
        <p className="text-sm text-slate-300 leading-relaxed mb-6">
          ระบบแพลตฟอร์มบริหารจัดการและควบคุมฟาร์มอัจฉริยะผ่านเทคโนโลยี IoT เชื่อมต่อฉับไว เรียลไทม์
        </p>

        {/* Footer Note */}
        <div className="mt-8 pt-6 border-t border-slate-800/80 w-full">
          <p className="text-[11px] text-slate-500 font-medium">
            Smart IoT Platform Solution © 2026
          </p>
        </div>

      </div>
    </div>
  );
}
