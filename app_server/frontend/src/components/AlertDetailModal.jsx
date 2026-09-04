import React, { useState } from 'react';
import Modal from './Modal';
import SeverityBadge from './SeverityBadge';
import { Shield, Server, Terminal, Copy, Check, Info, ArrowRight } from 'lucide-react';

export default function AlertDetailModal({ alert, isOpen, onClose }) {
  const [copied, setCopied] = useState(false);

  if (!alert) return null;

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(alert, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-cyan-400" />
          <span>Security Alert Investigation: <span className="font-mono text-cyan-400">{alert.id}</span></span>
        </div>
      }
      maxWidth="max-w-4xl"
    >
      <div className="space-y-6">
        {/* Severity Banner */}
        <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <SeverityBadge severity={alert.severity} level={alert.rule_level} />
            <span className="text-xs text-slate-400 font-mono">
              Rule #{alert.rule_id} &bull; {new Date(alert.timestamp).toLocaleString()}
            </span>
          </div>
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
            {alert.status}
          </span>
        </div>

        {/* Description */}
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Rule Description</h4>
          <p className="text-sm font-medium text-slate-100 bg-slate-900/80 p-3.5 rounded-lg border border-slate-800">
            {alert.rule_description}
          </p>
        </div>

        {/* MITRE ATT&CK Info */}
        {alert.mitre_tactic && (
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              MITRE ATT&CK Framework Mapping
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-800/60 p-2.5 rounded-lg border border-slate-700/50">
                <span className="text-slate-400">Tactic:</span>{' '}
                <span className="font-semibold text-cyan-300">{alert.mitre_tactic}</span>
              </div>
              <div className="bg-slate-800/60 p-2.5 rounded-lg border border-slate-700/50">
                <span className="text-slate-400">Technique:</span>{' '}
                <span className="font-semibold text-cyan-300">
                  {alert.mitre_technique_id} - {alert.mitre_technique_name}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Telemetry Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Agent Information */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400" />
              Target Endpoint
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Agent Name:</span>
                <span className="font-mono text-slate-200 font-semibold">{alert.agent_name}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Agent ID:</span>
                <span className="font-mono text-slate-200">{alert.agent_id}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Agent IP:</span>
                <span className="font-mono text-slate-200">{alert.agent_ip}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Log Location:</span>
                <span className="font-mono text-slate-300 truncate max-w-[200px]" title={alert.location}>{alert.location}</span>
              </div>
            </div>
          </div>

          {/* Network & Protocol Details */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Terminal className="w-4 h-4 text-cyan-400" />
              Network Flow
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Source IP:</span>
                <span className="font-mono text-rose-400 font-semibold">{alert.source_ip}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Destination IP:</span>
                <span className="font-mono text-slate-200">{alert.destination_ip || '-'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Port / Protocol:</span>
                <span className="font-mono text-slate-200">{alert.destination_port || '-'} / {alert.protocol || 'TCP'}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Rule Groups:</span>
                <span className="font-mono text-cyan-400 text-[11px] truncate max-w-[200px]">
                  {Array.isArray(alert.rule_groups) ? alert.rule_groups.join(', ') : '-'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Raw Log */}
        {alert.raw_log && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Raw Log Event</h4>
              <button
                onClick={handleCopyJson}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-mono transition"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied JSON' : 'Copy Payload'}
              </button>
            </div>
            <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
              {alert.raw_log}
            </pre>
          </div>
        )}
      </div>
    </Modal>
  );
}
