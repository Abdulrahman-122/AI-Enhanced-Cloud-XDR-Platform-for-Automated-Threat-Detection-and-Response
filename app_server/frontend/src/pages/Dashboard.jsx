import React, { useState, useEffect } from 'react';
import { dashboardService } from '../services/dashboardService';
import StatCard from '../components/StatCard';
import SeverityBadge from '../components/SeverityBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import AlertDetailModal from '../components/AlertDetailModal';
import { 
  Server, 
  CheckCircle2, 
  XCircle, 
  ShieldAlert, 
  Flame, 
  AlertTriangle, 
  AlertCircle, 
  ShieldCheck, 
  Activity, 
  Eye,
  TrendingUp,
  Radio
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend
} from 'recharts';

export default function Dashboard({ data, loading, error, onRefresh }) {
  const [selectedAlert, setSelectedAlert] = useState(null);

  if (loading && !data) {
    return <LoadingSpinner message="Synthesizing SOC Intelligence & Wazuh Telemetry..." />;
  }

  if (error && !data) {
    return <ErrorBanner message={error} onRetry={onRefresh} />;
  }

  const d = data || {
    total_agents: 0,
    active_agents: 0,
    disconnected_agents: 0,
    total_alerts: 0,
    critical_alerts: 0,
    high_alerts: 0,
    medium_alerts: 0,
    low_alerts: 0,
    alerts_over_time: [],
    alerts_by_severity: [],
    alerts_by_agent: [],
    top_rules: [],
    top_threat_categories: [],
    recent_alerts: [],
  };

  return (
    <div className="space-y-6">
      {/* KPI Cards Row 1: Endpoints & Health */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Endpoints"
          value={d.total_agents}
          subtitle="Registered Wazuh Agents"
          icon={Server}
          color="cyan"
        />
        <StatCard
          title="Active Agents"
          value={d.active_agents}
          subtitle="Live Health Keepalive"
          icon={CheckCircle2}
          color="emerald"
        />
        <StatCard
          title="Disconnected"
          value={d.disconnected_agents}
          subtitle="Endpoints Unreachable"
          icon={XCircle}
          color="crimson"
        />
        <StatCard
          title="Total Alert Events"
          value={d.total_alerts}
          subtitle="Monitored in SIEM / XDR"
          icon={ShieldAlert}
          color="blue"
        />
      </div>

      {/* KPI Cards Row 2: Severity Triage */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Critical Alerts"
          value={d.critical_alerts}
          subtitle="Level 12-15 Escalations"
          icon={Flame}
          color="crimson"
        />
        <StatCard
          title="High Severity"
          value={d.high_alerts}
          subtitle="Level 8-11 Detections"
          icon={AlertTriangle}
          color="amber"
        />
        <StatCard
          title="Medium Severity"
          value={d.medium_alerts}
          subtitle="Level 4-7 Events"
          icon={AlertCircle}
          color="purple"
        />
        <StatCard
          title="Low Severity"
          value={d.low_alerts}
          subtitle="Level 0-3 Informational"
          icon={ShieldCheck}
          color="emerald"
        />
      </div>

      {/* Charts Grid: Timeline & Severity Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline Area Chart */}
        <div className="lg:col-span-2 cyber-card rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">Alert Events Over Time</h3>
            </div>
            <span className="text-xs text-slate-400 font-mono">Real-time hourly frequency</span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={d.alerts_over_time}>
                <defs>
                  <linearGradient id="colorCrit" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EF4444" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#F97316" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#F97316" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorMed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EAB308" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#EAB308" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="time" stroke="#64748B" fontSize={11} />
                <YAxis stroke="#64748B" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0B1120', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  itemStyle={{ color: '#F8FAFC' }}
                />
                <Area type="monotone" dataKey="critical" stroke="#EF4444" fillOpacity={1} fill="url(#colorCrit)" name="Critical" />
                <Area type="monotone" dataKey="high" stroke="#F97316" fillOpacity={1} fill="url(#colorHigh)" name="High" />
                <Area type="monotone" dataKey="medium" stroke="#EAB308" fillOpacity={1} fill="url(#colorMed)" name="Medium" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Severity Donut Chart */}
        <div className="cyber-card rounded-2xl p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">Severity Breakdown</h3>
            </div>
          </div>

          <div className="h-52 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={d.alerts_by_severity}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={75}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {d.alerts_by_severity.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0B1120', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend Table */}
          <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-800">
            {d.alerts_by_severity.map((item) => (
              <div key={item.name} className="flex items-center justify-between px-2 py-1 rounded bg-slate-900/60">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-slate-300 font-medium">{item.name}</span>
                </div>
                <span className="font-mono text-slate-100 font-bold">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Grid: Alerts by Agent & Top Detection Rules */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alerts by Agent */}
        <div className="cyber-card rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Server className="w-4 h-4 text-cyan-400" />
            Alerts by Monitored Asset
          </h3>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d.alerts_by_agent} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis type="number" stroke="#64748B" fontSize={11} />
                <YAxis dataKey="agent" type="category" stroke="#94A3B8" fontSize={11} width={130} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0B1120', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="alerts" fill="#06B6D4" radius={[0, 4, 4, 0]} name="Security Events" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Detection Rules */}
        <div className="cyber-card rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Radio className="w-4 h-4 text-cyan-400" />
            Top Triggered Wazuh Detection Rules
          </h3>
          <div className="space-y-3">
            {d.top_rules.map((rule) => (
              <div
                key={rule.rule_id}
                className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 flex items-center justify-between gap-3 hover:border-slate-700 transition"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-cyan-400">Rule #{rule.rule_id}</span>
                    <SeverityBadge severity={rule.severity} level={rule.level} />
                  </div>
                  <p className="text-xs text-slate-300 font-medium truncate mt-1">
                    {rule.description}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <span className="font-mono text-base font-bold text-white">{rule.count}</span>
                  <div className="text-[10px] text-slate-400 uppercase">Triggers</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Alerts Table */}
      <div className="cyber-card rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-400" />
            <h3 className="text-sm font-semibold text-white">Live Incident Stream (Recent Alerts)</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">Showing latest verified triggers</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
                <th className="py-3 px-3">Timestamp</th>
                <th className="py-3 px-3">Agent</th>
                <th className="py-3 px-3">Rule ID</th>
                <th className="py-3 px-3">Description</th>
                <th className="py-3 px-3">Severity</th>
                <th className="py-3 px-3">Source IP</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {d.recent_alerts.map((al) => (
                <tr key={al.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-3 text-slate-400 whitespace-nowrap">
                    {new Date(al.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="py-3 px-3 text-cyan-300 font-semibold whitespace-nowrap">
                    {al.agent_name}
                  </td>
                  <td className="py-3 px-3 text-slate-300">
                    #{al.rule_id}
                  </td>
                  <td className="py-3 px-3 text-slate-200 font-sans max-w-xs truncate">
                    {al.rule_description}
                  </td>
                  <td className="py-3 px-3 whitespace-nowrap">
                    <SeverityBadge severity={al.severity} level={al.rule_level} />
                  </td>
                  <td className="py-3 px-3 text-rose-400 whitespace-nowrap">
                    {al.source_ip}
                  </td>
                  <td className="py-3 px-3 whitespace-nowrap">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-[11px] text-slate-300">
                      {al.status}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right whitespace-nowrap">
                    <button
                      onClick={() => setSelectedAlert(al)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 text-xs font-sans transition"
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
      </div>

      {/* Alert Investigation Modal */}
      <AlertDetailModal
        alert={selectedAlert}
        isOpen={!!selectedAlert}
        onClose={() => setSelectedAlert(null)}
      />
    </div>
  );
}
