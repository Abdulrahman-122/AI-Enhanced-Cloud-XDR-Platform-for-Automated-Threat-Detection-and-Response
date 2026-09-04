import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { authService } from './services/authService';
import { dashboardService } from './services/dashboardService';
import MainLayout from './layouts/MainLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Agents from './pages/Agents';
import SecurityAlerts from './pages/SecurityAlerts';
import ThreatDetection from './pages/ThreatDetection';
import Reports from './pages/Reports';
import AboutAcademy from './pages/AboutAcademy';
import Settings from './pages/Settings';

// Protected Route Guard
function ProtectedRoute({ children }) {
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [autoRefreshSeconds, setAutoRefreshSeconds] = useState(30);

  const fetchDashboardData = useCallback(async () => {
    if (!authService.isAuthenticated()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await dashboardService.getOverview();
      setDashboardData(data);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      console.error(err);
      setError('Wazuh service telemetry is currently unreachable or initializing.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch on mount
  useEffect(() => {
    if (authService.isAuthenticated()) {
      fetchDashboardData();
    }
  }, [fetchDashboardData]);

  // Auto-refresh timer
  useEffect(() => {
    if (!autoRefreshSeconds || autoRefreshSeconds <= 0) return;
    const interval = setInterval(() => {
      fetchDashboardData();
    }, autoRefreshSeconds * 1000);
    return () => clearInterval(interval);
  }, [autoRefreshSeconds, fetchDashboardData]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Login Route */}
        <Route
          path="/login"
          element={
            authService.isAuthenticated() ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <Login onLoginSuccess={fetchDashboardData} />
            )
          }
        />

        {/* Public Standalone About Academy Route for direct access / visitors */}
        <Route
          path="/academy"
          element={
            <div className="min-h-screen bg-[#070B14] p-6 md:p-10 max-w-7xl mx-auto">
              <AboutAcademy />
            </div>
          }
        />

        {/* Protected Application Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MainLayout
                wazuhStatus={dashboardData?.wazuh_status}
                onRefresh={fetchDashboardData}
                isRefreshing={loading}
                lastUpdated={lastUpdated}
                autoRefreshSeconds={autoRefreshSeconds}
              />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route
            path="dashboard"
            element={
              <Dashboard
                data={dashboardData}
                loading={loading}
                error={error}
                onRefresh={fetchDashboardData}
              />
            }
          />
          <Route path="agents" element={<Agents />} />
          <Route path="alerts" element={<SecurityAlerts />} />
          <Route path="threats" element={<ThreatDetection />} />
          <Route path="reports" element={<Reports />} />
          <Route path="about" element={<AboutAcademy />} />
          <Route
            path="settings"
            element={
              <Settings
                autoRefreshSeconds={autoRefreshSeconds}
                setAutoRefreshSeconds={setAutoRefreshSeconds}
              />
            }
          />
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
