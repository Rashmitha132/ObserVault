import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import {
  Compass,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight,
  GitBranch,
  Search,
  Copy,
  Check,
  Brain,
  Server,
  Activity,
  Terminal,
  ShieldAlert,
  Info,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  Sparkles
} from 'lucide-react';
import AIExplanationCard from '../components/ai/AIExplanationCard';

export default function RootCauseAnalysisPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedIncidentId = searchParams.get('incidentId');

  const [incidents, setIncidents] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState(requestedIncidentId || '');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [expandedCandidate, setExpandedCandidate] = useState(null);

  // AI Intelligence State (Phase 3)
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);

  const handleRunAIRCA = async () => {
    if (!selectedIncidentId) return;
    setAiLoading(true);
    setAiError(null);
    try {
      const res = await api.getIncidentAIRCA(selectedIncidentId);
      setAiAnalysis(res);
    } catch (err) {
      console.error('Failed to run AI RCA explanation:', err);
      setAiError(err.message || 'Failed to generate AI RCA explanation.');
    } finally {
      setAiLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, []);

  useEffect(() => {
    if (selectedIncidentId) {
      loadIncidentRCA(selectedIncidentId);
    }
  }, [selectedIncidentId]);

  const loadIncidents = async () => {
    try {
      setLoading(true);
      const incList = await api.getRCAIncidents();
      setIncidents(incList || []);

      if (incList && incList.length > 0) {
        // If query param matched an incident, use it; otherwise pick first
        const match = incList.find(i => i.incident_id === requestedIncidentId);
        const activeId = match ? match.incident_id : incList[0].incident_id;
        setSelectedIncidentId(activeId);
      } else {
        setLoading(false);
      }
    } catch (err) {
      console.error('Failed to load RCA incidents:', err);
      setLoading(false);
    }
  };

  const loadIncidentRCA = async (incidentId) => {
    try {
      setLoading(true);
      const data = await api.getIncidentRCA(incidentId);
      setAnalysis(data);
    } catch (err) {
      console.error('Failed to load RCA details:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectIncident = (id) => {
    setSelectedIncidentId(id);
    setSearchParams({ incidentId: id });
  };

  const handleCopyCommand = (cmd, index) => {
    navigator.clipboard.writeText(cmd);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2500);
  };

  const primaryHypothesis = analysis?.primary_root_cause_hypothesis;
  const blastRadius = analysis?.blast_radius;
  const rankedCandidates = analysis?.ranked_candidates || [];
  const timeline = analysis?.incident_timeline || [];
  const investigationSteps = analysis?.suggested_investigation_steps || [];

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900/60 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-600 text-white shadow-md shadow-indigo-500/20">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                  Intelligent Root Cause Analysis (RCA)
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                  AIOps Stage 2D
                </span>
              </div>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Multi-signal temporal precedence, dependency-tree topology, and causal blast radius.
              </p>
            </div>
          </div>
        </div>

        {/* Incident Selector */}
        <div className="flex items-center gap-3">
          <select
            value={selectedIncidentId}
            onChange={(e) => handleSelectIncident(e.target.value)}
            className="text-xs sm:text-sm px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-medium focus:outline-none focus:ring-1 focus:ring-indigo-500 max-w-xs truncate"
          >
            {incidents.map((inc) => (
              <option key={inc.incident_id} value={inc.incident_id}>
                {inc.incident_code}: {inc.title.slice(0, 45)}...
              </option>
            ))}
          </select>

          {/* AI Explain Button */}
          <button
            onClick={handleRunAIRCA}
            disabled={aiLoading || !selectedIncidentId}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-md shadow-indigo-500/20 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 shrink-0"
            title="Generate AI Root Cause Explanation"
          >
            <Sparkles className={`w-3.5 h-3.5 ${aiLoading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{aiLoading ? 'Synthesizing...' : 'AI Explain'}</span>
          </button>

          <button
            onClick={() => loadIncidentRCA(selectedIncidentId)}
            disabled={loading}
            className="p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors"
            title="Refresh Analysis"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Advisory Disclaimer Notice */}
      <div className="p-4 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/20 border border-indigo-200/80 dark:border-indigo-800/50 text-xs text-indigo-900 dark:text-indigo-200 flex items-start gap-3">
        <Info className="w-5 h-5 text-indigo-600 dark:text-indigo-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-slate-900 dark:text-slate-100">
            Advisory Causal Hypothesis Model:
          </span>
          <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
            Correlation does not equal guaranteed causation. ObserVault calculates explainable causal hypotheses by evaluating temporal sequence ordering (what failed first), service dependency call trees (what called what), and multi-signal telemetry convergence (CPU, ML outliers, trace errors). Results are ranked hypotheses to accelerate human engineering investigation.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-16 text-center text-slate-400 bg-white dark:bg-slate-900/60 rounded-2xl border border-slate-200 dark:border-slate-800">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-500" />
          <p className="text-sm font-medium">Running multi-signal cross-domain correlation...</p>
          <p className="text-xs text-slate-500 mt-1">Analyzing temporal precedence & dependency graphs</p>
        </div>
      ) : !analysis || !primaryHypothesis ? (
        <div className="p-16 text-center border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900/40">
          <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">No Active Incidents Detected</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto mt-1">
            All microservices, databases, and infrastructure nodes are operating within learned baseline parameters.
          </p>
        </div>
      ) : (
        <>
          {/* Hero: Primary Probable Root Cause Hypothesis */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-indigo-950/80 via-slate-900 to-slate-900 border border-indigo-500/30 text-white shadow-lg relative overflow-hidden">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
              <div className="space-y-3 flex-1">
                <div className="flex items-center gap-2.5">
                  <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
                    Primary Suspected Root Cause (Rank #1)
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    Incident {analysis.incident_code}
                  </span>
                </div>

                <div className="space-y-1">
                  <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                    <Server className="w-6 h-6 text-indigo-400" />
                    {primaryHypothesis.name}
                  </h2>
                  <p className="text-xs text-slate-300 uppercase tracking-wider font-mono">
                    Component Type: {primaryHypothesis.component_type}
                  </p>
                </div>

                <p className="text-sm text-slate-300 leading-relaxed font-mono bg-slate-800/40 p-3 rounded-xl border border-slate-700/50">
                  {primaryHypothesis.ranking_rationale}
                </p>

                {/* Converging Signals Badges */}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <span className="text-xs text-slate-400 font-semibold mr-1">Converging Signals:</span>
                  {primaryHypothesis.signals_detected?.map((sig, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg text-xs font-mono font-medium bg-slate-800/80 text-cyan-300 border border-cyan-500/30 flex items-center gap-1.5"
                    >
                      <Activity className="w-3 h-3 text-cyan-400" />
                      {sig.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              </div>

              {/* Confidence Gauge */}
              <div className="flex flex-col sm:flex-row lg:flex-col items-center justify-center p-5 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm min-w-[200px] text-center gap-3">
                <div className="relative w-28 h-28 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-slate-800"
                      strokeWidth="3.5"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className="text-cyan-400 transition-all duration-1000 ease-out"
                      strokeDasharray={`${primaryHypothesis.confidence_percent}, 100`}
                      strokeWidth="3.5"
                      strokeLinecap="round"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <div className="absolute flex flex-col items-center">
                    <span className="text-2xl font-black text-white">
                      {primaryHypothesis.confidence_percent}%
                    </span>
                    <span className="text-[10px] text-cyan-300 uppercase tracking-wider font-semibold">
                      Confidence
                    </span>
                  </div>
                </div>

                <div className="text-xs text-slate-300">
                  Impact: <span className="font-bold text-rose-400 uppercase">{blastRadius?.user_impact_level || 'High'}</span>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {blastRadius?.total_services_impacted || 1} downstream service(s)
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* AI Root Cause Explanation Section */}
          {(aiAnalysis || aiLoading || aiError) ? (
            <AIExplanationCard
              title="Groq AI Root Cause Explanation"
              subtitle="Grounded causal analysis distinguishing empirical facts from ranking heuristics"
              data={aiAnalysis}
              loading={aiLoading}
              error={aiError}
              onRefresh={handleRunAIRCA}
              type="rca"
            />
          ) : (
            <div className="p-4 rounded-2xl border border-dashed border-indigo-200 dark:border-indigo-800/60 bg-gradient-to-r from-indigo-50/50 via-white to-purple-50/30 dark:from-slate-900/40 dark:via-slate-900/40 dark:to-indigo-950/20 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400">
                  <Brain className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Want a grounded AI explanation of this root cause?
                  </h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Groq analyzes temporal precedence, contrasts alternative suspects, and outputs safe diagnostics.
                  </p>
                </div>
              </div>
              <button
                onClick={handleRunAIRCA}
                disabled={aiLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-md shadow-indigo-500/20 transition-all hover:scale-105 active:scale-95 shrink-0"
              >
                <Sparkles className="w-4 h-4 fill-current" />
                <span>Explain with Groq AI</span>
              </button>
            </div>
          )}

          {/* Blast Radius Propagation & Service Path */}
          <div className="p-6 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <GitBranch className="w-5 h-5 text-indigo-500" />
                  Downstream Blast-Radius & Topology Path
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {blastRadius?.causal_link_summary}
                </p>
              </div>
              <span className={`text-xs font-bold uppercase px-2.5 py-1 rounded-full ${
                blastRadius?.user_impact_level === 'critical'
                  ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-900'
                  : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-900'
              }`}>
                {blastRadius?.user_impact_level} User Impact
              </span>
            </div>

            {/* Visual Propagation Chain */}
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 overflow-x-auto">
              <div className="flex items-center gap-3 min-w-[550px]">
                {/* Node 1: Origin */}
                <div className="p-3 rounded-xl border border-rose-500/40 bg-rose-50/50 dark:bg-rose-950/30 flex-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 block mb-1">
                    Origin (Root Cause)
                  </span>
                  <div className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                    {blastRadius?.originating_suspect}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                    Earliest observed anomaly
                  </div>
                </div>

                <ArrowRight className="w-5 h-5 text-slate-400 flex-shrink-0 animate-pulse" />

                {/* Node 2: Directly Affected */}
                <div className="p-3 rounded-xl border border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/30 flex-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 block mb-1">
                    Direct Callers ({blastRadius?.directly_affected_services?.length || 0})
                  </span>
                  <div className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                    {blastRadius?.directly_affected_services?.join(', ') || 'None directly mapped'}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                    Cascading call timeouts
                  </div>
                </div>

                <ArrowRight className="w-5 h-5 text-slate-400 flex-shrink-0" />

                {/* Node 3: Indirectly Affected (Gateway / Users) */}
                <div className="p-3 rounded-xl border border-indigo-500/40 bg-indigo-50/50 dark:bg-indigo-950/30 flex-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 block mb-1">
                    Upstream Gateway & Users
                  </span>
                  <div className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                    {blastRadius?.indirectly_affected_services?.join(', ') || 'api-gateway'}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                    504 Gateway Timeouts
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Two-Column Grid: Ranked Candidates vs Incident Timeline */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Ranked Root Cause Candidates */}
            <div className="p-6 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Layers className="w-5 h-5 text-indigo-500" />
                  Ranked Causal Candidates
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Ranked by temporal precedence ($T_0$), callee dependency depth, and multi-signal convergence.
                </p>
              </div>

              <div className="space-y-3">
                {rankedCandidates.map((c) => (
                  <div
                    key={c.candidate_id}
                    className={`p-4 rounded-xl border transition-all ${
                      c.is_primary_hypothesis
                        ? 'border-indigo-500/40 bg-indigo-50/30 dark:bg-indigo-950/20'
                        : 'border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                          c.rank === 1
                            ? 'bg-indigo-600 text-white shadow-sm'
                            : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
                        }`}>
                          #{c.rank}
                        </span>
                        <div>
                          <div className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
                            {c.name}
                            {c.is_primary_hypothesis && (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300">
                                Primary Hypothesis
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            {c.component_type} • {c.signal_count} signal type(s)
                          </div>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-sm font-bold text-indigo-600 dark:text-indigo-400">
                          {c.confidence_percent}%
                        </div>
                        <div className="text-[10px] text-slate-400 uppercase font-semibold">
                          Score
                        </div>
                      </div>
                    </div>

                    {/* Supporting Evidence Items */}
                    <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700/60 space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
                      <span className="text-[11px] font-semibold text-slate-900 dark:text-slate-200">
                        Supporting Telemetry Facts:
                      </span>
                      {c.supporting_evidence?.map((ev, i) => (
                        <div key={i} className="flex items-start gap-1.5 text-slate-600 dark:text-slate-400 font-mono text-[11px]">
                          <span className="text-indigo-500 mt-0.5">•</span>
                          <span>{ev}</span>
                        </div>
                      ))}
                    </div>

                    {/* Alternative Hypotheses */}
                    {c.alternative_hypotheses?.length > 0 && (
                      <div className="mt-2.5 p-2 rounded-lg bg-white/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400">
                        <span className="font-semibold text-slate-700 dark:text-slate-300">Alternative Hypothesis: </span>
                        {c.alternative_hypotheses[0]}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Right: Incident Chronological Timeline */}
            <div className="p-6 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Clock className="w-5 h-5 text-indigo-500" />
                  Chronological Incident Timeline
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Reconstructed sequence of events from first suspicious trigger to cascading alerts.
                </p>
              </div>

              <div className="space-y-4 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-800">
                {timeline.map((evt, idx) => (
                  <div key={idx} className="relative flex items-start gap-3.5 pl-1 group">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 z-10 text-[10px] font-bold ${
                      evt.type === 'INFRASTRUCTURE_ALERT'
                        ? 'bg-rose-500 text-white ring-4 ring-rose-100 dark:ring-rose-950'
                        : evt.type === 'ML_ANOMALY'
                        ? 'bg-indigo-500 text-white ring-4 ring-indigo-100 dark:ring-indigo-950'
                        : evt.type === 'TRACE_FAILURE'
                        ? 'bg-amber-500 text-white ring-4 ring-amber-100 dark:ring-amber-950'
                        : 'bg-emerald-500 text-white ring-4 ring-emerald-100 dark:ring-emerald-950'
                    }`}>
                      {idx + 1}
                    </div>

                    <div className="flex-1 p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 group-hover:border-indigo-500/40 transition-all">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-xs text-slate-900 dark:text-slate-100">
                          {evt.title}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          {new Date(evt.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 font-mono">
                        {evt.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Suggested Investigation Next Steps Card */}
          <div className="p-6 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Terminal className="w-5 h-5 text-indigo-500" />
                Evidence-Based Investigation Next Steps
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Advisory engineering actions derived directly from observed telemetry patterns. (Non-destructive).
              </p>
            </div>

            <div className="space-y-3">
              {investigationSteps.map((step, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 space-y-2"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <span className="w-5 h-5 rounded-md bg-indigo-100 text-indigo-700 dark:bg-indigo-900/60 dark:text-indigo-300 text-xs font-bold flex items-center justify-center">
                        {step.step_number}
                      </span>
                      <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                        {step.title}
                      </h4>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed pl-7">
                    <strong className="text-slate-700 dark:text-slate-300">Rationale: </strong>
                    {step.rationale}
                  </p>

                  {step.command_hint && (
                    <div className="pl-7 pt-1">
                      <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 dark:bg-black/60 text-emerald-400 font-mono text-xs border border-slate-800">
                        <span className="truncate pr-3">{step.command_hint}</span>
                        <button
                          onClick={() => handleCopyCommand(step.command_hint, idx)}
                          className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white transition-colors flex-shrink-0"
                          title="Copy Diagnostic Command"
                        >
                          {copiedIndex === idx ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                              <span className="text-emerald-400">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
