import React from 'react';
import { ShieldCheck } from 'lucide-react';

export default function EmptyState({ title = 'No records found', message = 'No security events match your current filter parameters.', icon: Icon = ShieldCheck }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400 mb-4">
        <Icon className="w-7 h-7 text-cyan-400" />
      </div>
      <h3 className="text-base font-semibold text-slate-200">{title}</h3>
      <p className="text-xs text-slate-400 max-w-sm mt-1">{message}</p>
    </div>
  );
}
