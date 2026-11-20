// frontend/src/pages/IntegrationsPage.jsx
import React, { useState, useEffect } from 'react';
import { 
  Blocks, 
  Cpu, 
  HardDrive, 
  Layers, 
  Activity, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  RefreshCw, 
  Server, 
  Database, 
  Terminal, 
  ExternalLink, 
  ShieldCheck, 
  Flame, 
  Boxes,
  Zap,
  Radio
} from 'lucide-react';
import { api } from '../services/api';

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState([]);
  const [realHostData, setRealHostData] = useState(null);
  const [dockerData, setDockerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [samplingHost, setSamplingHost] = useState(false);
  const [probingDocker, setProbingDocker] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [intList, hostRes, docRes] = await Promise.all([
        api.getIntegrations(),
        api.getRealHostTelemetry(),
        api.getDockerStatus(),
      ]);
      setIntegrations(intList || []);
      setRealHostData(hostRes);
      setDockerData(docRes);
    } catch (err) {
      console.error('Failed to load integrations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const sampleHostNow = async () => {
    setSamplingHost(true);
    try {
      const res = await api.getRealHostTelemetry();
      setRealHostData(res);
    } catch (e) {
      console.error(e);
    } finally {
      setSamplingHost(false);
    }
  };

  const probeDockerNow = async () => {
    setProbingDocker(true);
    try {
      const res = await api.getDockerStatus();
      setDockerData(res);
    } catch (e) {
      console.error(e);
    } finally {
      setProbingDocker(false);
    }
  };

  const testIntegration = async (type) => {
    try {
      const res = await api.testIntegration(type);
      setTestResult({ type, ...res });
      setTimeout(() => setTestResult(null), 5000);
    } catch (e) {
      alert(`Test failed for ${type}: ` + e.message);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-cyan-500 via-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <Blocks className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                Enterprise Infrastructure & Application Integrations
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Phase 2E: Authentic kernel telemetry, container runtime probes, and application instrumentation
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-slate-700/60 shadow-sm transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Integrations
          </button>
        </div>
      </div>

      {/* Telemetry Authenticity Callout */}
      <div className="p-4 rounded-3xl bg-gradient-to-r from-cyan-500/10 via-indigo-500/10 to-purple-500/10 border border-cyan-500/20 backdrop-blur-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-cyan-500/20 flex items-center justify-center text-cyan-500 shrink-0">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-900 dark:text-white">
                Dual Telemetry Pipeline Architecture
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-cyan-500 text-white uppercase">
                Real vs Simulated
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5">
              ObserVault strictly tags all ingest streams. Hardware kernel readings and live FastAPI traces are flagged <strong className="text-cyan-600 dark:text-cyan-400">REAL TELEMETRY</strong>. Demo stress generators are explicitly labeled <strong className="text-purple-600 dark:text-purple-400">SIMULATED</strong>.
            </p>
          </div>
        </div>
      </div>

      {/* Hero Live Hardware Probe Card */}
      <div className="p-6 rounded-3xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-2xl border border-slate-200 dark:border-white/10 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-500">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900 dark:text-white">
                  Local Operating System Kernel Probe (psutil)
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 uppercase">
                  Connected & Live
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-cyan-500 text-white uppercase">
                  Real Telemetry
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Host: <span className="font-mono text-slate-700 dark:text-slate-200">{realHostData?.hostname || 'Local Machine'}</span> • {realHostData?.os_info}
              </p>
            </div>
          </div>

          <button
            onClick={sampleHostNow}
            disabled={samplingHost}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-md shadow-cyan-500/20 transition-all self-start sm:self-auto"
          >
            <Zap className={`w-3.5 h-3.5 ${samplingHost ? 'animate-spin' : ''}`} />
            Sample Real Hardware Now
          </button>
        </div>

        {/* 5 Real Hardware Metric Tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-white/5">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider">CPU Usage</span>
              <Cpu className="w-3.5 h-3.5 text-cyan-500" />
            </div>
            <p className="text-xl font-extrabold text-slate-900 dark:text-white">
              {realHostData?.cpu_percent !== undefined ? realHostData.cpu_percent : '--'}%
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Real Kernel Sample</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-white/5">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider">RAM Memory</span>
              <Layers className="w-3.5 h-3.5 text-indigo-500" />
            </div>
            <p className="text-xl font-extrabold text-slate-900 dark:text-white">
              {realHostData?.memory_percent !== undefined ? realHostData.memory_percent : '--'}%
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Virtual Memory</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-white/5">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider">Storage (Root)</span>
              <HardDrive className="w-3.5 h-3.5 text-purple-500" />
            </div>
            <p className="text-xl font-extrabold text-slate-900 dark:text-white">
              {realHostData?.disk_percent !== undefined ? realHostData.disk_percent : '--'}%
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Root Partition</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-white/5">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider">Network I/O</span>
              <Activity className="w-3.5 h-3.5 text-emerald-500" />
            </div>
            <p className="text-base font-extrabold text-slate-900 dark:text-white mt-1 truncate">
              {realHostData?.network_sent_mb || 0}M / {realHostData?.network_recv_mb || 0}M
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Sent / Received</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-white/5">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider">Active PIDs</span>
              <Activity className="w-3.5 h-3.5 text-amber-500" />
            </div>
            <p className="text-xl font-extrabold text-slate-900 dark:text-white">
              {realHostData?.process_count || '--'}
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">OS Task Processes</p>
          </div>
        </div>
      </div>

      {/* Integration Connectors Grid */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">
          Configured Integrations & Runtime Connectors
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Docker Container Engine */}
          <div className="p-5 rounded-3xl bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 shadow-sm space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-500">
                  <Boxes className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">Docker Engine & Containers</h3>
                  <p className="text-xs text-slate-400 font-mono">unix:///var/run/docker.sock</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                  dockerData?.status === 'connected'
                    ? 'bg-emerald-500 text-white'
                    : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                }`}>
                  {dockerData?.status || 'Offline'}
                </span>
              </div>
            </div>

            <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/50 dark:border-white/5 text-xs space-y-2">
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                {dockerData?.setup_guide}
              </p>
              {dockerData?.error_detail && (
                <p className="text-[11px] font-mono text-amber-500">
                  Status Notice: {dockerData.error_detail}
                </p>
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-white/5">
              <span className="text-[11px] text-slate-400">
                Containers: {dockerData?.container_count || 0} active
              </span>
              <button
                onClick={probeDockerNow}
                disabled={probingDocker}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-500 transition-all flex items-center gap-1.5"
              >
                <RefreshCw className={`w-3 h-3 ${probingDocker ? 'animate-spin' : ''}`} />
                Probe Socket
              </button>
            </div>
          </div>

          {/* FastAPI Application Instrumentation */}
          <div className="p-5 rounded-3xl bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 shadow-sm space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">FastAPI Internal Telemetry</h3>
                  <p className="text-xs text-slate-400 font-mono">http://127.0.0.1:8000</p>
                </div>
              </div>

              <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-emerald-500 text-white">
                Active & Traced
              </span>
            </div>

            <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/50 dark:border-white/5 text-xs space-y-2">
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                FastAPI auto-instrumentation middleware is embedded directly into the central server. Every incoming API call produces a correlated OpenTelemetry span.
              </p>
              <div className="flex items-center gap-4 text-[11px] text-slate-500 font-mono">
                <span>Active Endpoints: 48</span>
                <span>•</span>
                <span>Trace Middleware: In-Memory</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-white/5">
              <span className="text-[11px] text-slate-400">Stream: Real Telemetry</span>
              <button
                onClick={() => testIntegration('fastapi_app')}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500 transition-all"
              >
                Test Middleware
              </button>
            </div>
          </div>

          {/* PostgreSQL Database Integration */}
          <div className="p-5 rounded-3xl bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 shadow-sm space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-500">
                  <Database className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">PostgreSQL Exporter</h3>
                  <p className="text-xs text-slate-400 font-mono">localhost:5432</p>
                </div>
              </div>

              <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                Port Probe Ready
              </span>
            </div>

            <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/50 dark:border-white/5 text-xs space-y-2">
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                Connects to <code className="font-mono bg-slate-200 dark:bg-slate-800 px-1 py-0.5 rounded">pg_stat_activity</code> and <code className="font-mono bg-slate-200 dark:bg-slate-800 px-1 py-0.5 rounded">pg_stat_statements</code>. In accordance with ObserVault privacy rules, all SQL query text is omitted or parameter-stripped.
              </p>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-white/5">
              <span className="text-[11px] text-slate-400">Target: Port 5432</span>
              <button
                onClick={() => testIntegration('postgres_db')}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-500 transition-all"
              >
                Probe Port 5432
              </button>
            </div>
          </div>

          {/* Nginx Ingress Reverse Proxy */}
          <div className="p-5 rounded-3xl bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 shadow-sm space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">Nginx Web Server / Proxy</h3>
                  <p className="text-xs text-slate-400 font-mono">http://localhost:80/stub_status</p>
                </div>
              </div>

              <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                Configurable
              </span>
            </div>

            <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/50 dark:border-white/5 text-xs space-y-2">
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                Monitors active connections, accepted requests, and HTTP 5xx rate ratios. URL query parameters are stripped before metric aggregation.
              </p>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-white/5">
              <span className="text-[11px] text-slate-400">Ingress Gateway</span>
              <span className="text-[11px] font-medium text-slate-500">Log Exporter Configured</span>
            </div>
          </div>
        </div>

        {/* Temporary Test Result Banner */}
        {testResult && (
          <div className="p-4 rounded-2xl bg-slate-900 text-white border border-slate-700 animate-fadeIn text-xs flex items-center justify-between">
            <div>
              <span className="font-bold text-cyan-400 uppercase tracking-wider">Test Probe Response:</span>{' '}
              <span>{testResult.message} (Connected: {testResult.connected ? 'YES' : 'NO'})</span>
            </div>
            <button onClick={() => setTestResult(null)} className="text-slate-400 hover:text-white">✕</button>
          </div>
        )}
      </div>
    </div>
  );
}
