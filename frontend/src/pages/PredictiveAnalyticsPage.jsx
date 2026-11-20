// frontend/src/pages/PredictiveAnalyticsPage.jsx
import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { 
  TrendingUp, 
  AlertTriangle, 
  Clock, 
  ShieldCheck, 
  Server, 
  Cpu, 
  HardDrive, 
  Layers, 
  Activity, 
  RefreshCw, 
  ChevronRight, 
  Info, 
  CheckCircle2, 
  XCircle, 
  ArrowUpRight, 
  Plus, 
  Copy, 
  Check, 
  Flame, 
  Calendar,
  Sparkles,
  Brain
} from 'lucide-react';
import { api } from '../services/api';
import AIExplanationCard from '../components/ai/AIExplanationCard';

export default function PredictiveAnalyticsPage() {
  const [servers, setServers] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [selectedMetric, setSelectedMetric] = useState('disk_percent');
  const [horizon, setHorizon] = useState('7d');
  
  const [forecastData, setForecastData] = useState(null);
  const [capacityWarnings, setCapacityWarnings] = useState([]);
  const [sloMetrics, setSloMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState(null);

  // AI Predictive Insight State (Phase 3)
  const [aiPredictiveData, setAiPredictiveData] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);

  const handleRunAIPredictive = async () => {
    if (!selectedServer) return;
    setAiLoading(true);
    setAiError(null);
    try {
      const res = await api.getPredictiveAIAnalysis(selectedServer.id, selectedMetric, horizon);
      setAiPredictiveData(res);
    } catch (err) {
      console.error('Failed to run AI Predictive Analysis:', err);
      setAiError(err.message || 'Failed to generate AI predictive explanation.');
    } finally {
      setAiLoading(false);
    }
  };

  // New SLO Modal State
  const [showSloModal, setShowSloModal] = useState(false);
  const [newSloName, setNewSloName] = useState('');
  const [newSloService, setNewSloService] = useState('api-gateway');
  const [newSloType, setNewSloType] = useState('availability');
  const [newSloTarget, setNewSloTarget] = useState('99.9');

  const metricOptions = [
    { id: 'disk_percent', label: 'Disk Storage (%)', icon: HardDrive, unit: '%' },
    { id: 'memory_percent', label: 'RAM Memory (%)', icon: Layers, unit: '%' },
    { id: 'cpu_percent', label: 'CPU Usage (%)', icon: Cpu, unit: '%' },
    { id: 'network_latency_ms', label: 'Network Latency (ms)', icon: Activity, unit: 'ms' },
    { id: 'packet_loss_percent', label: 'Packet Loss (%)', icon: Activity, unit: '%' },
  ];

  const horizonOptions = [
    { value: '15m', label: '15 Mins' },
    { value: '1h', label: '1 Hour' },
    { value: '24h', label: '24 Hours' },
    { value: '7d', label: '7 Days' },
    { value: '14d', label: '14 Days' },
    { value: '30d', label: '30 Days' },
  ];

  const loadData = async () => {
    setLoading(true);
    try {
      // 1. Fetch servers
      const infraRes = await api.getInfrastructure();
      const srvList = infraRes.servers || [];
      setServers(srvList);

      const activeServer = selectedServer || srvList[0];
      if (activeServer) {
        setSelectedServer(activeServer);
        // 2. Fetch Forecast
        const fc = await api.getForecast(activeServer.id, selectedMetric, horizon);
        setForecastData(fc);
      }

      // 3. Fetch Capacity Warnings
      const warnings = await api.getCapacityWarnings();
      setCapacityWarnings(warnings);

      // 4. Fetch SLO Metrics
      const slos = await api.getSLOMetrics();
      setSloMetrics(slos);
    } catch (err) {
      console.error('Failed to load predictive analytics data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleServerChange = async (srv) => {
    setSelectedServer(srv);
    setLoading(true);
    try {
      const fc = await api.getForecast(srv.id, selectedMetric, horizonDays);
      setForecastData(fc);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleMetricChange = async (metricId) => {
    setSelectedMetric(metricId);
    if (!selectedServer) return;
    setLoading(true);
    try {
      const fc = await api.getForecast(selectedServer.id, metricId, horizon);
      setForecastData(fc);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleHorizonChange = async (hVal) => {
    setHorizon(hVal);
    if (!selectedServer) return;
    setLoading(true);
    try {
      const fc = await api.getForecast(selectedServer.id, selectedMetric, hVal);
      setForecastData(fc);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSlo = async (e) => {
    e.preventDefault();
    try {
      await api.createSLO({
        name: newSloName,
        service_name: newSloService,
        sli_type: newSloType,
        target_percentage: parseFloat(newSloTarget),
        warning_threshold: Math.max(90.0, parseFloat(newSloTarget) - 0.5),
        rolling_window_days: 30
      });
      setShowSloModal(false);
      setNewSloName('');
      const slos = await api.getSLOMetrics();
      setSloMetrics(slos);
    } catch (err) {
      alert('Failed to create SLO: ' + err.message);
    }
  };

  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Render SVG Prediction Chart
  const renderForecastChart = () => {
    if (!forecastData || !forecastData.historical_points) return null;

    const hist = forecastData.historical_points;
    const fc = forecastData.forecast_points;
    const allPoints = [...hist, ...fc];
    if (allPoints.length === 0) return null;

    const width = 800;
    const height = 260;
    const padX = 50;
    const padY = 30;

    const maxVal = 100.0;
    const minVal = 0.0;
    const threshold = forecastData.threshold_value || 90.0;

    const scaleX = (index) => padX + (index / (allPoints.length - 1)) * (width - 2 * padX);
    const scaleY = (val) => height - padY - ((val - minVal) / (maxVal - minVal)) * (height - 2 * padY);

    // Build historical path
    const histPath = hist.map((p, idx) => {
      const x = scaleX(idx);
      const y = scaleY(p.observed_value !== null ? p.observed_value : p.forecasted_value);
      return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(' ');

    // Build forecast dashed path
    const histLen = hist.length;
    const fcPath = fc.map((p, idx) => {
      const overallIdx = histLen - 1 + idx;
      const x = scaleX(overallIdx);
      const y = scaleY(p.forecasted_value);
      return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(' ');

    // Connect last historical point to first forecast point
    const lastHistX = scaleX(histLen - 1);
    const lastHistY = scaleY(hist[histLen - 1].observed_value || hist[histLen - 1].forecasted_value);
    const connectorPath = `M ${lastHistX.toFixed(1)} ${lastHistY.toFixed(1)} L ${scaleX(histLen).toFixed(1)} ${scaleY(fc[0]?.forecasted_value || 0).toFixed(1)}`;

    // Build shaded 95% Confidence Interval polygon for forecast
    let upperPolygon = [];
    let lowerPolygon = [];
    fc.forEach((p, idx) => {
      const overallIdx = histLen - 1 + idx;
      const x = scaleX(overallIdx);
      const yUpper = scaleY(p.upper_bound !== null ? p.upper_bound : p.forecasted_value);
      const yLower = scaleY(p.lower_bound !== null ? p.lower_bound : p.forecasted_value);
      upperPolygon.push(`${x.toFixed(1)},${yUpper.toFixed(1)}`);
      lowerPolygon.unshift(`${x.toFixed(1)},${yLower.toFixed(1)}`);
    });
    const confidenceConePath = upperPolygon.length > 0 ? `M ${upperPolygon.join(' L ')} L ${lowerPolygon.join(' L ')} Z` : '';

    const threshY = scaleY(threshold);

    return (
      <div className="relative w-full overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-64 select-none">
          {/* Background Grid */}
          {[0, 25, 50, 75, 100].map((v) => {
            const y = scaleY(v);
            return (
              <g key={v}>
                <line x1={padX} y1={y} x2={width - padX} y2={y} stroke="currentColor" className="text-slate-200 dark:text-slate-800" strokeDasharray="3 3" />
                <text x={padX - 8} y={y + 4} textAnchor="end" className="text-[10px] font-mono fill-slate-400 dark:fill-slate-500">{v}%</text>
              </g>
            );
          })}

          {/* 90% Threshold Warning Line */}
          <line x1={padX} y1={threshY} x2={width - padX} y2={threshY} stroke="#ef4444" strokeWidth="1.5" strokeDasharray="5 4" />
          <text x={width - padX} y={threshY - 6} textAnchor="end" className="text-[10px] font-bold fill-red-500">Threshold ({threshold}%)</text>

          {/* Forecast Horizon Boundary Divider */}
          <line x1={lastHistX} y1={padY} x2={lastHistX} y2={height - padY} stroke="#8b5cf6" strokeWidth="1.5" strokeDasharray="2 2" />
          <text x={lastHistX + 6} y={padY + 12} className="text-[10px] font-bold fill-purple-500">Forecast Horizon ➔</text>

          {/* Shaded 95% Confidence Interval Cone */}
          {confidenceConePath && (
            <path d={confidenceConePath} fill="url(#confidenceGradient)" opacity="0.4" />
          )}

          {/* Historical Baseline Line (Solid Cyan) */}
          <path d={histPath} fill="none" stroke="#06b6d4" strokeWidth="3" strokeLinecap="round" />

          {/* Historical Data Dots */}
          {hist.map((p, idx) => (
            <circle 
              key={`h-${idx}`} 
              cx={scaleX(idx)} 
              cy={scaleY(p.observed_value !== null ? p.observed_value : p.forecasted_value)} 
              r="3.5" 
              className="fill-cyan-500 stroke-white dark:stroke-slate-900 stroke-2" 
            />
          ))}

          {/* Connector */}
          <path d={connectorPath} fill="none" stroke="#8b5cf6" strokeWidth="2.5" strokeDasharray="4 3" />

          {/* Forecast Projected Trend Line (Dashed Purple) */}
          <path d={fcPath} fill="none" stroke="#8b5cf6" strokeWidth="3" strokeDasharray="5 4" strokeLinecap="round" />

          {/* Forecast Data Dots */}
          {fc.map((p, idx) => (
            <circle 
              key={`f-${idx}`} 
              cx={scaleX(histLen - 1 + idx)} 
              cy={scaleY(p.forecasted_value)} 
              r="3.5" 
              className="fill-purple-500 stroke-white dark:stroke-slate-900 stroke-2" 
            />
          ))}

          {/* Gradients */}
          <defs>
            <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.1" />
            </linearGradient>
          </defs>
        </svg>

        {/* Legend */}
        <div className="flex flex-wrap items-center justify-center gap-6 mt-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-1 bg-cyan-500 rounded-full" />
            <span className="text-slate-600 dark:text-slate-300 font-medium">Historical Baseline</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-1 border-b-2 border-dashed border-purple-500" />
            <span className="text-slate-600 dark:text-slate-300 font-medium">OLS Linear Projection</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-purple-500/20 border border-purple-500/40 rounded" />
            <span className="text-slate-600 dark:text-slate-300 font-medium">95% Prediction Interval</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-1 border-b-2 border-dashed border-red-500" />
            <span className="text-slate-600 dark:text-slate-300 font-medium">Exhaustion Threshold</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-purple-500/20">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                Predictive Analytics & Capacity Forecasting
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Phase 2E: Proactive capacity planning, empirical trend regression, and SLO error budget management
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunAIPredictive}
            disabled={aiLoading || !selectedServer}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-md shadow-indigo-500/20 transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
            title="Generate AI capacity forecast interpretation"
          >
            <Sparkles className={`w-3.5 h-3.5 ${aiLoading ? 'animate-spin' : ''}`} />
            <span>{aiLoading ? 'Interpreting...' : 'AI Forecast Insight'}</span>
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-slate-700/60 shadow-sm transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Forecast
          </button>
          <button
            onClick={() => setShowSloModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-500/20 hover:opacity-95 transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            Configure SLO
          </button>
        </div>
      </div>

      {/* Control Bar: Server, Metric, Horizon */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Server Select */}
        <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-800/70 backdrop-blur-xl border border-slate-200/80 dark:border-white/10 shadow-sm">
          <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-2">
            <Server className="w-3.5 h-3.5 text-indigo-500" />
            Target Server
          </label>
          <select
            value={selectedServer?.id || ''}
            onChange={(e) => {
              const srv = servers.find((s) => s.id === e.target.value);
              if (srv) handleServerChange(srv);
            }}
            className="w-full mt-1.5 px-3 py-2 text-xs font-medium rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {servers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.display_name} ({s.hostname})
              </option>
            ))}
          </select>
        </div>

        {/* Metric Select */}
        <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-800/70 backdrop-blur-xl border border-slate-200/80 dark:border-white/10 shadow-sm">
          <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-cyan-500" />
            Forecast Metric
          </label>
          <div className="grid grid-cols-2 gap-1.5 mt-1.5">
            {metricOptions.map((m) => {
              const Icon = m.icon;
              const isSelected = selectedMetric === m.id;
              return (
                <button
                  key={m.id}
                  onClick={() => handleMetricChange(m.id)}
                  className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    isSelected
                      ? 'bg-gradient-to-r from-cyan-600 to-indigo-600 text-white shadow-sm'
                      : 'bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  <Icon className="w-3 h-3" />
                  <span className="truncate">{m.label.split(' ')[0]}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Horizon Select */}
        <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-800/70 backdrop-blur-xl border border-slate-200/80 dark:border-white/10 shadow-sm">
          <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 text-purple-500" />
            Prediction Horizon
          </label>
          <div className="grid grid-cols-3 gap-1.5 mt-1.5">
            {horizonOptions.map((h) => {
              const isSelected = horizon === h.value;
              return (
                <button
                  key={h.value}
                  onClick={() => handleHorizonChange(h.value)}
                  className={`py-2 text-xs font-bold rounded-lg text-center transition-all ${
                    isSelected
                      ? 'bg-purple-600 text-white shadow-sm'
                      : 'bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {h.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Forecast Hero Card with Chart */}
      <div className="p-6 rounded-3xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-2xl border border-slate-200 dark:border-white/10 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-white/10 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                Statistical OLS Extrapolation
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                forecastData?.is_real_telemetry 
                  ? 'bg-cyan-500 text-white' 
                  : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
              }`}>
                {forecastData?.is_real_telemetry ? 'Real Telemetry' : 'Synthetic Baseline'}
              </span>
              <span className="text-xs text-slate-400">|</span>
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                {selectedServer?.display_name} • {selectedMetric.replace('_', ' ').toUpperCase()} • {forecastData?.horizon_label || horizon}
              </span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white mt-1">
              Resource Consumption Trajectory & Forecast Horizon
            </h2>
          </div>

          {/* Time to threshold countdown */}
          {forecastData?.days_to_threshold !== null && forecastData?.days_to_threshold !== undefined && (
            <div className={`flex items-center gap-3 px-4 py-2 rounded-2xl border ${
              forecastData.days_to_threshold < 7
                ? 'bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400'
                : forecastData.days_to_threshold < 30
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400'
                : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
            }`}>
              <Clock className="w-5 h-5" />
              <div>
                <p className="text-[10px] uppercase font-bold tracking-wider opacity-80">Estimated Days to Exhaustion</p>
                <p className="text-base font-extrabold">{forecastData.days_to_threshold} Days</p>
              </div>
            </div>
          )}
        </div>

        {/* 4 Summary Stat Gauges */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/80 dark:border-white/5">
            <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Current Reading</p>
            <p className="text-xl font-extrabold text-slate-900 dark:text-white mt-1">
              {forecastData?.current_value !== undefined ? forecastData.current_value : '--'}%
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Last observed sample</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/80 dark:border-white/5">
            <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Daily Velocity</p>
            <p className={`text-xl font-extrabold mt-1 ${
              (forecastData?.slope_per_day || 0) > 0 ? 'text-amber-500' : 'text-emerald-500'
            }`}>
              {(forecastData?.slope_per_day || 0) > 0 ? '+' : ''}{forecastData?.slope_per_day || 0}% / day
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Linear growth slope</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/80 dark:border-white/5">
            <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Projected Breach Date</p>
            <p className="text-sm font-extrabold text-slate-900 dark:text-white mt-2 truncate">
              {forecastData?.projected_breach_date ? new Date(forecastData.projected_breach_date).toLocaleDateString() : 'None in horizon'}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Threshold at 90.0%</p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/80 dark:border-white/5">
            <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Model Confidence</p>
            <p className="text-xl font-extrabold text-indigo-500 mt-1">95.0%</p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Normal confidence cone</p>
          </div>
        </div>

        {/* Out-of-Sample Holdout Accuracy Metrics */}
        {forecastData?.accuracy_evaluation && (
          <div className="p-4 rounded-2xl bg-slate-100/70 dark:bg-slate-800/40 border border-slate-200/70 dark:border-white/5 flex flex-wrap items-center justify-between gap-4 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
              <span className="font-bold text-slate-800 dark:text-slate-200">
                Holdout Validation ({forecastData.accuracy_evaluation.train_test_split || '80/20 Time Split'}):
              </span>
              <span className="text-slate-500 dark:text-slate-400">
                {forecastData.accuracy_evaluation.train_sample_count || 0} train / {forecastData.accuracy_evaluation.test_sample_count || 0} test points
              </span>
            </div>
            <div className="flex items-center gap-6 font-mono font-semibold">
              <span className="text-slate-700 dark:text-slate-300">
                MAE: <strong className="text-indigo-600 dark:text-indigo-400">{forecastData.accuracy_evaluation.mae !== null ? forecastData.accuracy_evaluation.mae : 'N/A'}</strong>
              </span>
              <span className="text-slate-700 dark:text-slate-300">
                RMSE: <strong className="text-purple-600 dark:text-purple-400">{forecastData.accuracy_evaluation.rmse !== null ? forecastData.accuracy_evaluation.rmse : 'N/A'}</strong>
              </span>
              {forecastData.accuracy_evaluation.mape_percent !== null && (
                <span className="text-slate-700 dark:text-slate-300">
                  MAPE: <strong className="text-cyan-600 dark:text-cyan-400">{forecastData.accuracy_evaluation.mape_percent}%</strong>
                </span>
              )}
            </div>
          </div>
        )}

        {/* Visual Chart Canvas */}
        <div className="p-4 rounded-2xl bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-white/10">
          {renderForecastChart()}
        </div>

        {/* Actionable Recommendation Bar */}
        {forecastData?.recommendation && (
          <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-700 dark:text-indigo-300 flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-indigo-500 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-xs font-bold uppercase tracking-wider">Capacity Planning Advisory</p>
              <p className="text-xs leading-relaxed">{forecastData.recommendation}</p>
            </div>
          </div>
        )}

        <div className="text-[11px] text-slate-400 dark:text-slate-500 italic">
          * {forecastData?.disclaimer}
        </div>
      </div>

      {/* AI Forecast Insight Section */}
      {(aiPredictiveData || aiLoading || aiError) ? (
        <AIExplanationCard
          title={`Groq AI Capacity Interpretation (${selectedServer?.display_name || 'Server'})`}
          subtitle={`Forecast explanation for ${selectedMetric} over ${horizon} horizon`}
          data={aiPredictiveData}
          loading={aiLoading}
          error={aiError}
          onRefresh={handleRunAIPredictive}
          type="predictive"
        />
      ) : (
        <div className="p-4 rounded-2xl border border-dashed border-indigo-200 dark:border-indigo-800/60 bg-gradient-to-r from-indigo-50/50 via-white to-purple-50/30 dark:from-slate-900/40 dark:via-slate-900/40 dark:to-indigo-950/20 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Want an AI interpretation of this capacity trajectory?
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Groq analyzes daily growth velocity, projects breach timelines, and evaluates holdout accuracy.
              </p>
            </div>
          </div>
          <button
            onClick={handleRunAIPredictive}
            disabled={aiLoading || !selectedServer}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-md shadow-indigo-500/20 transition-all hover:scale-105 active:scale-95 shrink-0"
          >
            <Sparkles className="w-4 h-4 fill-current" />
            <span>Generate AI Insight</span>
          </button>
        </div>
      )}

      {/* Active Capacity Warnings */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Active Capacity Warnings ({capacityWarnings.length})
            </h2>
          </div>
          <span className="text-xs text-slate-400">Continuous Trend Horizon Evaluation</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {capacityWarnings.length === 0 ? (
            <div className="col-span-2 p-8 rounded-2xl bg-white/70 dark:bg-slate-800/70 border border-slate-200 dark:border-white/10 text-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                No Impending Capacity Breaches Detected
              </p>
              <p className="text-xs text-slate-400 mt-1">All nodes are within safe operational limits.</p>
            </div>
          ) : (
            capacityWarnings.map((w, idx) => (
              <div 
                key={w.id || idx}
                className={`p-5 rounded-3xl border backdrop-blur-xl transition-all shadow-sm ${
                  w.severity === 'critical'
                    ? 'bg-red-500/5 border-red-500/30'
                    : 'bg-amber-500/5 border-amber-500/30'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                        w.severity === 'critical'
                          ? 'bg-red-500 text-white'
                          : 'bg-amber-500 text-white'
                      }`}>
                        {w.severity}
                      </span>
                      <span className="text-xs font-bold text-slate-900 dark:text-white">
                        {w.component_name}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      Metric: <span className="font-semibold text-slate-700 dark:text-slate-300">{w.metric_name}</span> (Current: {w.current_value}%)
                    </p>
                  </div>

                  <div className="text-right">
                    <p className="text-[10px] uppercase font-bold text-slate-400">Time to Threshold</p>
                    <p className="text-base font-extrabold text-red-500">{w.days_to_exhaustion} Days</p>
                  </div>
                </div>

                <div className="mt-4 p-3 rounded-xl bg-white/60 dark:bg-slate-900/60 border border-slate-200/50 dark:border-white/5 space-y-2">
                  <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                    {w.recommended_action}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Service Level Objectives (SLO) & Error Budgets */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-indigo-500" />
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Service Level Objectives (SLO) & Error Budgets
            </h2>
          </div>
          <span className="text-xs text-slate-400">Google SRE Error Budget Framework (30-Day Window)</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {sloMetrics.map((slo) => {
            const isBreached = slo.status === 'breached';
            const isWarning = slo.status === 'warning';
            const budgetPct = slo.error_budget_remaining_percent || 0;

            return (
              <div 
                key={slo.id}
                className="p-5 rounded-3xl bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 shadow-sm space-y-4 hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                      {slo.service_name} • {slo.sli_type}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white mt-0.5 line-clamp-1">
                      {slo.name}
                    </h3>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    isBreached 
                      ? 'bg-red-500/10 text-red-500 border border-red-500/20' 
                      : isWarning
                      ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                      : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                  }`}>
                    {slo.status}
                  </span>
                </div>

                {/* Attainment Gauge */}
                <div className="flex items-baseline justify-between">
                  <div>
                    <p className="text-2xl font-extrabold text-slate-900 dark:text-white">
                      {slo.current_sli}%
                    </p>
                    <p className="text-[11px] text-slate-400">Target: {slo.target_percentage}%</p>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1 text-xs font-semibold text-slate-600 dark:text-slate-300">
                      <Flame className={`w-3.5 h-3.5 ${slo.burn_rate > 2 ? 'text-red-500 animate-pulse' : 'text-slate-400'}`} />
                      <span>{slo.burn_rate}x Burn</span>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-0.5">{slo.error_budget_total_minutes}m budget</p>
                  </div>
                </div>

                {/* Error Budget Bar */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    <span>Remaining Budget</span>
                    <span className="font-bold text-slate-900 dark:text-white">{budgetPct}%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 ${
                        budgetPct < 20
                          ? 'bg-red-500'
                          : budgetPct < 50
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, budgetPct))}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Configure Custom SLO Modal */}
      {showSloModal && createPortal(
        <div 
          onClick={(e) => { if (e.target === e.currentTarget) setShowSloModal(false); }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn"
        >
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">Configure Service Level Objective (SLO)</h3>
              <button 
                onClick={() => setShowSloModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSlo} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Objective Name</label>
                <input 
                  type="text" 
                  value={newSloName} 
                  onChange={(e) => setNewSloName(e.target.value)} 
                  placeholder="e.g. Ingress API Availability" 
                  required
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Target Service</label>
                <input 
                  type="text" 
                  value={newSloService} 
                  onChange={(e) => setNewSloService(e.target.value)} 
                  placeholder="e.g. api-gateway, order-service, global" 
                  required
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">SLI Metric Type</label>
                  <select 
                    value={newSloType} 
                    onChange={(e) => setNewSloType(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="availability">Availability (% 2xx/3xx)</option>
                    <option value="latency_p95">p95 Latency (&lt; 250ms)</option>
                    <option value="error_rate">Error Rate (&lt; 0.5%)</option>
                    <option value="uptime">Node Uptime</option>
                  </select>
                </div>

                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Target %</label>
                  <input 
                    type="number" 
                    step="0.01" 
                    min="50" 
                    max="100" 
                    value={newSloTarget} 
                    onChange={(e) => setNewSloTarget(e.target.value)} 
                    required
                    className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-white/5">
                <button
                  type="button"
                  onClick={() => setShowSloModal(false)}
                  className="px-4 py-2 rounded-xl font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl font-semibold bg-purple-600 text-white shadow-md shadow-purple-500/20"
                >
                  Save Objective
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
