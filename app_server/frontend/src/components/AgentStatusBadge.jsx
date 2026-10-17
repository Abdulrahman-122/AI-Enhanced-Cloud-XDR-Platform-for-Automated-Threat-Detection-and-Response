import React from 'react';
import { CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';

export default function AgentStatusBadge({ status }) {
  const st = (status || 'unknown').toLowerCase();

  if (st === 'active' || st === 'online') {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
        <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
        Active
      </span>
    );
  }

  if (st === 'disconnected' || st === 'offline') {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/15 text-rose-400 border border-rose-500/30">
        <XCircle className="w-3.5 h-3.5 mr-1" />
        Disconnected
      </span>
    );
  }

  if (st === 'pending') {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30">
        <Clock className="w-3.5 h-3.5 mr-1 animate-spin" />
        Pending
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-500/15 text-slate-400 border border-slate-500/30">
      <AlertCircle className="w-3.5 h-3.5 mr-1" />
      {status}
    </span>
  );
}
