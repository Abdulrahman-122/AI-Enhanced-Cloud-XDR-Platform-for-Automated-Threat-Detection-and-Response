import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'cyan', trend }) {
  const colorMap = {
    cyan: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20 shadow-glow-cyan',
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20 shadow-glow-emerald',
    crimson: 'text-rose-400 bg-rose-500/10 border-rose-500/20 shadow-glow-crimson',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    blue: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  };

  const activeColor = colorMap[color] || colorMap.cyan;

  return (
    <div className="cyber-card rounded-xl p-4 md:p-5 relative overflow-hidden group">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold tracking-wider text-slate-400 uppercase">{title}</p>
          <div className="flex items-baseline space-x-2 mt-2">
            <span className="text-2xl md:text-3xl font-bold font-mono text-white tracking-tight">{value}</span>
            {trend && (
              <span className={`text-xs font-medium ${trend > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {trend > 0 ? `+${trend}%` : `${trend}%`}
              </span>
            )}
          </div>
          {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`p-3 rounded-lg border ${activeColor} transition-transform group-hover:scale-110 duration-200`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
      <div className={`absolute bottom-0 left-0 right-0 h-0.5 opacity-60 bg-gradient-to-r from-transparent via-${color === 'crimson' ? 'rose' : color}-500 to-transparent`} />
    </div>
  );
}
