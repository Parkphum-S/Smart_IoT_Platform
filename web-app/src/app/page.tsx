'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

export default function SplashPage() {
  const router = useRouter();

  useEffect(() => {
    // หน่วงเวลา 2.5 วินาที แล้วเปลี่ยนเส้นทางไปหน้า Login อัตโนมัติ
    const timer = setTimeout(() => {
      router.push('/login');
    }, 2500);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-cover bg-center" style={{ backgroundImage: "url('/images/Gemini_Generated_Image.jpeg')" }}>
      {/* Dark Overlay สำหรับปรับความมืดภาพพื้นหลังเล็กน้อย */}
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[1px]" />

      {/* การ์ดตรงกลางแบบโปร่งแสง (Glassmorphism) */}
      <div className="relative z-10 w-full max-w-md p-8 bg-gray-900/40 backdrop-blur-md rounded-3xl border border-white/10 shadow-2xl flex flex-col items-center text-center mx-4">
        {/* โลโก้ */}
        <div className="w-20 h-20 mb-5 rounded-2xl bg-white/80 backdrop-blur-md flex items-center justify-center shadow-lg p-2 border border-white/20">
          <Image 
            src="/images/logo.png" 
            alt="Smart IoT Logo" 
            width={64} 
            height={64} 
            className="object-contain"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
        </div>

        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-medium mb-4">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
          <span>IoT Farm Connected</span>
        </div>

        <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight mb-3 drop-shadow-md">
          Smart IoT Platform
        </h1>
        <p className="text-xs md:text-sm text-gray-200 max-w-sm leading-relaxed mb-6 drop-shadow">
          ระบบแพลตฟอร์มบริหารจัดการและควบคุมฟาร์มอัจฉริยะผ่านเทคโนโลยี IoT เชื่อมต่อฉับไว เรียลไทม์
        </p>

        <div className="text-[11px] text-gray-300 mt-2">
          Smart IoT Platform Solution &copy; 2026
        </div>
      </div>
    </main>
  );
}
