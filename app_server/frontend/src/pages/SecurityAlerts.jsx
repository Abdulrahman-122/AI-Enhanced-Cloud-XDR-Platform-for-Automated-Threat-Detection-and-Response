import React, { useState, useEffect } from 'react';
import { alertService } from '../services/alertService';
import SeverityBadge from '../components/SeverityBadge';
import AlertDetailModal from '../components/AlertDetailModal';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import EmptyState from '../components/EmptyState';
import { ShieldAlert, Search, Filter, RefreshCw, Eye, ChevronLeft, ChevronRight, Terminal } from 'lucide-react';

export default function SecurityAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filters & Pagination
  const [severity, setSeverity] = useState('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const [selectedAlert, setSelectedAlert] = useState(null);

  const fetchAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const offset = (page - 1) * pageSize;
      const res = await alertService.getAlerts({
        severity: severity !== 'all' ? severity : undefined,
        search: search || undefined,
        limit: pageSize,
        offset: offset,
      });
      setAlerts(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch security alerts from backend API.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [severity, page]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchAlerts();
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Search & Filter Header */}
      <div className="cyber-card rounded-2xl p-4 md:p-5 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Search Input */}
        <form onSubmit={handleSearch} className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search rules, IDs, source IPs, MITRE tactics..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900/80 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 font-mono transition"
          />
        </form>

        {/* Severity Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
            <button
              key={sev}
              onClick={() => {
                setSeverity(sev);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition ${
                severity === sev
                  ? sev === 'critical'
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-glow-crimson'
                    : sev === 'high'
                    ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40'
                    : sev === 'medium'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    : sev === 'low'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {sev}
            </button>
          ))}
          <button
            onClick={fetchAlerts}
            className="p-2 rounded-xl bg-slate-900/60 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition"
            title="Refresh Alerts"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Alerts Table */}
      {loading ? (
        <LoadingSpinner message="Querying security alert events & SIEM logs..." />
      ) : error ? (
        <ErrorBanner message={error} onRetry={fetchAlerts} />
      ) : alerts.length === 0 ? (
        <EmptyState
          title="No Security Alerts Found"
          message="No alerts match the selected severity or search query."
          icon={ShieldAlert}
        />
      ) : (
        <div className="cyber-card rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Security Incident Records ({total} Total Detections)
            </span>
            <span className="text-[11px] font-mono text-cyan-400">Page {page} of {totalPages}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold bg-slate-950/40">
                  <th className="py-3.5 px-4">Alert ID</th>
                  <th className="py-3.5 px-4">Timestamp</th>
                  <th className="py-3.5 px-4">Agent Name</th>
                  <th className="py-3.5 px-4">Rule ID</th>
                  <th className="py-3.5 px-4">Description</th>
                  <th className="py-3.5 px-4">Severity</th>
                  <th className="py-3.5 px-4">Source IP</th>
                  <th className="py-3.5 px-4">MITRE Tactic</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {alerts.map((al) => (
                  <tr key={al.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 text-cyan-400 font-bold whitespace-nowrap">
                      {al.id}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 whitespace-nowrap">
                      {new Date(al.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="py-3.5 px-4 font-sans font-semibold text-white whitespace-nowrap">
                      {al.agent_name}
                    </td>
                    <td className="py-3.5 px-4 text-slate-300">
                      #{al.rule_id}
                    </td>
                    <td className="py-3.5 px-4 font-sans text-slate-200 max-w-sm truncate">
                      {al.rule_description}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <SeverityBadge severity={al.severity} level={al.rule_level} />
                    </td>
                    <td className="py-3.5 px-4 text-rose-400 whitespace-nowrap">
                      {al.source_ip}
                    </td>
                    <td className="py-3.5 px-4 font-sans text-cyan-300 text-[11px] whitespace-nowrap">
                      {al.mitre_tactic || '-'}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => setSelectedAlert(al)}
                        className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 font-sans text-xs transition"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="px-5 py-3.5 border-t border-slate-800 flex items-center justify-between bg-slate-900/40">
            <span className="text-xs text-slate-400 font-mono">
              Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} of {total} alerts
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30 transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-3 py-1 rounded-lg bg-slate-800 text-xs font-mono text-cyan-400 font-bold">
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30 transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Alert Investigation Modal */}
      <AlertDetailModal
        alert={selectedAlert}
        isOpen={!!selectedAlert}
        onClose={() => setSelectedAlert(null)}
      />
    </div>
  );
}
