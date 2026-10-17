import React from 'react';
import { NavLink as RouterNavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Server, 
  ShieldAlert, 
  Crosshair, 
  FileText, 
  Settings, 
  LogOut, 
  ChevronLeft, 
  ChevronRight,
  UserCheck,
  ShieldCheck,
  GraduationCap
} from 'lucide-react';
import { authService } from '../services/authService';

export default function Sidebar({ collapsed, setCollapsed }) {
  const user = authService.getStoredUser() || { username: 'Analyst', full_name: 'SOC Analyst' };

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Agents', path: '/agents', icon: Server },
    { name: 'Security Alerts', path: '/alerts', icon: ShieldAlert },
    { name: 'Threat Detection', path: '/threats', icon: Crosshair },
    { name: 'Reports', path: '/reports', icon: FileText },
    { name: 'About Academy', path: '/about', icon: GraduationCap },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside
      className={`fixed top-0 bottom-0 left-0 z-40 flex flex-col bg-[#0B1120] border-r border-slate-800 transition-all duration-300 ${
        collapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Header Branding */}
      <div className="flex flex-col items-center justify-center p-4 border-b border-slate-800/80 relative">
        <div className="flex items-center gap-3 w-full">
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-slate-700/60 p-1 flex items-center justify-center shrink-0 overflow-hidden shadow-glow-cyan">
            <img 
              src="/sha_logo.png" 
              alt="El Shorouk Academy Logo" 
              className="w-full h-full object-contain"
            />
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <h1 className="text-xs font-black tracking-wider text-white uppercase truncate">
                XDR Security Platform
              </h1>
              <p className="text-[10px] font-semibold text-cyan-400 tracking-tight truncate">
                El Shorouk Academy
              </p>
              <p className="text-[9px] text-slate-400 uppercase tracking-widest truncate">
                Graduation Project
              </p>
            </div>
          )}
        </div>

        {/* Collapse Toggle Button */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden md:flex absolute -right-3 top-6 w-6 h-6 rounded-full bg-slate-800 border border-slate-700 items-center justify-center text-slate-300 hover:text-white hover:bg-slate-700 shadow-md transition"
        >
          {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <RouterNavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold tracking-wide transition-all duration-150 ${
                  isActive
                    ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/10 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
                }`
              }
              title={collapsed ? item.name : undefined}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span>{item.name}</span>}
            </RouterNavLink>
          );
        })}
      </nav>

      {/* Bottom User Profile & Logout */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/40">
        {!collapsed ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-2 rounded-lg bg-slate-900/60 border border-slate-800">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500/30 to-blue-600/30 border border-cyan-500/30 flex items-center justify-center text-cyan-300 font-bold text-xs shrink-0">
                {(user.full_name || user.username || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-200 truncate">
                  {user.full_name || user.username}
                </p>
                <div className="flex items-center gap-1.5 text-[10px] text-emerald-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>SOC Analyst</span>
                </div>
              </div>
            </div>

            <button
              onClick={authService.logout}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-rose-300 hover:text-rose-100 hover:bg-rose-500/20 border border-rose-500/30 transition duration-150"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div 
              className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-300 font-bold text-xs"
              title={user.full_name || user.username}
            >
              {(user.full_name || user.username || 'U').charAt(0).toUpperCase()}
            </div>
            <button
              onClick={authService.logout}
              className="p-2 rounded-lg text-rose-400 hover:bg-rose-500/20 transition"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
