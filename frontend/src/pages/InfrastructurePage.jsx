// frontend/src/pages/InfrastructurePage.jsx
import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../services/api';
import { useTheme } from '../context/ThemeContext';
import StatusBadge from '../components/StatusBadge';
import ChartCard from '../components/ChartCard';
import StatCard from '../components/StatCard';
import { 
  Server, 
  Search, 
  Filter, 
  ExternalLink, 
  RefreshCw, 
  Cpu, 
  HardDrive, 
  Activity, 
  X,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Radio
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid 
} from 'recharts';

export default function InfrastructurePage() {
  const { isDark } = useTheme();
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedServer, setSelectedServer] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [serverHistory, setServerHistory] = useState([]);

  const fetchServers = async () => {
    try {
      setLoading(true);
      const res = await api.getInfrastructure(statusFilter, searchQuery);
      setServers(res);
    } catch (err) {
      console.error('Failed to fetch infrastructure list', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, [statusFilter, searchQuery]);

  const handleOpenDetail = async (server) => {
    setSelectedServer(server);
    setDetailLoading(true);
    try {
      const res = await api.getServerDetail(server.id);
      setSelectedServer(res.server);
      setServerHistory(res.history);
    } catch (err) {
      console.error('Failed to load server details', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const healthyCount = servers.filter(s => s.status === 'healthy').length;
  const warningCount = servers.filter(s => s.status === 'warning').length;
  const criticalCount = servers.filter(s => s.status === 'critical').length;
  const offlineCount = servers.filter(s => s.status === 'offline').length;

  // Chart styles based on theme
  const gridStroke = isDark ? '#1e293b' : '#f1f5f9';
  const axisStroke = isDark ? '#64748b' : '#94a3b8';
  const tooltipBg = isDark ? '#0b1120' : '#ffffff';
  const tooltipBorder = isDark ? '#334155' : '#e2e8f0';
  const tooltipColor = isDark ? '#f8fafc' : '#0f172a';

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 dark:border-white/5 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            Infrastructure Inventory & Node Metrics
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time physical and virtual node health, utilization metrics, and service status.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={fetchServers}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 transition shadow-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh Nodes
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard 
          title="Monitored Nodes"
          value={servers.length}
          subtitle="Host & virtual instances"
          icon={Server}
          color="cyan"
          badge="Inventory"
        />
        <StatCard 
          title="Healthy Systems"
          value={healthyCount}
          subtitle="Operating in nominal range"
          icon={CheckCircle2}
          color="emerald"
          badge="Nominal"
        />
        <StatCard 
          title="Warning Condition"
          value={warningCount}
          subtitle="Elevated compute/latency"
          icon={AlertTriangle}
          color="amber"
          badge="Attention"
        />
        <StatCard 
          title="Critical / Offline"
          value={criticalCount + offlineCount}
          subtitle={`${criticalCount} Critical • ${offlineCount} Offline`}
          icon={Cpu}
          color="rose"
          badge={criticalCount > 0 ? "Action Req" : "Zero"}
        />
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl glass-card">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text"
              placeholder="Search by server name, hostname, or IP..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 transition shadow-inner"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" />
            Status:
          </span>
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-900 p-1 rounded-xl border border-slate-200 dark:border-slate-800">
            {['', 'healthy', 'warning', 'critical', 'offline'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition ${
                  statusFilter === st 
                    ? 'bg-white dark:bg-cyan-950 text-cyan-700 dark:text-cyan-300 border border-slate-200 dark:border-cyan-500/30 shadow-xs' 
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                {st || 'All'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Servers Table */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 dark:bg-slate-900/80 text-slate-500 dark:text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-200/80 dark:border-white/5">
              <tr>
                <th className="py-3.5 px-4 font-bold">Server Node</th>
                <th className="py-3.5 px-4 font-bold">Health Status</th>
                <th className="py-3.5 px-4 font-bold">Service</th>
                <th className="py-3.5 px-4 font-bold">CPU Usage</th>
                <th className="py-3.5 px-4 font-bold">Memory</th>
                <th className="py-3.5 px-4 font-bold">Storage</th>
                <th className="py-3.5 px-4 font-bold">Latency</th>
                <th className="py-3.5 px-4 font-bold">Last Telemetry</th>
                <th className="py-3.5 px-4 font-bold text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan="9" className="py-12 text-center text-slate-500 dark:text-slate-400">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                      Loading servers...
                    </div>
                  </td>
                </tr>
              ) : servers.length === 0 ? (
                <tr>
                  <td colSpan="9" className="py-12 text-center text-slate-500 dark:text-slate-400 font-medium">
                    No monitored servers match your filter.
                  </td>
                </tr>
              ) : (
                servers.map((s) => (
                  <tr 
                    key={s.id} 
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition group cursor-pointer"
                    onClick={() => handleOpenDetail(s)}
                  >
                    <td className="py-3.5 px-4">
                      <div>
                        <div className="font-bold text-slate-900 dark:text-white group-hover:text-cyan-600 dark:group-hover:text-cyan-300 transition flex items-center gap-2">
                          <Server className="w-3.5 h-3.5 text-slate-400" />
                          <span>{s.display_name}</span>
                          {s.is_simulated && (
                            <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20">
                              SIM
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-0.5">{s.hostname} • {s.ip_address}</p>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold capitalize ${
                        s.service_status === 'up' 
                          ? 'text-emerald-800 bg-emerald-100/80 dark:text-emerald-300 dark:bg-emerald-950/60' 
                          : 'text-rose-800 bg-rose-100/80 dark:text-rose-300 dark:bg-rose-950/60'
                      }`}>
                        {s.service_status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="space-y-1 w-24">
                        <div className="flex justify-between text-[11px] font-mono">
                          <span className={s.last_cpu > 90 ? 'text-rose-600 dark:text-rose-400 font-bold' : 'text-slate-700 dark:text-slate-200 font-medium'}>
                            {s.last_cpu?.toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${s.last_cpu > 90 ? 'bg-rose-500' : 'bg-cyan-500'}`} 
                            style={{ width: `${Math.min(100, s.last_cpu || 0)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="space-y-1 w-24">
                        <div className="flex justify-between text-[11px] font-mono">
                          <span className={s.last_memory > 90 ? 'text-rose-600 dark:text-rose-400 font-bold' : 'text-slate-700 dark:text-slate-200 font-medium'}>
                            {s.last_memory?.toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${s.last_memory > 90 ? 'bg-rose-500' : 'bg-indigo-500'}`} 
                            style={{ width: `${Math.min(100, s.last_memory || 0)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-700 dark:text-slate-300">
                      {s.last_disk?.toFixed(1)}%
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-700 dark:text-slate-300">
                      {s.last_latency?.toFixed(1)} ms
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 dark:text-slate-400 text-[11px] font-mono">
                      {s.last_seen ? new Date(s.last_seen).toLocaleTimeString() : 'N/A'}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition shadow-2xs">
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detailed Server Modal */}
      {selectedServer && createPortal(
        <div 
          onClick={(e) => { if (e.target === e.currentTarget) setSelectedServer(null); }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fadeIn"
        >
          <div className="bg-white dark:bg-slate-900 w-full max-w-4xl rounded-2xl p-6 border border-slate-200 dark:border-white/10 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between border-b border-slate-100 dark:border-white/5 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-cyan-100 text-cyan-800 dark:bg-slate-800 dark:text-cyan-400 border border-cyan-200 dark:border-slate-700 shadow-sm">
                  <Server className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white">{selectedServer.display_name}</h2>
                    <StatusBadge status={selectedServer.status} />
                    {selectedServer.is_simulated && (
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30">
                        SIMULATED TELEMETRY
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                    {selectedServer.hostname} • {selectedServer.ip_address} • {selectedServer.os_info}
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedServer(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-white/5 shadow-2xs">
                <p className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Current CPU</p>
                <p className="text-xl font-bold font-mono text-cyan-600 dark:text-cyan-400">{selectedServer.last_cpu?.toFixed(1)}%</p>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-white/5 shadow-2xs">
                <p className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Current Memory</p>
                <p className="text-xl font-bold font-mono text-indigo-600 dark:text-indigo-400">{selectedServer.last_memory?.toFixed(1)}%</p>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-white/5 shadow-2xs">
                <p className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Disk Volume</p>
                <p className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">{selectedServer.last_disk?.toFixed(1)}%</p>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-white/5 shadow-2xs">
                <p className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Network Latency</p>
                <p className="text-xl font-bold font-mono text-amber-600 dark:text-amber-400">{selectedServer.last_latency?.toFixed(1)} ms</p>
              </div>
            </div>

            {/* Historical Telemetry Chart */}
            <ChartCard 
              title="Recent Node Performance Timeline" 
              subtitle="Last 30 approved telemetry intervals received from edge collector"
              badge="Allow-List Verified"
            >
              <div className="h-64 w-full">
                {detailLoading ? (
                  <div className="h-full flex items-center justify-center text-xs text-slate-500 dark:text-slate-400">
                    Loading historical telemetry...
                  </div>
                ) : serverHistory.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-xs text-slate-500 dark:text-slate-400">
                    No historical telemetry captured yet for this host.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={serverHistory}>
                      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                      <XAxis dataKey="timestamp" stroke={axisStroke} tick={{ fontSize: 10 }} />
                      <YAxis stroke={axisStroke} domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" />
                      <Tooltip contentStyle={{ 
                        backgroundColor: tooltipBg, 
                        borderColor: tooltipBorder, 
                        color: tooltipColor,
                        borderRadius: '0.75rem', 
                        fontSize: '11px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                      }} />
                      <Line type="monotone" dataKey="cpu" name="CPU (%)" stroke="#0ea5e9" strokeWidth={2.5} dot={false} />
                      <Line type="monotone" dataKey="memory" name="Memory (%)" stroke="#6366f1" strokeWidth={2.5} dot={false} />
                      <Line type="monotone" dataKey="disk" name="Disk (%)" stroke="#10b981" strokeWidth={2.5} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </ChartCard>

            <div className="flex justify-end pt-3 border-t border-slate-100 dark:border-white/5">
              <button 
                onClick={() => setSelectedServer(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-xs font-bold text-slate-700 dark:text-slate-200 transition"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
