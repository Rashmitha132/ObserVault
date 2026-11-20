// frontend/src/pages/NetworkPage.jsx
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useTheme } from '../context/ThemeContext';
import ChartCard from '../components/ChartCard';
import StatusBadge from '../components/StatusBadge';
import StatCard from '../components/StatCard';
import { 
  Activity, 
  Wifi, 
  WifiOff, 
  AlertTriangle, 
  RefreshCw, 
  ArrowDownUp, 
  Server,
  Network,
  Radio,
  CheckCircle2
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid 
} from 'recharts';

export default function NetworkPage() {
  const { isDark } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchNetwork = async () => {
    try {
      setLoading(true);
      const res = await api.getNetworkObservability();
      setData(res);
    } catch (err) {
      console.error('Failed to load network observability data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNetwork();
    const interval = setInterval(fetchNetwork, 10000);
    return () => clearInterval(interval);
  }, []);

  const { servers = [], trends = [], active_anomalies = [] } = data || {};

  // Compute metrics
  const avgLatency = servers.length > 0 
    ? (servers.reduce((acc, s) => acc + (s.latency_ms || 0), 0) / servers.length).toFixed(1)
    : '0.0';
  const degradedCount = servers.filter(s => s.status === 'degraded').length;

  const gridStroke = isDark ? '#1e293b' : '#f1f5f9';
  const axisStroke = isDark ? '#64748b' : '#94a3b8';
  const tooltipBg = isDark ? '#0b1120' : '#ffffff';
  const tooltipBorder = isDark ? '#334155' : '#e2e8f0';
  const tooltipColor = isDark ? '#f8fafc' : '#0f172a';

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 dark:border-white/5 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            Network Observability & Mesh Transport
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time latency distribution, packet loss diagnostics, and route anomaly detection.
          </p>
        </div>
        <button 
          onClick={fetchNetwork}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 transition shadow-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Metrics
        </button>
      </div>

      {/* Network KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard 
          title="Avg Latency (RTT)"
          value={`${avgLatency} ms`}
          subtitle="Nominal threshold < 120ms"
          icon={Activity}
          color={Number(avgLatency) > 120 ? 'amber' : 'emerald'}
          badge={Number(avgLatency) > 120 ? 'Elevated' : 'Optimal'}
        />
        <StatCard 
          title="Monitored Interfaces"
          value={servers.length}
          subtitle="Active edge network endpoints"
          icon={Network}
          color="cyan"
          badge="100% Bound"
        />
        <StatCard 
          title="Active Anomalies"
          value={active_anomalies.length}
          subtitle="Network route breaches"
          icon={AlertTriangle}
          color={active_anomalies.length > 0 ? 'rose' : 'emerald'}
          badge={active_anomalies.length > 0 ? 'Attention' : 'Zero'}
        />
        <StatCard 
          title="Degraded Paths"
          value={degradedCount}
          subtitle="Experiencing packet loss or latency"
          icon={WifiOff}
          color={degradedCount > 0 ? 'amber' : 'emerald'}
          badge={degradedCount > 0 ? `${degradedCount} Degraded` : 'All Optimal'}
        />
      </div>

      {/* Network Anomaly Banner (if active) */}
      {active_anomalies.length > 0 && (
        <div className="p-4 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-500/30 flex items-start gap-3.5 text-amber-900 dark:text-amber-300 shadow-sm">
          <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-xs font-bold uppercase tracking-wider">
              {active_anomalies.length} Active Network Transport Anomalies Detected
            </h4>
            <p className="text-xs text-amber-800/80 dark:text-amber-200/80 leading-relaxed">
              Elevated round-trip latency or packet loss conditions detected across one or more monitored interfaces. Correlating route paths for packet drops.
            </p>
          </div>
        </div>
      )}

      {/* Trends Chart */}
      <ChartCard 
        title="Network Transport Performance History" 
        subtitle="Continuous round-trip latency (ms) and packet drop rate (%)"
        badge="Edge Ping Verified"
      >
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trends}>
              <defs>
                <linearGradient id="latGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.45}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis dataKey="time" stroke={axisStroke} tick={{ fontSize: 11 }} />
              <YAxis stroke={axisStroke} tick={{ fontSize: 11 }} unit="ms" />
              <Tooltip contentStyle={{ 
                backgroundColor: tooltipBg, 
                borderColor: tooltipBorder, 
                color: tooltipColor,
                borderRadius: '0.75rem', 
                fontSize: '12px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
              }} />
              <Area type="monotone" dataKey="latency_ms" name="Latency (ms)" stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#latGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      {/* Server Interfaces Breakdown Grid */}
      <div className="glass-card rounded-2xl p-5 sm:p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/5 pb-3">
          <div>
            <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">Interface Connectivity & Routing Status</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Per-node edge networking health</p>
          </div>
          <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
            {servers.length} Connected Nodes
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {servers.map((s) => (
            <div key={s.id} className="p-4 rounded-xl bg-slate-50/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-white/5 hover:border-cyan-500/40 transition space-y-3 shadow-2xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-bold text-slate-900 dark:text-white">{s.display_name}</span>
                </div>
                <StatusBadge status={s.status} size="xs" />
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-slate-200/60 dark:border-white/5">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">RTT Latency</span>
                  <p className={`font-mono font-bold text-sm ${s.latency_ms > 120 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                    {s.latency_ms} ms
                  </p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Packet Loss</span>
                  <p className={`font-mono font-bold text-sm ${s.packet_loss_percent > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-700 dark:text-slate-300'}`}>
                    {s.packet_loss_percent}%
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 font-mono pt-1">
                <span>{s.ip_address}</span>
                {s.is_simulated && (
                  <span className="px-1.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20 text-[9px] font-bold">
                    Simulated
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
