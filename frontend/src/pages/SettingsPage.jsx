// frontend/src/pages/SettingsPage.jsx
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useTheme } from '../context/ThemeContext';
import { 
  Building2, 
  Users, 
  Sliders, 
  Cpu, 
  Check, 
  AlertCircle, 
  Save, 
  RefreshCw,
  ShieldCheck,
  Lock,
  Mail,
  UserCheck,
  Sun,
  Moon,
  Laptop,
  CheckCircle2
} from 'lucide-react';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Editable threshold states
  const [cpuThreshold, setCpuThreshold] = useState(90.0);
  const [memoryThreshold, setMemoryThreshold] = useState(90.0);
  const [diskThreshold, setDiskThreshold] = useState(85.0);
  const [latencyThreshold, setLatencyThreshold] = useState(120.0);
  const [failedLoginThreshold, setFailedLoginThreshold] = useState(3);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const res = await api.getTenantSettings();
      setSettings(res);
      if (res.tenant?.thresholds) {
        setCpuThreshold(res.tenant.thresholds.cpu_threshold ?? 90.0);
        setMemoryThreshold(res.tenant.thresholds.memory_threshold ?? 90.0);
        setDiskThreshold(res.tenant.thresholds.disk_threshold ?? 85.0);
        setLatencyThreshold(res.tenant.thresholds.latency_threshold_ms ?? 120.0);
        setFailedLoginThreshold(res.tenant.thresholds.failed_login_threshold ?? 3);
      }
    } catch (err) {
      console.error('Failed to load tenant settings', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSaveThresholds = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFeedback(null);
    try {
      await api.updateTenantSettings({
        cpu_threshold: parseFloat(cpuThreshold),
        memory_threshold: parseFloat(memoryThreshold),
        disk_threshold: parseFloat(diskThreshold),
        latency_threshold_ms: parseFloat(latencyThreshold),
        failed_login_threshold: parseInt(failedLoginThreshold)
      });
      setFeedback({ type: 'success', text: 'Threshold parameters updated and live across anomaly engine.' });
      await fetchSettings();
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Failed to update threshold parameters' });
    } finally {
      setSaving(false);
    }
  };

  if (loading && !settings) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          Loading organisation settings...
        </div>
      </div>
    );
  }

  const { tenant, users = [], collectors_count = 0 } = settings || {};

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-cyan-50 dark:bg-cyan-950/60 text-cyan-600 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-800/40">
              <Building2 className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Organisation Profile & System Preferences
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Configure tenant-isolated detection thresholds, manage display themes, and review authorized user access.
          </p>
        </div>
      </div>

      {/* Tenant Profile Banner */}
      <div className="glass-card rounded-2xl p-6 shadow-soft flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div className="flex items-center gap-4">
          <div className="p-3.5 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20">
            <Building2 className="w-7 h-7" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">{tenant?.name}</h2>
              <span className="text-[10px] font-mono font-semibold px-2.5 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950 text-cyan-800 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-500/30 uppercase">
                {tenant?.plan}
              </span>
            </div>
            <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
              Slug: <span className="text-slate-700 dark:text-slate-300">{tenant?.slug}</span> • Tenant ID: <span className="text-slate-700 dark:text-slate-300">{tenant?.id}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6 text-xs font-mono text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-950/50 p-3 rounded-2xl border border-slate-200/80 dark:border-slate-800/80">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400">Enrolled Users</span>
            <p className="text-base font-bold text-slate-900 dark:text-slate-200">{users.length}</p>
          </div>
          <div className="h-7 w-px bg-slate-200 dark:bg-slate-800" />
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400">Active Collectors</span>
            <p className="text-base font-bold text-cyan-600 dark:text-cyan-400">{collectors_count}</p>
          </div>
        </div>
      </div>

      {/* APPEARANCE & THEME PREFERENCE (LIGHT / DARK / SYSTEM) */}
      <div className="glass-card rounded-2xl p-6 shadow-soft space-y-4">
        <div className="border-b border-slate-100 dark:border-slate-800/80 pb-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Sun className="w-4 h-4 text-amber-500" />
            Appearance & Visual Theme
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Choose your preferred display theme. Your selection persists across browser refreshes and sessions.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Light Mode Card */}
          <button
            type="button"
            onClick={() => setTheme('light')}
            className={`p-4 rounded-2xl border text-left transition-all duration-200 ${
              theme === 'light'
                ? 'border-cyan-500 ring-2 ring-cyan-500/20 bg-cyan-50/30 dark:bg-slate-900 shadow-md shadow-cyan-500/10'
                : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-slate-50/50 dark:bg-slate-950/40'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 rounded-xl bg-amber-100 text-amber-600">
                <Sun className="w-5 h-5" />
              </div>
              {theme === 'light' && (
                <CheckCircle2 className="w-5 h-5 text-cyan-600" />
              )}
            </div>
            <h4 className="text-xs font-bold text-slate-900 dark:text-white">Light Mode</h4>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
              Clean white & lavender gradients, soft blue accents, and optimal daytime readability.
            </p>
          </button>

          {/* Dark Mode Card */}
          <button
            type="button"
            onClick={() => setTheme('dark')}
            className={`p-4 rounded-2xl border text-left transition-all duration-200 ${
              theme === 'dark'
                ? 'border-cyan-500 ring-2 ring-cyan-500/20 bg-cyan-50/30 dark:bg-slate-900 shadow-md shadow-cyan-500/10'
                : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-slate-50/50 dark:bg-slate-950/40'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 rounded-xl bg-indigo-950 text-cyan-400 border border-indigo-800">
                <Moon className="w-5 h-5" />
              </div>
              {theme === 'dark' && (
                <CheckCircle2 className="w-5 h-5 text-cyan-400" />
              )}
            </div>
            <h4 className="text-xs font-bold text-slate-900 dark:text-white">Dark Mode</h4>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
              Deep navy and charcoal surfaces, glowing status indicators, and reduced eye strain.
            </p>
          </button>

          {/* System Mode Card */}
          <button
            type="button"
            onClick={() => setTheme('system')}
            className={`p-4 rounded-2xl border text-left transition-all duration-200 ${
              theme === 'system'
                ? 'border-cyan-500 ring-2 ring-cyan-500/20 bg-cyan-50/30 dark:bg-slate-900 shadow-md shadow-cyan-500/10'
                : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-slate-50/50 dark:bg-slate-950/40'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 rounded-xl bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                <Laptop className="w-5 h-5" />
              </div>
              {theme === 'system' && (
                <CheckCircle2 className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
              )}
            </div>
            <h4 className="text-xs font-bold text-slate-900 dark:text-white">System Preference</h4>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
              Automatically synchronize with your operating system light and dark schedule.
            </p>
          </button>
        </div>
      </div>

      {/* Configurable Anomaly Thresholds Form */}
      <form onSubmit={handleSaveThresholds} className="glass-card rounded-2xl p-6 shadow-soft space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800/80 pb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              Configurable Detection Thresholds
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Fine-tune the threshold parameters that trigger explainable anomalies and alert deduplication.
            </p>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs shadow-md shadow-cyan-500/20 transition disabled:opacity-50 active:scale-[0.99] w-fit"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? 'Updating...' : 'Save Parameters'}</span>
          </button>
        </div>

        {feedback && (
          <div className={`p-3.5 rounded-xl text-xs border ${
            feedback.type === 'success' 
              ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30' 
              : 'bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border-rose-200 dark:border-rose-500/30'
          }`}>
            {feedback.text}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
              CPU Utilisation Limit (%)
            </label>
            <input 
              type="number" 
              step="1"
              min="10"
              max="99"
              value={cpuThreshold}
              onChange={(e) => setCpuThreshold(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
            />
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Default: 90% (Triggers High CPU alert)</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
              Memory Utilisation Limit (%)
            </label>
            <input 
              type="number" 
              step="1"
              min="10"
              max="99"
              value={memoryThreshold}
              onChange={(e) => setMemoryThreshold(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
            />
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Default: 90% (Triggers High Memory alert)</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
              Storage Disk Limit (%)
            </label>
            <input 
              type="number" 
              step="1"
              min="10"
              max="99"
              value={diskThreshold}
              onChange={(e) => setDiskThreshold(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
            />
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Default: 85% (Triggers Disk Capacity alert)</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
              Latency Threshold (ms)
            </label>
            <input 
              type="number" 
              step="5"
              min="10"
              max="2000"
              value={latencyThreshold}
              onChange={(e) => setLatencyThreshold(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
            />
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Default: 120ms (Triggers Network Latency alert)</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
              Failed Login Attempt Limit
            </label>
            <input 
              type="number" 
              step="1"
              min="1"
              max="50"
              value={failedLoginThreshold}
              onChange={(e) => setFailedLoginThreshold(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:border-cyan-500"
            />
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Default: 3 attempts (Triggers Auth Spike alert)</p>
          </div>
        </div>
      </form>

      {/* User Directory Table */}
      <div className="glass-card rounded-2xl p-6 shadow-soft space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              Tenant User Directory & Roles
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Authorized users with tenant-isolated access rights</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 dark:bg-slate-900/80 text-slate-600 dark:text-slate-400 font-mono text-[10px] uppercase border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Full Name</th>
                <th className="py-2.5 px-3 font-semibold">Email Address</th>
                <th className="py-2.5 px-3 font-semibold">Role</th>
                <th className="py-2.5 px-3 font-semibold">Status</th>
                <th className="py-2.5 px-3 font-semibold">Enrolled At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                  <td className="py-3 px-3 font-bold text-slate-900 dark:text-white">{u.full_name}</td>
                  <td className="py-3 px-3 font-mono text-slate-600 dark:text-slate-300">{u.email}</td>
                  <td className="py-3 px-3">
                    <span className="text-[10px] font-mono uppercase px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-cyan-700 dark:text-cyan-300 border border-slate-200 dark:border-slate-700 font-bold">
                      {u.role}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      Active
                    </span>
                  </td>
                  <td className="py-3 px-3 text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
