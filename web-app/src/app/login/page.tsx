'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Lock, Mail, ArrowRight } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('parkphum@smartiot.com');
  const [password, setPassword] = useState('********');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    router.push('/dashboard');
  };

  return (
    <div className="min-h-screen bg-emerald-50 flex items-center justify-center p-4 font-sans">
      <div className="bg-white rounded-3xl shadow-xl w-full max-w-md p-8 border border-emerald-100">
        {/* Brand Logo & Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-3xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto mb-4 overflow-hidden shadow-sm">
            <img 
              src="/images/logo.png" 
              alt="Smart IoT Platform Logo" 
              className="w-full h-full object-cover"
            />
          </div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight">Smart IoT Platform</h1>
          <p className="text-xs text-slate-400 mt-1">ระบบจัดการและควบคุมฟาร์มอัจฉริยะ</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">อีเมลผู้ใช้งาน</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-400">
                <Mail size={16} />
              </span>
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full pl-10 pr-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 transition-colors"
                placeholder="name@smartiot.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">รหัสผ่าน</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-400">
                <Lock size={16} />
              </span>
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full pl-10 pr-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-emerald-600 transition-colors"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button 
            type="submit"
            className="w-full mt-2 bg-emerald-600 hover:bg-emerald-700 text-white py-3.5 rounded-2xl text-xs font-bold shadow-md transition-all flex items-center justify-center gap-2"
          >
            เข้าสู่ระบบ
            <ArrowRight size={16} />
          </button>
        </form>

        <div className="text-center mt-6">
          <p className="text-[11px] text-slate-400">Smart IoT Farm Management Solution © 2026</p>
        </div>
      </div>
    </div>
  );
}
