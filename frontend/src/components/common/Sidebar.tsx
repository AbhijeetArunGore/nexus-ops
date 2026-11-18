import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  SearchCode,
  AlertTriangle,
  FlaskConical,
  BotMessageSquare,
  BookOpen,
  GraduationCap,
  Settings
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', label: 'Operations Overview', icon: LayoutDashboard },
  { path: '/investigate', label: 'Incident Investigator', icon: SearchCode },
  { path: '/incidents', label: 'Incident Management', icon: AlertTriangle },
  { path: '/lab', label: 'Payment Reliability Lab', icon: FlaskConical },
  { path: '/copilot', label: 'Ops Knowledge Copilot', icon: BotMessageSquare },
  { path: '/runbooks', label: 'Runbook Library', icon: BookOpen },
  { path: '/learning', label: 'Incident Learning Hub', icon: GraduationCap },
  { path: '/settings', label: 'System Settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-[#111827] border-r border-gray-800 flex flex-col justify-between h-[calc(100vh-3.5rem)] sticky top-14 select-none">
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-[11px] font-mono font-semibold tracking-wider text-gray-500 uppercase">
          Navigation
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                    : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800/60'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="truncate">{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      {/* SRE Operational Mode Footer */}
      <div className="p-4 border-t border-gray-800/80 bg-gray-900/40">
        <div className="flex items-center justify-between text-xs font-mono text-gray-400">
          <span>PIPELINE</span>
          <span className="text-emerald-400 font-semibold">DETERMINISTIC 1ST</span>
        </div>
        <div className="flex items-center justify-between text-[11px] font-mono text-gray-500 mt-1">
          <span>AI REASONING</span>
          <span className="text-blue-400 font-semibold">EVIDENCE-GROUNDED</span>
        </div>
      </div>
    </aside>
  );
};
