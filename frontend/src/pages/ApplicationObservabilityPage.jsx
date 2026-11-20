// frontend/src/pages/ApplicationObservabilityPage.jsx
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import StatCard from '../components/StatCard';
import { 
  GitCommit, 
  Layers, 
  Network, 
  Activity, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw, 
  Search, 
  Filter, 
  Database, 
  Cpu, 
  ArrowRight, 
  ShieldCheck, 
  FileCode,
  Share2,
  ChevronRight,
  Server,
  Zap
} from 'lucide-react';

export default function ApplicationObservabilityPage() {
  const [services, setServices] = useState([]);
  const [dependencyGraph, setDependencyGraph] = useState(null);
  const [traces, setTraces] = useState([]);
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('traces'); // 'traces' | 'dependencies' | 'services'
  const [serviceFilter, setServiceFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [svcData, depData, trcData] = await Promise.all([
        api.getServices(),
        api.getServiceDependencies(),
        api.getTraces(serviceFilter, statusFilter)
      ]);
      setServices(svcData || []);
      setDependencyGraph(depData || null);
      setTraces(trcData || []);
      if (trcData && trcData.length > 0 && !selectedTrace) {
        // Automatically fetch details for the first trace
        const firstDetail = await api.getTraceDetail(trcData[0].trace_id);
        setSelectedTrace(firstDetail);
      }
    } catch (err) {
      console.error('Failed to load application observability data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [serviceFilter, statusFilter]);

  const handleSelectTrace = async (traceId) => {
    try {
      const detail = await api.getTraceDetail(traceId);
      setSelectedTrace(detail);
    } catch (err) {
      console.error('Failed to load trace detail', err);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-cyan-50 dark:bg-cyan-950/60 text-cyan-600 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-800/40">
              <GitCommit className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Application Observability & OpenTelemetry
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Distributed multi-hop transaction tracing, microservice topology mapping, and privacy-sanitized span attributes.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Tab Switcher */}
          <div className="flex items-center p-1 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <button
              onClick={() => setActiveTab('traces')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === 'traces'
                  ? 'bg-white dark:bg-slate-800 text-cyan-700 dark:text-cyan-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <GitCommit className="w-3.5 h-3.5" />
              <span>Distributed Traces</span>
            </button>
            <button
              onClick={() => setActiveTab('dependencies')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === 'dependencies'
                  ? 'bg-white dark:bg-slate-800 text-cyan-700 dark:text-cyan-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Share2 className="w-3.5 h-3.5" />
              <span>Service Map</span>
            </button>
            <button
              onClick={() => setActiveTab('services')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === 'services'
                  ? 'bg-white dark:bg-slate-800 text-cyan-700 dark:text-cyan-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Server className="w-3.5 h-3.5" />
              <span>Services ({services.length})</span>
            </button>
          </div>
          <button 
            onClick={fetchData}
            disabled={loading}
            className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition shadow-xs"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* Zero-Leak Trace Guarantee Banner */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-50 via-teal-50/50 to-blue-50 dark:from-emerald-950/40 dark:via-teal-950/20 dark:to-slate-950/50 border border-emerald-200/80 dark:border-emerald-500/30 flex items-start gap-3.5 shadow-soft">
        <div className="p-2 rounded-xl bg-emerald-600 text-white shadow-md shadow-emerald-600/20 shrink-0">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div className="space-y-0.5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-300">
            OpenTelemetry Trace Privacy Sanitization Active
          </h3>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            All traces pass through the on-premises <strong className="font-semibold text-slate-800 dark:text-white">TracePrivacySanitiser</strong> before transmission. Database SQL literals are parameterized to <code className="font-mono text-emerald-700 dark:text-emerald-400">?</code>, bearer tokens and cookies are purged, and unapproved span attributes are dropped at the edge.
          </p>
        </div>
      </div>

      {/* TAB 1: DISTRIBUTED TRACES & WATERFALL INSPECTOR */}
      {activeTab === 'traces' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Traces List */}
          <div className="lg:col-span-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300 px-1">
              <span>Traces ({traces.length})</span>
              <div className="flex items-center gap-1.5 text-[11px] font-normal">
                <button
                  onClick={() => setStatusFilter('')}
                  className={`px-2 py-0.5 rounded ${!statusFilter ? 'bg-cyan-500 text-white font-semibold' : 'text-slate-500'}`}
                >
                  All
                </button>
                <button
                  onClick={() => setStatusFilter('OK')}
                  className={`px-2 py-0.5 rounded ${statusFilter === 'OK' ? 'bg-emerald-600 text-white font-semibold' : 'text-slate-500'}`}
                >
                  OK
                </button>
                <button
                  onClick={() => setStatusFilter('ERROR')}
                  className={`px-2 py-0.5 rounded ${statusFilter === 'ERROR' ? 'bg-rose-600 text-white font-semibold' : 'text-slate-500'}`}
                >
                  Errors
                </button>
              </div>
            </div>

            <div className="space-y-2 max-h-[650px] overflow-y-auto pr-1">
              {traces.length === 0 ? (
                <div className="glass-card rounded-2xl p-8 text-center text-slate-400 text-xs">
                  No traces found matching filter.
                </div>
              ) : (
                traces.map((t) => (
                  <div
                    key={t.trace_id}
                    onClick={() => handleSelectTrace(t.trace_id)}
                    className={`p-3.5 rounded-2xl glass-card cursor-pointer border transition-all ${
                      selectedTrace?.trace_id === t.trace_id
                        ? 'border-cyan-500 ring-2 ring-cyan-500/20 bg-cyan-50/20 dark:bg-slate-900/90 shadow-md'
                        : 'border-slate-200/80 dark:border-slate-800/80 hover:border-cyan-400/50 shadow-soft'
                    } space-y-2`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono font-bold text-cyan-600 dark:text-cyan-400 truncate max-w-[200px]">
                        {t.trace_id}
                      </span>
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                        t.has_error
                          ? 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-300 dark:border-rose-500/40'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-500/40'
                      }`}>
                        {t.has_error ? 'ERROR' : 'OK'}
                      </span>
                    </div>

                    <div className="space-y-0.5">
                      <div className="text-xs font-bold text-slate-900 dark:text-white truncate">
                        {t.root_operation}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between">
                        <span>Root: <strong className="text-slate-700 dark:text-slate-300 font-medium">{t.root_service}</strong></span>
                        <span className="font-mono text-cyan-600 dark:text-cyan-400 font-bold">{t.duration_ms.toFixed(1)}ms</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 pt-1 border-t border-slate-100 dark:border-slate-800/60 text-[10px] text-slate-400 font-mono">
                      <span>{t.span_count} spans</span>
                      <span>•</span>
                      <span>{t.services.join(' → ')}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Trace Waterfall & Span Inspector Drawer */}
          <div className="lg:col-span-7 glass-card rounded-2xl p-6 shadow-soft space-y-5">
            {selectedTrace ? (
              <>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800/80 pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400">
                        {selectedTrace.trace_id}
                      </span>
                      <span className={`text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border ${
                        selectedTrace.has_error
                          ? 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-300'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300'
                      }`}>
                        {selectedTrace.has_error ? 'ERROR' : 'OK'}
                      </span>
                    </div>
                    <h3 className="text-base font-extrabold text-slate-900 dark:text-white mt-1">
                      Transaction Waterfall Execution
                    </h3>
                  </div>

                  <div className="flex items-center gap-3 text-xs font-mono bg-slate-50 dark:bg-slate-950/60 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800">
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 block font-bold">Total Duration</span>
                      <span className="font-bold text-slate-800 dark:text-slate-200">{selectedTrace.total_duration_ms}ms</span>
                    </div>
                    <div className="h-6 w-px bg-slate-200 dark:bg-slate-800" />
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 block font-bold">Spans</span>
                      <span className="font-bold text-cyan-600 dark:text-cyan-400">{selectedTrace.total_spans}</span>
                    </div>
                  </div>
                </div>

                {/* Waterfall Visualizer */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    Span Hierarchy & Latency Timeline
                  </h4>

                  <div className="space-y-2.5">
                    {selectedTrace.spans.map((span) => {
                      const totalDur = selectedTrace.total_duration_ms || 1;
                      const leftPercent = Math.min(95, (span.offset_ms / totalDur) * 100);
                      const widthPercent = Math.max(5, Math.min(100 - leftPercent, (span.duration_ms / totalDur) * 100));

                      return (
                        <div key={span.span_id} className="p-3 rounded-xl bg-slate-50/70 dark:bg-slate-900/60 border border-slate-200/70 dark:border-slate-800/60 space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-900 dark:text-white">{span.service_name}</span>
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                                {span.span_kind}
                              </span>
                              <span className="text-xs text-slate-600 dark:text-slate-400 font-medium truncate max-w-[220px]">
                                {span.operation_name}
                              </span>
                            </div>
                            <span className="font-mono text-xs font-bold text-cyan-600 dark:text-cyan-400">
                              {span.duration_ms.toFixed(1)}ms
                            </span>
                          </div>

                          {/* Relative Timeline Bar */}
                          <div className="relative w-full h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div
                              style={{ left: `${leftPercent}%`, width: `${widthPercent}%` }}
                              className={`absolute top-0 bottom-0 rounded-full ${
                                span.status_code === 'ERROR'
                                  ? 'bg-rose-500'
                                  : 'bg-gradient-to-r from-cyan-500 to-blue-500'
                              }`}
                            />
                          </div>

                          {/* Sanitized Attributes Inspector */}
                          {Object.keys(span.attributes).length > 0 && (
                            <div className="pt-1.5 border-t border-slate-200/50 dark:border-slate-800/40">
                              <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono">
                                {Object.entries(span.attributes).map(([k, v]) => (
                                  <span key={k} className="p-1 rounded bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300">
                                    <strong className="text-cyan-700 dark:text-cyan-400 font-medium">{k}</strong>: {String(v)}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <div className="py-20 text-center text-slate-400 text-xs">
                Select a trace from the left panel to inspect its waterfall hierarchy.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: SERVICE DEPENDENCY GRAPH & BLAST RADIUS */}
      {activeTab === 'dependencies' && dependencyGraph && (
        <div className="space-y-6">
          {/* Blast Radius Warning Banner if any node is degraded */}
          {Object.keys(dependencyGraph.blast_radius_analysis || {}).length > 0 && (
            <div className="p-4 rounded-2xl bg-amber-50 dark:bg-amber-950/50 border border-amber-300 dark:border-amber-500/40 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-900 dark:text-amber-300">
                <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <span>Blast Radius Alert: Degradation Cascading to Upstream Consumers</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-slate-700 dark:text-slate-300">
                {Object.values(dependencyGraph.blast_radius_analysis).map((item, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-amber-200 dark:border-amber-800/40">
                    <span className="font-bold text-rose-600 dark:text-rose-400">{item.source_service}</span> ({item.current_status})
                    <p className="text-[11px] text-slate-500 mt-1">
                      Impacting upstream: <strong className="text-slate-700 dark:text-slate-200">{item.affected_upstream_callers.join(', ') || 'Direct Ingress'}</strong>
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Service Dependency Topology Cards */}
          <div className="glass-card rounded-2xl p-6 shadow-soft space-y-5">
            <div className="border-b border-slate-100 dark:border-slate-800/80 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Share2 className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                  Discovered Microservice Dependency Topology
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Dynamic caller-to-callee request flows discovered automatically via OpenTelemetry context propagation.
                </p>
              </div>
              <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                {dependencyGraph.total_dependencies} Active Links
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {dependencyGraph.edges.map((edge, idx) => (
                <div key={idx} className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 shadow-soft space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-900 dark:text-white">{edge.source}</span>
                    <ArrowRight className="w-4 h-4 text-cyan-500 shrink-0" />
                    <span className="font-bold text-slate-900 dark:text-white">{edge.target}</span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200/50 dark:border-slate-800/40 text-center font-mono text-xs">
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 block">Calls</span>
                      <strong className="text-slate-800 dark:text-slate-200">{edge.call_count}</strong>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 block">Avg RTT</span>
                      <strong className="text-cyan-600 dark:text-cyan-400">{edge.avg_latency_ms}ms</strong>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 block">Errors</span>
                      <strong className={edge.error_count > 0 ? 'text-rose-500' : 'text-emerald-500'}>
                        {edge.error_count}
                      </strong>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: SERVICES DIRECTORY & GOLDEN SIGNALS */}
      {activeTab === 'services' && (
        <div className="glass-card rounded-2xl overflow-hidden shadow-soft">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 dark:bg-slate-900/80 text-slate-600 dark:text-slate-400 font-mono text-[10px] uppercase border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4 font-semibold">Service Name</th>
                  <th className="py-3 px-4 font-semibold">Type</th>
                  <th className="py-3 px-4 font-semibold">Health Status</th>
                  <th className="py-3 px-4 font-semibold">Throughput (RPM)</th>
                  <th className="py-3 px-4 font-semibold">Avg Latency</th>
                  <th className="py-3 px-4 font-semibold">P95 Latency</th>
                  <th className="py-3 px-4 font-semibold">Error Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
                {services.map((svc) => (
                  <tr key={svc.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-sans font-bold text-slate-900 dark:text-white">
                      {svc.name}
                    </td>
                    <td className="py-3 px-4 text-slate-500 dark:text-slate-400 uppercase text-[10px]">
                      {svc.service_type}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={svc.health_status} size="xs" />
                    </td>
                    <td className="py-3 px-4 text-slate-800 dark:text-slate-200">
                      {svc.throughput_rpm.toFixed(0)} rpm
                    </td>
                    <td className="py-3 px-4 text-cyan-600 dark:text-cyan-400 font-bold">
                      {svc.avg_latency_ms.toFixed(1)}ms
                    </td>
                    <td className="py-3 px-4 text-slate-700 dark:text-slate-300">
                      {svc.p95_latency_ms.toFixed(1)}ms
                    </td>
                    <td className="py-3 px-4">
                      <span className={svc.error_rate > 0.05 ? 'text-rose-500 font-bold' : 'text-emerald-500'}>
                        {(svc.error_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
