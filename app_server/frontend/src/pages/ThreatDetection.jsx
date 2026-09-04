import React, { useState, useEffect } from 'react';
import { threatService } from '../services/threatService';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import { Crosshair, Shield, Bug, FileCheck, RefreshCw, AlertTriangle, Layers, ArrowUpRight } from 'lucide-react';

export default function ThreatDetection() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('mitre'); // 'mitre' | 'fim' | 'vulnerabilities'

  const fetchThreats = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await threatService.getThreatIntelligence();
      setData(res);
    } catch (err) {
      console.error(err);
      setError('Failed to load threat intelligence and MITRE telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchThreats();
  }, []);

  if (loading) {
    return <LoadingSpinner message="Correlating MITRE ATT&CK Matrix, FIM & CVE feeds..." />;
  }

  if (error && !data) {
    return <ErrorBanner message={error} onRetry={fetchThreats} />;
  }

  const { mitre_tactics = [], fim_events = [], vulnerabilities = [] } = data || {};

  return (
    <div className="space-y-6">
      {/* Navigation Tabs */}
      <div className="cyber-card rounded-2xl p-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('mitre')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold tracking-wide transition ${
              activeTab === 'mitre'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Crosshair className="w-4 h-4" />
            <span>MITRE ATT&CK Matrix ({mitre_tactics.length} Tactics)</span>
          </button>

          <button
            onClick={() => setActiveTab('fim')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold tracking-wide transition ${
              activeTab === 'fim'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <FileCheck className="w-4 h-4" />
            <span>File Integrity (FIM / Syscheck)</span>
          </button>

          <button
            onClick={() => setActiveTab('vulnerabilities')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold tracking-wide transition ${
              activeTab === 'vulnerabilities'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Bug className="w-4 h-4" />
            <span>Vulnerability Detector (CVE)</span>
          </button>
        </div>

        <button
          onClick={fetchThreats}
          className="p-2 rounded-xl bg-slate-900/60 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition"
          title="Refresh Threat Intel"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* MITRE ATT&CK View */}
      {activeTab === 'mitre' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {mitre_tactics.map((tactic) => (
              <div key={tactic.id} className="cyber-card rounded-2xl p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
                    <div>
                      <span className="font-mono text-xs font-bold text-cyan-400">{tactic.id}</span>
                      <h3 className="text-sm font-bold text-white mt-0.5">{tactic.name}</h3>
                    </div>
                    <span className="px-2.5 py-1 rounded-lg bg-cyan-950 text-cyan-300 font-mono text-xs font-bold border border-cyan-500/30">
                      {tactic.event_count} Events
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {tactic.techniques.map((tech) => (
                      <div
                        key={tech.id}
                        className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 flex items-center justify-between gap-3 text-xs"
                      >
                        <div className="min-w-0">
                          <span className="font-mono text-[11px] text-slate-400">{tech.id}</span>
                          <p className="font-medium text-slate-200 truncate">{tech.name}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <span className="font-mono font-bold text-white">{tech.count}</span>
                          <div className={`text-[10px] uppercase font-semibold ${
                            tech.severity === 'critical' ? 'text-rose-400' : tech.severity === 'high' ? 'text-orange-400' : 'text-amber-400'
                          }`}>
                            {tech.severity}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
                  <span>Wazuh Detection Policy Active</span>
                  <span className="text-cyan-400 font-mono">Mapped &bull; 100%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* File Integrity Monitoring (FIM) View */}
      {activeTab === 'fim' && (
        <div className="cyber-card rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-cyan-400" />
              Real-time Syscheck & File Integrity Events ({fim_events.length} Mod Events)
            </span>
            <span className="text-[11px] font-mono text-cyan-400">PCI-DSS 11.5 / FIM</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold bg-slate-950/40">
                  <th className="py-3.5 px-4">Event ID</th>
                  <th className="py-3.5 px-4">Timestamp</th>
                  <th className="py-3.5 px-4">Target Endpoint</th>
                  <th className="py-3.5 px-4">Monitored File Path</th>
                  <th className="py-3.5 px-4">Event Classification</th>
                  <th className="py-3.5 px-4">User</th>
                  <th className="py-3.5 px-4">Checksum Delta</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {fim_events.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 text-cyan-400 font-bold whitespace-nowrap">
                      {ev.id}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 whitespace-nowrap">
                      {new Date(ev.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="py-3.5 px-4 font-sans font-semibold text-white whitespace-nowrap">
                      {ev.agent_name}
                    </td>
                    <td className="py-3.5 px-4 text-rose-300 font-bold max-w-sm truncate">
                      {ev.file_path}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-sans">
                        {ev.event_type}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-300 whitespace-nowrap">
                      {ev.user}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 text-[11px] whitespace-nowrap">
                      <span className="text-slate-500">{ev.md5_before}</span> &rarr; <span className="text-cyan-400 font-bold">{ev.md5_after}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Vulnerability Detector View */}
      {activeTab === 'vulnerabilities' && (
        <div className="cyber-card rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Bug className="w-4 h-4 text-rose-400" />
              Wazuh Vulnerability Detector / CVE Telemetry
            </span>
            <span className="text-[11px] font-mono text-cyan-400">NVD / CVE Feeds</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold bg-slate-950/40">
                  <th className="py-3.5 px-4">CVE Identifier</th>
                  <th className="py-3.5 px-4">Vulnerable Package</th>
                  <th className="py-3.5 px-4">Target Endpoint</th>
                  <th className="py-3.5 px-4">CVSS Severity</th>
                  <th className="py-3.5 px-4">Vulnerability Summary</th>
                  <th className="py-3.5 px-4">Remediation Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {vulnerabilities.map((vuln) => (
                  <tr key={vuln.cve_id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 text-rose-400 font-bold whitespace-nowrap">
                      {vuln.cve_id}
                    </td>
                    <td className="py-3.5 px-4 text-cyan-300 font-semibold whitespace-nowrap">
                      {vuln.package}
                    </td>
                    <td className="py-3.5 px-4 font-sans font-semibold text-white whitespace-nowrap">
                      {vuln.agent_name}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className={`px-2.5 py-0.5 rounded text-xs font-semibold ${
                        vuln.severity.includes('Critical') ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30' : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                      }`}>
                        {vuln.severity}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-sans text-slate-300 max-w-md truncate">
                      {vuln.description}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-sans">
                        {vuln.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
