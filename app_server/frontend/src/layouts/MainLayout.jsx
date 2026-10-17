import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';

export default function MainLayout({ wazuhStatus, onRefresh, isRefreshing, lastUpdated, autoRefreshSeconds }) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  const getPageTitle = (pathname) => {
    switch (pathname) {
      case '/dashboard':
        return { title: 'Security Operations Command Center', subtitle: 'Real-time telemetry, endpoint health, and active incident response' };
      case '/agents':
        return { title: 'Wazuh Monitored Endpoints', subtitle: 'Server & workstation agent inventory, status, and health telemetry' };
      case '/alerts':
        return { title: 'Security Alerts & Incident Logs', subtitle: 'SIEM/EDR rule detections, threat severity triage, and log investigation' };
      case '/threats':
        return { title: 'Threat Detection & Intelligence', subtitle: 'MITRE ATT&CK Matrix, File Integrity Monitoring (FIM), and Vulnerabilities' };
      case '/reports':
        return { title: 'SOC Analytics & Compliance Reports', subtitle: 'Executive summaries, compliance metrics, and automated CSV exports' };
      case '/about':
      case '/academy':
        return { title: 'El Shorouk Academy & Engineering Sectors', subtitle: 'Academic institutional background, Higher Institute of Engineering & department programs' };
      case '/settings':
        return { title: 'System Settings & Diagnostics', subtitle: 'User profile, preferences, and live Wazuh API connection health' };
      default:
        return { title: 'XDR Security Platform', subtitle: 'El Shorouk Academy Graduation Project' };
    }
  };

  const { title, subtitle } = getPageTitle(location.pathname);

  return (
    <div className="min-h-screen bg-[#070B14] flex">
      {/* Sidebar */}
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${collapsed ? 'md:ml-20' : 'md:ml-64'}`}>
        <Navbar
          title={title}
          subtitle={subtitle}
          wazuhStatus={wazuhStatus}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
          lastUpdated={lastUpdated}
          autoRefreshSeconds={autoRefreshSeconds}
        />
        <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
