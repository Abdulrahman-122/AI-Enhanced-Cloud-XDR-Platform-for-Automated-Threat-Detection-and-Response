import React, { useState, useEffect } from 'react';
import { reportService } from '../services/reportService';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import { FileText, Download, Printer, ShieldCheck, CheckCircle2, TrendingUp, Server, AlertTriangle } from 'lucide-react';

export default function Reports() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);

  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await reportService.getSummary();
      setReport(res);
    } catch (err) {
      console.error(err);
      setError('Failed to generate SOC compliance & analytics report.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, []);

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      await reportService.downloadAlertsCsv();
    } catch (err) {
      console.error(err);
      alert('Failed to download CSV export.');
    } finally {
      setExporting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return <LoadingSpinner message="Generating compiled SOC incident & compliance report..." />;
  }

  if (error && !report) {
    return <ErrorBanner message={error} onRetry={fetchReport} />;
  }

  return (
    <div className="space-y-6">
      {/* Action Bar (Hidden in Print) */}
      <div className="cyber-card rounded-2xl p-4 md:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 no-print">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400" />
            SOC Executive Summary & Incident Analytics
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Official graduation project analytical evaluation report
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCsv}
            disabled={exporting}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-xs font-semibold uppercase tracking-wider transition shadow-glow-cyan disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            {exporting ? 'Generating CSV...' : 'Export Alerts CSV'}
          </button>

          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 text-xs font-semibold uppercase tracking-wider transition"
          >
            <Printer className="w-4 h-4" />
            Print / PDF Report
          </button>
        </div>
      </div>

      {/* Printable Report Document Card */}
      <div className="cyber-card rounded-2xl p-6 md:p-8 space-y-8 bg-slate-900/90 print:bg-white print:text-black print:p-0 print:border-none print:shadow-none">
        {/* Formal Report Header */}
        <div className="flex flex-col sm:flex-row items-center justify-between pb-6 border-b border-slate-800 print:border-black gap-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-xl bg-white/5 border border-slate-700 p-1 flex items-center justify-center shrink-0">
              <img
                src="/sha_logo.png"
                alt="El Shorouk Academy"
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <h1 className="text-lg font-black text-white print:text-black uppercase tracking-wider">
                El Shorouk Academy &bull; أكاديمية الشروق
              </h1>
              <p className="text-xs font-semibold text-cyan-400 print:text-blue-800">
                Department of Computer Science & Cybersecurity Engineering
              </p>
              <p className="text-[11px] font-mono text-slate-400 print:text-gray-600">
                Graduation Project: Enterprise XDR Security Platform
              </p>
            </div>
          </div>

          <div className="text-right text-xs font-mono text-slate-400 print:text-gray-700">
            <div>Report Date: {new Date(report.generated_at).toLocaleDateString()}</div>
            <div>Time: {new Date(report.generated_at).toLocaleTimeString()} UTC</div>
            <div className="text-emerald-400 print:text-green-800 font-bold">Status: Certified SOC Audit</div>
          </div>
        </div>

        {/* Executive Highlights Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 print:bg-gray-50 print:border-gray-300 text-center">
            <div className="text-2xl font-bold font-mono text-cyan-400 print:text-blue-900">{report.compliance_score}%</div>
            <div className="text-xs text-slate-400 print:text-gray-600 uppercase font-semibold mt-1">Compliance Score</div>
          </div>
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 print:bg-gray-50 print:border-gray-300 text-center">
            <div className="text-2xl font-bold font-mono text-white print:text-black">{report.total_events_analyzed}</div>
            <div className="text-xs text-slate-400 print:text-gray-600 uppercase font-semibold mt-1">Events Ingested</div>
          </div>
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 print:bg-gray-50 print:border-gray-300 text-center">
            <div className="text-2xl font-bold font-mono text-emerald-400 print:text-green-700">{report.resolved_incidents}</div>
            <div className="text-xs text-slate-400 print:text-gray-600 uppercase font-semibold mt-1">Incidents Remediated</div>
          </div>
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 print:bg-gray-50 print:border-gray-300 text-center">
            <div className="text-2xl font-bold font-mono text-rose-400 print:text-red-700">{report.critical_incidents}</div>
            <div className="text-xs text-slate-400 print:text-gray-600 uppercase font-semibold mt-1">Critical Alarms</div>
          </div>
        </div>

        {/* SOC Performance Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-5 rounded-xl bg-slate-950/40 border border-slate-800 print:border-gray-300 space-y-3">
            <h4 className="text-xs font-semibold text-slate-300 print:text-black uppercase tracking-wider flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              SLA & Threat Response Timing
            </h4>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between py-1 border-b border-slate-800 print:border-gray-200">
                <span className="text-slate-400 print:text-gray-600">Mean Time to Detect (MTTD):</span>
                <span className="text-cyan-300 font-bold">{report.threat_overview.mean_time_to_detect}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800 print:border-gray-200">
                <span className="text-slate-400 print:text-gray-600">Mean Time to Respond (MTTR):</span>
                <span className="text-emerald-400 font-bold">{report.threat_overview.mean_time_to_respond}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400 print:text-gray-600">MITRE ATT&CK Framework Coverage:</span>
                <span className="text-white font-bold">{report.threat_overview.mitre_coverage}</span>
              </div>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-slate-950/40 border border-slate-800 print:border-gray-300 space-y-3">
            <h4 className="text-xs font-semibold text-slate-300 print:text-black uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Severity Breakdown Distribution
            </h4>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between py-1 border-b border-slate-800 print:border-gray-200">
                <span className="text-rose-400 font-bold">Critical (Level 12+):</span>
                <span className="text-white">{report.severity_breakdown.critical}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800 print:border-gray-200">
                <span className="text-orange-400 font-bold">High (Level 8-11):</span>
                <span className="text-white">{report.severity_breakdown.high}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-amber-400 font-bold">Medium (Level 4-7):</span>
                <span className="text-white">{report.severity_breakdown.medium}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Top Affected Assets */}
        <div className="space-y-3">
          <h4 className="text-xs font-semibold text-slate-300 print:text-black uppercase tracking-wider flex items-center gap-2">
            <Server className="w-4 h-4 text-cyan-400" />
            Top Monitored Critical Assets
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 print:border-black text-slate-400 print:text-gray-700 uppercase font-semibold">
                  <th className="py-2.5 px-3">Asset Hostname</th>
                  <th className="py-2.5 px-3">IP Address</th>
                  <th className="py-2.5 px-3">Incidents Logged</th>
                  <th className="py-2.5 px-3 text-right">Defense Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 print:divide-gray-200 font-mono">
                {report.top_affected_assets.map((ast) => (
                  <tr key={ast.asset}>
                    <td className="py-2.5 px-3 text-white print:text-black font-semibold">{ast.asset}</td>
                    <td className="py-2.5 px-3 text-cyan-300 print:text-blue-900">{ast.ip}</td>
                    <td className="py-2.5 px-3 text-slate-300 print:text-black">{ast.incidents}</td>
                    <td className="py-2.5 px-3 text-right">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-sans">
                        {ast.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Graduation Project Sign-off */}
        <div className="pt-8 border-t border-slate-800 print:border-black flex flex-col sm:flex-row items-center justify-between gap-6 text-xs text-slate-400 print:text-black">
          <div>
            <p className="font-semibold text-slate-300 print:text-black">Supervised Graduation Project Examination</p>
            <p className="text-[11px] text-slate-500 print:text-gray-600">El Shorouk Academy &bull; Cybersecurity & Information Warfare</p>
          </div>
          <div className="flex gap-8 text-center">
            <div>
              <div className="w-32 border-b border-slate-600 print:border-black mb-1" />
              <span className="text-[10px] uppercase tracking-wider">Candidate Signature</span>
            </div>
            <div>
              <div className="w-32 border-b border-slate-600 print:border-black mb-1" />
              <span className="text-[10px] uppercase tracking-wider">Academic Supervisor</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
