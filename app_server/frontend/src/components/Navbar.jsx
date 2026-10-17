import React from 'react';
import { RefreshCw, Shield, Wifi, WifiOff, Bell, Clock } from 'lucide-react';

export default function Navbar({ title, subtitle, wazuhStatus, onRefresh, isRefreshing, lastUpdated, autoRefreshSeconds }) {
  const isConnected = wazuhStatus?.connected;

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between px-6 py-3.5 bg-[#070B14]/90 backdrop-blur-md border-b border-slate-800">
      {/* Title */}
      <div>
        <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
          {title}
        </h2>
        {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      </div>

      {/* Actions & Wazuh Connection Indicator */}
      <div className="flex items-center gap-3 md:gap-4">
        {/* Wazuh Status Pill */}
        <div 
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
            isConnected
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
          }`}
          title={wazuhStatus?.status_message || (isConnected ? 'Wazuh Online' : 'Simulation Mode')}
        >
          {isConnected ? (
            <>
              <Wifi className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
              <span className="hidden sm:inline">Wazuh Server:</span>
              <span className="font-mono text-[11px]">Connected ({wazuhStatus?.version || 'v4.8'})</span>
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden sm:inline">Wazuh Service:</span>
              <span className="font-mono text-[11px]">Simulation Mode</span>
            </>
          )}
        </div>

        {/* Last Updated & Auto Refresh */}
        {lastUpdated && (
          <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span>{new Date(lastUpdated).toLocaleTimeString()}</span>
            {autoRefreshSeconds > 0 && (
              <span className="text-[10px] text-cyan-400 font-semibold bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-500/30">
                {autoRefreshSeconds}s
              </span>
            )}
          </div>
        )}

        {/* Manual Refresh Button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition disabled:opacity-50"
            title="Refresh Security Telemetry"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        )}
      </div>
    </header>
  );
}
