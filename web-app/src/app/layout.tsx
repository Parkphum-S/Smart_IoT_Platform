import './globals.css';
import React from 'react';

export const metadata = {
  title: 'Smart IoT Platform',
  description: 'Smart Life style IoT Platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th">
      <body className="bg-slate-50 text-slate-900 antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
