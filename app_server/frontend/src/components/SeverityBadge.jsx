import React from 'react';

export default function SeverityBadge({ severity, level }) {
  const sev = (severity || 'low').toLowerCase();

  const styles = {
    critical: 'bg-rose-500/15 text-rose-400 border-rose-500/30 ring-rose-500/20',
    high: 'bg-orange-500/15 text-orange-400 border-orange-500/30 ring-orange-500/20',
    medium: 'bg-amber-500/15 text-amber-400 border-amber-500/30 ring-amber-500/20',
    low: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 ring-emerald-500/20',
  };

  const style = styles[sev] || styles.low;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${style} uppercase tracking-wider`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${sev === 'critical' ? 'bg-rose-400 animate-pulse' : sev === 'high' ? 'bg-orange-400' : sev === 'medium' ? 'bg-amber-400' : 'bg-emerald-400'}`} />
      {severity}
      {level !== undefined && level !== null && (
        <span className="ml-1 opacity-70 font-mono text-[10px]">L{level}</span>
      )}
    </span>
  );
}
