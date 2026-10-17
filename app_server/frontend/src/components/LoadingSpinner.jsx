import React from 'react';
import { Loader2 } from 'lucide-react';

export default function LoadingSpinner({ message = 'Loading SOC telemetry...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="relative">
        <div className="w-12 h-12 rounded-full border-2 border-cyan-500/20 border-t-cyan-400 animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-4 h-4 rounded-full bg-cyan-400/20 animate-pulse" />
        </div>
      </div>
      <p className="mt-4 text-sm font-medium text-slate-400 font-mono tracking-wide">{message}</p>
    </div>
  );
}
