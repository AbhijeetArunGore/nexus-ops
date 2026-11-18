import React, { useState, useEffect } from 'react';
import { ShieldAlert, Activity, Sparkles, Terminal } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toUTCString().replace('GMT', 'UTC'));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 bg-[#111827] border-b border-gray-800 px-6 flex items-center justify-between sticky top-0 z-50">
      {/* Brand & Tagline */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-extrabold text-base tracking-wider text-white">NEXUS</span>
            <span className="text-xs font-mono font-semibold bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/30">OPS</span>
          </div>
          <p className="text-[10px] text-gray-400 hidden sm:block">Payment Reliability & Incident Intelligence</p>
        </div>
      </div>

      {/* Mandatory Simulated Disclaimer Badge */}
      <div className="hidden md:flex items-center space-x-2 bg-amber-500/10 border border-amber-500/30 px-3 py-1 rounded-full text-amber-400 text-xs font-mono">
        <ShieldAlert className="w-3.5 h-3.5 animate-pulse text-amber-400" />
        <span className="font-semibold tracking-wide">SIMULATED ENVIRONMENT — NO PRODUCTION CONNECTION</span>
      </div>

      {/* System Status & UTC Time */}
      <div className="flex items-center space-x-4">
        <div className="hidden lg:flex items-center space-x-1.5 text-xs font-mono text-gray-400 bg-gray-900/60 px-2.5 py-1 rounded border border-gray-800">
          <Terminal className="w-3.5 h-3.5 text-emerald-400" />
          <span>{currentTime || 'Synchronizing UTC...'}</span>
        </div>

        <div className="flex items-center space-x-2 bg-emerald-950/40 border border-emerald-800/40 px-2.5 py-1 rounded text-emerald-400 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span>SYS: HEALTHY</span>
        </div>
      </div>
    </header>
  );
};
