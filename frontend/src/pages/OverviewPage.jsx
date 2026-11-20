// frontend/src/pages/OverviewPage.jsx
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useTheme } from '../context/ThemeContext';
import StatCard from '../components/StatCard';
import ChartCard from '../components/ChartCard';
import StatusBadge from '../components/StatusBadge';
import PrivacyFlowGraphic from '../components/PrivacyFlowGraphic';
import { 
  Server, 
  Cpu, 
  AlertTriangle, 
  Activity, 
  ShieldCheck, 
  Radio, 
  Lock, 
  EyeOff,
  Sparkles,
  ArrowUpRight,
  CheckCircle2,
  TrendingUp,
  Clock
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid,
  LineChart,
  Line
} from 'recharts';

export default function OverviewPage() {
  const { isDark } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchOverview = async () => {
    try {
      setLoading(true);
      const res = await api.getDashboardOverview();
      setData(res);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load dashboard overview');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
    const interval = setInterval(fetchOverview, 8000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">
            Loading infrastructure telemetry...
          </p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-6 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-500/30 text-rose-800 dark:text-rose-300 space-y-3">
        <h3 className="font-bold text-sm">Failed to connect to SaaS backend</h3>
        <p className="text-xs">{error}</p>
        <button 
          onClick={fetchOverview}
          className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-xs text-white font-semibold transition"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const { infrastructure, collectors, alerts, incidents, privacy, trends, recent_alerts, recent_incidents } = data || {};

  // Theme-aware chart colors
  const gridStroke = isDark ? '#1e293b' : '#f1f5f9';
  const axisStroke = isDark ? '#64748b' : '#94a3b8';
  const tooltipBg = isDark ? '#0b1120' : '#ffffff';
  const tooltipBorder = isDark ? '#334155' : '#e2e8f0';
  const tooltipColor = isDark ? '#f8fafc' : '#0f172a';

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Header & System Health Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 dark:border-white/5 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Infrastructure & Observability Command
            </h1>
            <span className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-500/30">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              All Systems Operational
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time telemetry, automated anomaly correlation, and edge-sanitized privacy verification.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 shadow-xs">
            <Radio className="w-3.5 h-3.5 text-cyan-500 animate-pulse" />
            <span className="font-semibold">Live Ingestion Active</span>
          </span>
        </div>
      </div>

      {/* Primary HUD Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard 
          title="Monitored Servers"
          value={infrastructure?.total_servers || 0}
          subtitle={`${infrastructure?.healthy || 0} Healthy • ${infrastructure?.warning || 0} Warning • ${infrastructure?.critical || 0} Critical`}
          icon={Server}
          color="cyan"
          badge={`${infrastructure?.healthy || 0} Healthy`}
        />
        <StatCard 
          title="Edge Collectors"
          value={`${collectors?.online || 0} / ${collectors?.total || 0}`}
          subtitle={`${collectors?.buffered_records || 0} Staged in Local SQLite`}
          icon={Cpu}
          color="emerald"
          badge={collectors?.offline > 0 ? `${collectors.offline} Offline` : 'All Online'}
        />
        <StatCard 
          title="Active Alerts"
          value={alerts?.active_total || 0}
          subtitle={`${alerts?.critical || 0} Critical severity breaches`}
          icon={AlertTriangle}
          color={alerts?.critical > 0 ? 'rose' : 'amber'}
          badge={alerts?.critical > 0 ? 'Action Req' : 'Nominal'}
        />
        <StatCard 
          title="Correlated Incidents"
          value={incidents?.active_total || 0}
          subtitle="Multi-signal root cause incidents"
          icon={Activity}
          color="indigo"
          badge="Automated"
        />
      </div>

      {/* Privacy & Egress Proof HUD Banner (Core USP) */}
      <div className="glass-card rounded-2xl p-5 border border-cyan-500/30 bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-purple-50/70 dark:from-slate-900/90 dark:via-cyan-950/20 dark:to-slate-900/90 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-cyan-100 text-cyan-800 dark:bg-cyan-950/80 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-500/40 shadow-sm shrink-0">
            <EyeOff className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-900 dark:text-white">Tier-1 Privacy Layer Proof</span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-cyan-100 text-cyan-800 border border-cyan-200 dark:bg-cyan-950 dark:text-cyan-400 dark:border-cyan-500/30">
                ZERO CLOUD LEAK
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
              Original logs and credentials remain 100% on-premises. Only strictly approved statistical metadata reaches this dashboard.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-6 text-xs">
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Processed Locally</p>
            <p className="text-lg font-mono font-bold text-slate-900 dark:text-slate-200">{privacy?.records_processed_locally || 0}</p>
          </div>
          <div className="h-8 w-px bg-slate-200 dark:bg-white/10" />
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Approved Outbound</p>
            <p className="text-lg font-mono font-bold text-emerald-600 dark:text-emerald-400">{privacy?.records_approved_outbound || 0}</p>
          </div>
          <div className="h-8 w-px bg-slate-200 dark:bg-white/10" />
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Sensitive Fields Stripped</p>
            <p className="text-lg font-mono font-bold text-cyan-600 dark:text-cyan-400">{privacy?.sensitive_fields_rejected || 0}</p>
          </div>
        </div>
      </div>

      {/* Visual Architectural Data Flow */}
      <PrivacyFlowGraphic />

      {/* Live Metric Trend Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard 
          title="Compute Resource Utilisation Trends" 
          subtitle="Real-time multi-host CPU and memory telemetry"
          badge="Live P95"
        >
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends || []}>
                <defs>
                  <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.45}/>
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.45}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                <XAxis dataKey="time" stroke={axisStroke} tick={{ fontSize: 11 }} />
                <YAxis stroke={axisStroke} domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: tooltipBg, 
                    borderColor: tooltipBorder, 
                    color: tooltipColor,
                    borderRadius: '0.75rem', 
                    fontSize: '12px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)' 
                  }}
                />
                <Area type="monotone" dataKey="cpu" name="CPU Utilisation (%)" stroke="#0ea5e9" strokeWidth={2.5} fillOpacity={1} fill="url(#cpuGrad)" />
                <Area type="monotone" dataKey="memory" name="Memory Utilisation (%)" stroke="#6366f1" strokeWidth={2.5} fillOpacity={1} fill="url(#memGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard 
          title="Network Latency & Packet Loss Stability" 
          subtitle="Round-trip transport latency and connection stability"
          badge="TCP RTT"
        >
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends || []}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                <XAxis dataKey="time" stroke={axisStroke} tick={{ fontSize: 11 }} />
                <YAxis stroke={axisStroke} tick={{ fontSize: 11 }} unit="ms" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: tooltipBg, 
                    borderColor: tooltipBorder, 
                    color: tooltipColor,
                    borderRadius: '0.75rem', 
                    fontSize: '12px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)' 
                  }}
                />
                <Line type="monotone" dataKey="latency" name="Round-Trip Latency (ms)" stroke="#10b981" strokeWidth={2.5} dot={false} />
                <Line type="monotone" dataKey="packet_loss" name="Packet Loss (%)" stroke="#f43f5e" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>

      {/* Lower Dual Tables: Recent Incidents & Recent Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Correlated Incidents */}
        <div className="glass-card rounded-2xl p-5 sm:p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/5 pb-3">
            <div>
              <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">Active Correlated Incidents</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Automated multi-signal root-cause groupings</p>
            </div>
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-500/30">
              {recent_incidents?.length || 0} Open
            </span>
          </div>

          <div className="space-y-2.5">
            {(!recent_incidents || recent_incidents.length === 0) ? (
              <p className="text-xs text-slate-500 dark:text-slate-400 py-8 text-center">
                No active correlated incidents. Infrastructure healthy.
              </p>
            ) : (
              recent_incidents.map((inc) => (
                <div key={inc.id} className="p-3.5 rounded-xl bg-slate-50/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-white/5 hover:border-cyan-500/40 transition space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400">{inc.code}</span>
                    <StatusBadge status={inc.severity} size="xs" />
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-200">{inc.title}</h4>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-200/60 dark:border-white/5">
                    <span>Confidence: {(inc.confidence_score * 100).toFixed(0)}%</span>
                    <span>{new Date(inc.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="glass-card rounded-2xl p-5 sm:p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/5 pb-3">
            <div>
              <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">Recent Telemetry Breaches</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Threshold triggers with deduplication</p>
            </div>
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700">
              {recent_alerts?.length || 0} Total
            </span>
          </div>

          <div className="space-y-2.5">
            {(!recent_alerts || recent_alerts.length === 0) ? (
              <p className="text-xs text-slate-500 dark:text-slate-400 py-8 text-center">
                No active alerts recorded.
              </p>
            ) : (
              recent_alerts.map((al) => (
                <div key={al.id} className="p-3 rounded-xl bg-slate-50/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-white/5 flex items-center justify-between gap-3">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <StatusBadge status={al.severity} size="xs" />
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-200">{al.title}</span>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-400">
                      Metric: <code className="text-cyan-600 dark:text-cyan-400 font-bold">{al.metric_name}</code> ({al.observed_value} vs limit {al.threshold_value})
                    </p>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 shrink-0">
                    {new Date(al.created_at).toLocaleTimeString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
