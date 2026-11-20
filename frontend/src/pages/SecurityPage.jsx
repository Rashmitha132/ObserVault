// frontend/src/pages/SecurityPage.jsx
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import StatCard from '../components/StatCard';
import { 
  ShieldAlert, 
  Lock, 
  KeyRound, 
  AlertTriangle, 
  CheckCircle, 
  Server, 
  Clock, 
  RefreshCw,
  EyeOff,
  ShieldCheck,
  Search,
  CheckCircle2
} from 'lucide-react';

export default function SecurityPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchSecurity = async () => {
    try {
      setLoading(true);
      const res = await api.getSecurityEvents();
      setData(res);
    } catch (err) {
      console.error('Failed to load security events', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSecurity();
  }, []);

  const { summary, servers = [], timeline = [], alerts = [] } = data || {};

  const filteredTimeline = timeline.filter(item => 
    !searchTerm || 
    item.server_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.event_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800/40">
              <ShieldAlert className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Security Observability & Auth Anomalies
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Privacy-preserving authentication telemetry. High-level statistical metadata is transmitted; credentials never leave the host.
          </p>
        </div>
        <button 
          onClick={fetchSecurity}
          disabled={loading}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 transition shadow-xs active:scale-[0.98] disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-500' : ''}`} />
          Refresh Security Feed
        </button>
      </div>

      {/* Critical Zero-Credential Assurance Banner */}
      <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-indigo-50 via-purple-50/50 to-blue-50 dark:from-indigo-950/50 dark:via-purple-950/30 dark:to-slate-950/50 border border-indigo-200/80 dark:border-indigo-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-soft">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-600/20 shrink-0">
            <EyeOff className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-900 dark:text-indigo-300">
                ObserveVault Privacy-Preserving Security Architecture
              </h3>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30">
                Zero Raw Logs / Zero Credentials Stored
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed max-w-3xl">
              Unlike legacy monitoring tools that transmit raw auth payloads (which can expose usernames, passwords, authorization tokens, or session headers), ObserveVault aggregates authentication attempts strictly at the local edge daemon. The central SaaS receives only high-level counts, rates, and timestamps.
            </p>
          </div>
        </div>
      </div>

      {/* Security Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
        <StatCard
          title="Total Failed Logins"
          value={summary?.total_failed_logins_recorded || 0}
          subtitle="Aggregated across all monitored endpoints"
          icon={KeyRound}
          color="purple"
        />
        <StatCard
          title="Nodes with Auth Failures"
          value={summary?.servers_with_auth_failures || 0}
          subtitle="Under local rate-limiting protection"
          icon={Server}
          color="amber"
        />
        <StatCard
          title="Active Security Alerts"
          value={alerts.length}
          subtitle="Repeated brute-force threshold breaches"
          icon={ShieldAlert}
          color="rose"
        />
      </div>

      {/* Security Alerts Table */}
      <div className="glass-card rounded-2xl p-5 sm:p-6 shadow-soft space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Security Event Alerts</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Automated threshold breaches triggered by statistical auth counts
            </p>
          </div>
          <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            {alerts.length} Flagged
          </span>
        </div>

        <div className="space-y-3">
          {alerts.length === 0 ? (
            <div className="py-8 text-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2 opacity-80" />
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
                No active authentication anomaly alerts. All endpoints nominal.
              </p>
            </div>
          ) : (
            alerts.map((al) => (
              <div 
                key={al.id} 
                className="p-4 rounded-xl bg-slate-50/80 dark:bg-slate-900/60 border border-rose-200 dark:border-rose-500/20 flex flex-col md:flex-row md:items-center justify-between gap-3 transition hover:border-rose-300 dark:hover:border-rose-500/40"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={al.severity} size="xs" />
                    <h4 className="text-xs font-bold text-slate-900 dark:text-white">{al.title}</h4>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Observed Failures: <code className="text-rose-600 dark:text-rose-400 font-bold">{al.observed_count} attempts</code> (Configured Threshold: {al.threshold})
                  </p>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                  <span className="font-mono text-[11px]">{new Date(al.created_at).toLocaleString()}</span>
                  <StatusBadge status={al.status} size="xs" />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Event Timeline Table */}
      <div className="glass-card rounded-2xl p-5 sm:p-6 shadow-soft space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800/80 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Privacy-Preserving Auth Audit Log</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Statistical event stream with deduplication IDs</p>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by server or event ID..."
              className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 dark:bg-slate-900/80 text-slate-600 dark:text-slate-400 font-mono text-[10px] uppercase border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Event ID</th>
                <th className="py-2.5 px-3 font-semibold">Timestamp</th>
                <th className="py-2.5 px-3 font-semibold">Failed Attempts</th>
                <th className="py-2.5 px-3 font-semibold">Target Server</th>
                <th className="py-2.5 px-3 font-semibold">Privacy Guarantee</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
              {filteredTimeline.length === 0 ? (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-400 dark:text-slate-500 font-sans">
                    No failed authentication attempts registered matching query.
                  </td>
                </tr>
              ) : (
                filteredTimeline.map((item) => (
                  <tr key={item.event_id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-300">{item.event_id.slice(0, 16)}...</td>
                    <td className="py-2.5 px-3 text-slate-500 dark:text-slate-400">{new Date(item.timestamp).toLocaleTimeString()}</td>
                    <td className="py-2.5 px-3 text-rose-600 dark:text-rose-400 font-bold">{item.failed_attempts}</td>
                    <td className="py-2.5 px-3 text-slate-700 dark:text-slate-200 font-sans font-medium">{item.server_id}</td>
                    <td className="py-2.5 px-3 text-emerald-600 dark:text-emerald-400 font-sans text-[11px] flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                      <span>{item.privacy_guarantee}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
