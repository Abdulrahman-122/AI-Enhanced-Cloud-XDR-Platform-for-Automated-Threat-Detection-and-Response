import React, { useState, useEffect } from 'react';
import { settingsService } from '../services/settingsService';
import { authService } from '../services/authService';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import { Settings as SettingsIcon, User, Lock, Activity, Wifi, Shield, Save, CheckCircle2, Clock, Volume2, Bell } from 'lucide-react';

export default function Settings({ autoRefreshSeconds, setAutoRefreshSeconds }) {
  const user = authService.getStoredUser() || {};
  const [fullName, setFullName] = useState(user.full_name || '');
  const [email, setEmail] = useState(user.email || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState('');
  const [profileError, setProfileError] = useState('');

  // Diagnostics
  const [diagnostics, setDiagnostics] = useState(null);
  const [diagLoading, setDiagLoading] = useState(true);
  const [diagError, setDiagError] = useState(null);

  // Preference states
  const [soundAlerts, setSoundAlerts] = useState(true);
  const [toastAlerts, setToastAlerts] = useState(true);

  const fetchDiagnostics = async () => {
    setDiagLoading(true);
    setDiagError(null);
    try {
      const res = await settingsService.getDiagnostics();
      setDiagnostics(res);
    } catch (err) {
      console.error(err);
      setDiagError('Failed to fetch system diagnostics.');
    } finally {
      setDiagLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    setProfileLoading(true);
    setProfileSuccess('');
    setProfileError('');

    try {
      const payload = {
        full_name: fullName,
        email: email,
      };
      if (newPassword) {
        payload.current_password = currentPassword;
        payload.new_password = newPassword;
      }
      await settingsService.updateProfile(payload);
      setProfileSuccess('Profile and security credentials updated successfully!');
      setCurrentPassword('');
      setNewPassword('');
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail;
      setProfileError(typeof detail === 'string' ? detail : 'Failed to update profile settings.');
    } finally {
      setProfileLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Diagnostics Panel */}
      <div className="cyber-card rounded-2xl p-6">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wide">
              Wazuh API & System Infrastructure Diagnostics
            </h3>
          </div>
          <button
            onClick={fetchDiagnostics}
            disabled={diagLoading}
            className="text-xs text-cyan-400 hover:underline font-mono"
          >
            {diagLoading ? 'Testing...' : 'Re-test Connection'}
          </button>
        </div>

        {diagLoading && !diagnostics ? (
          <div className="py-6 text-center text-xs text-slate-400 font-mono">
            Running connectivity probes against backend and Wazuh server...
          </div>
        ) : diagnostics ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Wazuh Server Status:</span>
                <span className={`font-bold ${diagnostics.wazuh_connected ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {diagnostics.wazuh_connected ? 'Connected & Active' : 'Simulation Telemetry Active'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Wazuh Endpoint:</span>
                <span className="text-cyan-300 truncate max-w-[200px]">{diagnostics.wazuh_endpoint}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Wazuh Version:</span>
                <span className="text-slate-200">{diagnostics.wazuh_version}</span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Database Engine:</span>
                <span className="text-emerald-400 font-bold">{diagnostics.database_status}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Platform Build:</span>
                <span className="text-cyan-300 font-bold">XDR v{diagnostics.app_version}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">JWT Security Token:</span>
                <span className="text-slate-200">{diagnostics.jwt_status}</span>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Preferences Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* User Profile Form */}
        <div className="cyber-card rounded-2xl p-6">
          <div className="flex items-center gap-2.5 pb-4 mb-4 border-b border-slate-800">
            <User className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wide">
              SOC Analyst Profile & Credentials
            </h3>
          </div>

          {profileSuccess && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{profileSuccess}</span>
            </div>
          )}

          {profileError && (
            <div className="mb-4 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{profileError}</span>
            </div>
          )}

          <form onSubmit={handleProfileUpdate} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-cyan-400 font-sans"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1.5">
                Official Academy Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-cyan-400 font-mono"
              />
            </div>

            <div className="pt-2 border-t border-slate-800 space-y-3">
              <p className="text-[11px] text-slate-400 font-medium">Change Password (Optional)</p>
              <div>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Current password"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
              <div>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="New password (min 6 chars)"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={profileLoading}
              className="w-full mt-2 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-bold uppercase tracking-wider shadow-glow-cyan flex items-center justify-center gap-2 transition disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{profileLoading ? 'Updating...' : 'Save Profile Changes'}</span>
            </button>
          </form>
        </div>

        {/* SOC Dashboard Preferences */}
        <div className="cyber-card rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 pb-4 mb-4 border-b border-slate-800">
              <SettingsIcon className="w-5 h-5 text-cyan-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wide">
                SOC Stream & Refresh Preferences
              </h3>
            </div>

            <div className="space-y-5 text-xs">
              {/* Auto Refresh Interval */}
              <div>
                <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-2 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-cyan-400" />
                  Auto-Refresh Polling Interval
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { label: 'Off', val: 0 },
                    { label: '10s', val: 10 },
                    { label: '30s', val: 30 },
                    { label: '60s', val: 60 }
                  ].map((opt) => (
                    <button
                      key={opt.label}
                      type="button"
                      onClick={() => setAutoRefreshSeconds(opt.val)}
                      className={`py-2 rounded-xl font-mono font-bold transition ${
                        autoRefreshSeconds === opt.val
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                          : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Notification Toggles */}
              <div className="pt-4 border-t border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-cyan-400" />
                    <span className="text-slate-200 font-medium">Critical Incident Audio Alerts</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={soundAlerts}
                    onChange={(e) => setSoundAlerts(e.target.checked)}
                    className="w-4 h-4 accent-cyan-500 cursor-pointer"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bell className="w-4 h-4 text-cyan-400" />
                    <span className="text-slate-200 font-medium">Desktop SOC Threat Popups</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={toastAlerts}
                    onChange={(e) => setToastAlerts(e.target.checked)}
                    className="w-4 h-4 accent-cyan-500 cursor-pointer"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 font-mono">
            Credentials and JWT authorization keys are secured in backend environment and never exposed in the browser.
          </div>
        </div>
      </div>
    </div>
  );
}
