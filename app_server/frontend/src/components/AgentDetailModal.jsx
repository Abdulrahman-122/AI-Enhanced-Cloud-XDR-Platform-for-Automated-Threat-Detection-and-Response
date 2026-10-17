import React from 'react';
import Modal from './Modal';
import AgentStatusBadge from './AgentStatusBadge';
import { Server, Activity, Cpu, HardDrive, ShieldCheck, Clock, Network, Layers } from 'lucide-react';

export default function AgentDetailModal({ agent, isOpen, onClose }) {
  if (!agent) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-cyan-400" />
          <span>Endpoint Telemetry: <span className="font-mono text-cyan-400">{agent.name}</span></span>
        </div>
      }
      maxWidth="max-w-3xl"
    >
      <div className="space-y-6">
        {/* Status Header */}
        <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AgentStatusBadge status={agent.status} />
            <span className="text-xs text-slate-400 font-mono">Agent ID: #{agent.id} &bull; Group: {agent.group || 'default'}</span>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            Version: <span className="text-cyan-400 font-semibold">{agent.version}</span>
          </span>
        </div>

        {/* System Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              Operating System
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">OS Name:</span>
                <span className="font-semibold text-slate-200">{agent.os}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">IP Address:</span>
                <span className="font-mono text-cyan-400 font-semibold">{agent.ip}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Architecture:</span>
                <span className="font-mono text-slate-300">{agent.os_architecture || 'x86_64'}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Node Cluster:</span>
                <span className="font-mono text-slate-300">{agent.node_name || 'wazuh-master'}</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              Security Modules
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">FIM / Syscheck:</span>
                <span className="text-emerald-400 font-semibold">Enabled (Active)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Rootcheck & SCA:</span>
                <span className="text-emerald-400 font-semibold">Enabled (Active)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Last Keepalive:</span>
                <span className="font-mono text-slate-300">{new Date(agent.last_keepalive).toLocaleTimeString()}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Last Baseline Scan:</span>
                <span className="font-mono text-slate-300">{agent.last_scan ? new Date(agent.last_scan).toLocaleDateString() : 'Recent'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Resource Telemetry */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            Live Endpoint Resource Health
          </h4>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/40">
              <Cpu className="w-4 h-4 text-cyan-400 mx-auto mb-1" />
              <div className="text-sm font-bold font-mono text-slate-100">{agent.cpu_usage || '16.8%'}</div>
              <div className="text-[10px] text-slate-400 uppercase">CPU Load</div>
            </div>
            <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/40">
              <Activity className="w-4 h-4 text-emerald-400 mx-auto mb-1" />
              <div className="text-sm font-bold font-mono text-slate-100">{agent.memory_usage || '41.2%'}</div>
              <div className="text-[10px] text-slate-400 uppercase">RAM Usage</div>
            </div>
            <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/40">
              <HardDrive className="w-4 h-4 text-amber-400 mx-auto mb-1" />
              <div className="text-sm font-bold font-mono text-slate-100">{agent.disk_usage || '53.4%'}</div>
              <div className="text-[10px] text-slate-400 uppercase">Disk Storage</div>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}
