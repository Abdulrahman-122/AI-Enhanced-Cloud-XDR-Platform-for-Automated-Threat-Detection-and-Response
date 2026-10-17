import React, { useState, useEffect } from 'react';
import { agentService } from '../services/agentService';
import AgentStatusBadge from '../components/AgentStatusBadge';
import AgentDetailModal from '../components/AgentDetailModal';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import EmptyState from '../components/EmptyState';
import { Server, Search, Filter, RefreshCw, Eye, Shield, Laptop, Monitor, Database } from 'lucide-react';

export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAgent, setSelectedAgent] = useState(null);

  const fetchAgents = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await agentService.getAgents({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        search: searchQuery || undefined,
      });
      setAgents(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error(err);
      setError('Failed to retrieve agents from Wazuh API service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, [statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchAgents();
  };

  const getOsIcon = (osName) => {
    const os = (osName || '').toLowerCase();
    if (os.includes('win')) return Monitor;
    if (os.includes('db') || os.includes('sql') || os.includes('cluster')) return Database;
    return Server;
  };

  return (
    <div className="space-y-6">
      {/* Controls & Filter Bar */}
      <div className="cyber-card rounded-2xl p-4 md:p-5 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search agents by name, IP, ID, OS..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900/80 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 font-mono transition"
          />
        </form>

        {/* Status Filter Buttons */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          {['all', 'active', 'disconnected', 'pending'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition ${
                statusFilter === st
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {st}
            </button>
          ))}
          <button
            onClick={fetchAgents}
            className="p-2 rounded-xl bg-slate-900/60 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition"
            title="Refresh Agents"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Agents Table Content */}
      {loading ? (
        <LoadingSpinner message="Polling Wazuh agent manager inventory..." />
      ) : error ? (
        <ErrorBanner message={error} onRetry={fetchAgents} />
      ) : agents.length === 0 ? (
        <EmptyState
          title="No Agents Found"
          message="No Wazuh endpoints match your filter parameters."
          icon={Server}
        />
      ) : (
        <div className="cyber-card rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Enrolled Endpoint Inventory ({total} Assets)
            </span>
            <span className="text-[11px] font-mono text-cyan-400">Wazuh SIEM/EDR Core</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold bg-slate-950/40">
                  <th className="py-3.5 px-4">Agent ID</th>
                  <th className="py-3.5 px-4">Endpoint Name</th>
                  <th className="py-3.5 px-4">IP Address</th>
                  <th className="py-3.5 px-4">Operating System</th>
                  <th className="py-3.5 px-4">Wazuh Version</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Last Keepalive</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {agents.map((ag) => {
                  const OsIcon = getOsIcon(ag.name);
                  return (
                    <tr key={ag.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3.5 px-4 text-slate-400 font-bold">
                        #{ag.id}
                      </td>
                      <td className="py-3.5 px-4 font-sans font-semibold text-white whitespace-nowrap">
                        <div className="flex items-center gap-2.5">
                          <div className="p-1.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
                            <OsIcon className="w-3.5 h-3.5" />
                          </div>
                          <span>{ag.name}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-cyan-300 font-semibold whitespace-nowrap">
                        {ag.ip}
                      </td>
                      <td className="py-3.5 px-4 font-sans text-slate-300 max-w-xs truncate">
                        {ag.os}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 whitespace-nowrap">
                        {ag.version}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <AgentStatusBadge status={ag.status} />
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 whitespace-nowrap">
                        {new Date(ag.last_keepalive).toLocaleString()}
                      </td>
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <button
                          onClick={() => setSelectedAgent(ag)}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 font-sans text-xs transition"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          Telemetry
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Agent Detail Modal */}
      <AgentDetailModal
        agent={selectedAgent}
        isOpen={!!selectedAgent}
        onClose={() => setSelectedAgent(null)}
      />
    </div>
  );
}
