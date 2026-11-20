// frontend/src/pages/AlertsIncidentsPage.jsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import { 
  AlertTriangle, 
  Activity, 
  CheckCircle2, 
  Clock, 
  Search, 
  Filter, 
  RefreshCw, 
  ChevronRight,
  ShieldAlert,
  Server,
  Zap,
  Check,
  RotateCcw,
  Sparkles,
  Compass,
  Brain,
  ShieldCheck,
  Terminal,
  ThumbsUp
} from 'lucide-react';
import AIExplanationCard from '../components/ai/AIExplanationCard';

export default function AlertsIncidentsPage() {
  const [activeTab, setActiveTab] = useState('incidents'); // 'incidents' | 'alerts'
  const [incidents, setIncidents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  // AI Incident Intelligence State (Phase 3)
  const [aiExplainData, setAiExplainData] = useState(null);
  const [aiExplainLoading, setAiExplainLoading] = useState(false);
  const [aiExplainError, setAiExplainError] = useState(null);

  const [aiRemediationData, setAiRemediationData] = useState(null);
  const [aiRemediationLoading, setAiRemediationLoading] = useState(false);
  const [aiRemediationError, setAiRemediationError] = useState(null);
  const [approvedSteps, setApprovedSteps] = useState(new Set());

  const handleExplainIncident = async (incidentId) => {
    if (!incidentId) return;
    setAiExplainLoading(true);
    setAiExplainError(null);
    try {
      const res = await api.explainIncident(incidentId);
      setAiExplainData(res);
    } catch (err) {
      console.error('Failed to explain incident with AI:', err);
      setAiExplainError(err.message || 'Failed to generate AI incident explanation.');
    } finally {
      setAiExplainLoading(false);
    }
  };

  const handleGetRemediationPlan = async (incidentId) => {
    if (!incidentId) return;
    setAiRemediationLoading(true);
    setAiRemediationError(null);
    try {
      const res = await api.getRemediationPlan(incidentId);
      setAiRemediationData(res);
    } catch (err) {
      console.error('Failed to generate remediation plan:', err);
      setAiRemediationError(err.message || 'Failed to generate remediation plan.');
    } finally {
      setAiRemediationLoading(false);
    }
  };

  const toggleStepApproval = (stepNumber) => {
    setApprovedSteps(prev => {
      const updated = new Set(prev);
      if (updated.has(stepNumber)) {
        updated.delete(stepNumber);
      } else {
        updated.add(stepNumber);
      }
      return updated;
    });
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const [incRes, alRes] = await Promise.all([
        api.getIncidents(statusFilter),
        api.getAlerts(statusFilter)
      ]);
      setIncidents(incRes);
      setAlerts(alRes);
      if (selectedIncident) {
        const updated = incRes.find(i => i.id === selectedIncident.id);
        if (updated) setSelectedIncident(updated);
      }
    } catch (err) {
      console.error('Failed to load alerts and incidents', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const handleUpdateAlertStatus = async (alertId, newStatus) => {
    setActionLoading(true);
    try {
      await api.updateAlertStatus(alertId, newStatus);
      await fetchData();
    } catch (err) {
      console.error('Failed to update alert', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateIncidentStatus = async (incidentId, newStatus) => {
    setActionLoading(true);
    try {
      await api.updateIncidentStatus(incidentId, newStatus);
      await fetchData();
    } catch (err) {
      console.error('Failed to update incident', err);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-cyan-50 dark:bg-cyan-950/60 text-cyan-600 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-800/40">
              <Activity className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Alerts & Incident Correlation
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Correlate related infrastructure breaches into actionable incidents with explainable probable causes and evidence.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Tab Switcher */}
          <div className="flex items-center p-1 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <button
              onClick={() => setActiveTab('incidents')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === 'incidents'
                  ? 'bg-white dark:bg-slate-800 text-cyan-700 dark:text-cyan-300 shadow-xs border border-slate-200/60 dark:border-slate-700'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Correlated Incidents ({incidents.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('alerts')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === 'alerts'
                  ? 'bg-white dark:bg-slate-800 text-cyan-700 dark:text-cyan-300 shadow-xs border border-slate-200/60 dark:border-slate-700'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Telemetry Alerts ({alerts.length})</span>
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

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl glass-card text-xs shadow-soft">
        <div className="flex flex-wrap items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-500 dark:text-slate-400 font-semibold">Filter Status:</span>
          {['', 'open', 'investigating', 'acknowledged', 'resolved'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded-lg capitalize font-medium transition ${
                statusFilter === st 
                  ? 'bg-cyan-500 text-white shadow-xs font-semibold' 
                  : 'bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {st || 'All'}
            </button>
          ))}
        </div>
      </div>

      {/* INCIDENTS TAB */}
      {activeTab === 'incidents' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Incident List */}
          <div className={`${selectedIncident ? 'lg:col-span-5' : 'lg:col-span-12'} space-y-3`}>
            {incidents.length === 0 ? (
              <div className="glass-card rounded-2xl p-12 text-center text-slate-400 shadow-soft">
                <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3 opacity-90" />
                <p className="text-sm font-bold text-slate-800 dark:text-slate-200">No active incidents found</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">All correlated events have been resolved or nominal.</p>
              </div>
            ) : (
              incidents.map((inc) => (
                <div
                  key={inc.id}
                  onClick={() => setSelectedIncident(inc)}
                  className={`p-4 rounded-2xl glass-card cursor-pointer border transition-all duration-200 ${
                    selectedIncident?.id === inc.id
                      ? 'border-cyan-500 ring-2 ring-cyan-500/20 bg-cyan-50/20 dark:bg-slate-900/90 shadow-md shadow-cyan-500/10'
                      : 'border-slate-200/80 dark:border-slate-800/80 hover:border-cyan-400/50 hover:bg-slate-50/50 dark:hover:bg-slate-800/40 shadow-soft'
                  } space-y-2.5`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400">{inc.incident_code}</span>
                    <div className="flex items-center gap-1.5">
                      <StatusBadge status={inc.severity} size="xs" />
                      <StatusBadge status={inc.status} size="xs" />
                    </div>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">{inc.title}</h3>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-1.5 border-t border-slate-100 dark:border-slate-800/60 font-medium">
                    <span>Target: <strong className="text-slate-700 dark:text-slate-300 font-normal">{inc.primary_server_name || 'Cluster'}</strong></span>
                    <span className="font-mono text-cyan-600 dark:text-cyan-400">Confidence: {(inc.confidence_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Incident Detail Drawer */}
          {selectedIncident && (
            <div className="lg:col-span-7 glass-card rounded-2xl p-6 border border-cyan-500/40 shadow-soft-lg space-y-5 animate-fadeIn">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-slate-100 dark:border-slate-800/80 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400">{selectedIncident.incident_code}</span>
                    <StatusBadge status={selectedIncident.severity} size="xs" />
                    <StatusBadge status={selectedIncident.status} size="xs" />
                  </div>
                  <h2 className="text-base font-extrabold text-slate-900 dark:text-white mt-1.5">{selectedIncident.title}</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Correlated on {new Date(selectedIncident.created_at).toLocaleString()}
                  </p>
                </div>
                {/* Actions */}
                <div className="flex items-center gap-2">
                  {/* AI Explain & Remediation Action Buttons */}
                  <button
                    disabled={aiExplainLoading}
                    onClick={() => handleExplainIncident(selectedIncident.id)}
                    className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-xs font-bold text-white transition flex items-center gap-1.5 shadow-md shadow-indigo-600/20 disabled:opacity-50"
                    title="Generate grounded AI incident narrative"
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${aiExplainLoading ? 'animate-spin' : ''}`} />
                    <span>{aiExplainLoading ? 'Analyzing...' : 'AI Explain'}</span>
                  </button>

                  <button
                    disabled={aiRemediationLoading}
                    onClick={() => handleGetRemediationPlan(selectedIncident.id)}
                    className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-xs font-bold text-white transition flex items-center gap-1.5 shadow-md shadow-purple-600/20 disabled:opacity-50"
                    title="Synthesize risk-tiered remediation steps"
                  >
                    <ShieldCheck className={`w-3.5 h-3.5 ${aiRemediationLoading ? 'animate-spin' : ''}`} />
                    <span>{aiRemediationLoading ? 'Planning...' : 'AI Remediation Plan'}</span>
                  </button>

                  <Link
                    to={`/rca?incidentId=${selectedIncident.id}`}
                    className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-xs font-bold text-white transition flex items-center gap-1.5 shadow-md shadow-indigo-600/20"
                  >
                    <Compass className="w-3.5 h-3.5" />
                    Deep RCA ➔
                  </Link>
                  {selectedIncident.status !== 'resolved' ? (
                    <>
                      <button
                        disabled={actionLoading}
                        onClick={() => handleUpdateIncidentStatus(selectedIncident.id, 'acknowledged')}
                        className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 transition shadow-xs"
                      >
                        Acknowledge
                      </button>
                      <button
                        disabled={actionLoading}
                        onClick={() => handleUpdateIncidentStatus(selectedIncident.id, 'resolved')}
                        className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white transition flex items-center gap-1.5 shadow-md shadow-emerald-600/20"
                      >
                        <Check className="w-3.5 h-3.5" />
                        Resolve Incident
                      </button>
                    </>
                  ) : (
                    <button
                      disabled={actionLoading}
                      onClick={() => handleUpdateIncidentStatus(selectedIncident.id, 'open')}
                      className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 transition"
                    >
                      Re-open
                    </button>
                  )}
                </div>
              </div>

              {/* Probable Cause & Correlation */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-cyan-50/70 via-blue-50/50 to-indigo-50/70 dark:from-cyan-950/40 dark:via-blue-950/30 dark:to-slate-950/40 border border-cyan-200 dark:border-cyan-500/30 space-y-1.5">
                <span className="text-[10px] font-mono uppercase font-bold text-cyan-800 dark:text-cyan-400 flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                  Correlated Probable Cause ({Math.round(selectedIncident.confidence_score * 100)}% Confidence)
                </span>
                <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-semibold">
                  {selectedIncident.possible_cause}
                </p>
              </div>

              {/* Supporting Evidence */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono uppercase font-bold text-slate-500 dark:text-slate-400">
                  Supporting Telemetry Evidence
                </span>
                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 font-mono text-[11px]">
                  {selectedIncident.evidence_summary}
                </p>
              </div>

              {/* AI Grounded Incident Explanation */}
              {(aiExplainData || aiExplainLoading || aiExplainError) && (
                <AIExplanationCard
                  title={`Groq AI Explanation (${selectedIncident.incident_code})`}
                  subtitle="Grounded incident narrative separating confirmed facts from hypotheses"
                  data={aiExplainData}
                  loading={aiExplainLoading}
                  error={aiExplainError}
                  onRefresh={() => handleExplainIncident(selectedIncident.id)}
                  type="incident"
                />
              )}

              {/* AI Remediation Plan Panel */}
              {(aiRemediationData || aiRemediationLoading || aiRemediationError) && (
                <div className="p-4 rounded-xl border border-indigo-200/80 dark:border-indigo-500/30 bg-gradient-to-br from-indigo-50/40 via-white to-purple-50/20 dark:from-slate-900/90 dark:via-indigo-950/20 dark:to-slate-900/90 space-y-3.5">
                  <div className="flex items-center justify-between border-b border-indigo-100 dark:border-indigo-500/20 pb-2.5">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                        AI Prioritized Remediation Plan
                      </h4>
                    </div>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700/50">
                      Human Approval Required
                    </span>
                  </div>

                  {aiRemediationLoading ? (
                    <div className="py-6 text-center text-xs text-slate-500 dark:text-slate-400 flex items-center justify-center gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-500" />
                      Synthesizing safe remediation steps...
                    </div>
                  ) : aiRemediationError ? (
                    <div className="text-xs text-rose-600 dark:text-rose-400">
                      {aiRemediationError}
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-mono">
                        {aiRemediationData.strategy_overview}
                      </p>

                      <div className="space-y-2">
                        {aiRemediationData.prioritized_steps?.map((step) => {
                          const isApproved = approvedSteps.has(step.step_number);
                          return (
                            <div 
                              key={step.step_number}
                              className={`p-3 rounded-xl border text-xs transition-all ${
                                isApproved 
                                  ? 'bg-emerald-50/70 dark:bg-emerald-950/20 border-emerald-300 dark:border-emerald-600/40' 
                                  : 'bg-white dark:bg-slate-800/80 border-slate-200 dark:border-slate-700'
                              }`}
                            >
                              <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-2 font-bold text-slate-800 dark:text-slate-100">
                                  <span className="w-5 h-5 rounded-full bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 text-[10px] flex items-center justify-center font-mono shrink-0">
                                    {step.step_number}
                                  </span>
                                  <span>{step.action}</span>
                                </div>
                                <span className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded-full font-bold shrink-0 ${
                                  step.risk_level === 'high'
                                    ? 'bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300'
                                    : step.risk_level === 'medium'
                                      ? 'bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300'
                                      : 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300'
                                }`}>
                                  Risk: {step.risk_level}
                                </span>
                              </div>

                              <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-1 pl-7">
                                <strong>Rationale:</strong> {step.rationale}
                              </p>
                              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 pl-7 font-mono">
                                <strong>Rollback:</strong> {step.rollback_procedure}
                              </p>

                              <div className="mt-2.5 pl-7 flex items-center justify-between">
                                <span className="text-[10px] text-slate-400 italic">
                                  Target: {step.target_component}
                                </span>
                                <button
                                  onClick={() => toggleStepApproval(step.step_number)}
                                  className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                                    isApproved
                                      ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs'
                                      : 'bg-slate-100 dark:bg-slate-700 hover:bg-indigo-50 dark:hover:bg-indigo-950 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-600'
                                  }`}
                                >
                                  {isApproved ? (
                                    <>
                                      <Check className="w-3.5 h-3.5" />
                                      Approved by SRE
                                    </>
                                  ) : (
                                    <>
                                      <ThumbsUp className="w-3.5 h-3.5" />
                                      Review & Approve
                                    </>
                                  )}
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      <div className="p-2.5 rounded-lg bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200/60 dark:border-amber-800/40 text-[11px] text-amber-800 dark:text-amber-300 flex items-center gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                        <span>Safety Policy: Autonomous execution is disabled. Human approval required before operational changes.</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Related Alerts in this Incident */}
              <div className="space-y-2">
                <span className="text-[10px] font-mono uppercase font-bold text-slate-500 dark:text-slate-400">
                  Associated Telemetry Alerts ({selectedIncident.related_alerts?.length || 0})
                </span>
                <div className="space-y-2">
                  {selectedIncident.related_alerts?.map((ra) => (
                    <div key={ra.id} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between text-xs">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <StatusBadge status={ra.severity} size="xs" />
                          <span className="font-bold text-slate-800 dark:text-slate-200">{ra.title}</span>
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                          Observed: {ra.observed_value} vs Threshold {ra.threshold_value} ({ra.metric_name})
                        </p>
                      </div>
                      <StatusBadge status={ra.status} size="xs" />
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommended Remediation Steps */}
              <div className="space-y-2">
                <span className="text-[10px] font-mono uppercase font-bold text-slate-500 dark:text-slate-400">
                  Actionable Next Steps (Human Approval Required)
                </span>
                <div className="space-y-1.5">
                  {selectedIncident.recommended_actions?.map((act, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/40 text-xs text-slate-700 dark:text-slate-300 border border-slate-200/80 dark:border-slate-800/60">
                      <span className="w-5 h-5 rounded-full bg-cyan-100 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-400 border border-cyan-300 dark:border-cyan-500/30 flex items-center justify-center font-mono text-[10px] font-bold shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <span className="leading-relaxed">{act}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ALERTS TAB */}
      {activeTab === 'alerts' && (
        <div className="glass-card rounded-2xl overflow-hidden shadow-soft">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 dark:bg-slate-900/80 text-slate-600 dark:text-slate-400 font-mono text-[10px] uppercase border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4 font-semibold">Alert Title</th>
                  <th className="py-3 px-4 font-semibold">Severity</th>
                  <th className="py-3 px-4 font-semibold">Server</th>
                  <th className="py-3 px-4 font-semibold">Observed Metric</th>
                  <th className="py-3 px-4 font-semibold">Threshold</th>
                  <th className="py-3 px-4 font-semibold">Detected At</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {alerts.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="py-12 text-center text-slate-400 dark:text-slate-500 font-sans">
                      No active alerts recorded.
                    </td>
                  </tr>
                ) : (
                  alerts.map((al) => (
                    <tr key={al.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-bold text-slate-900 dark:text-slate-200">
                        {al.title}
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={al.severity} size="xs" />
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600 dark:text-slate-300">
                        {al.server_hostname || al.server_id}
                      </td>
                      <td className="py-3 px-4 font-mono text-rose-600 dark:text-rose-400 font-bold">
                        {al.observed_value} ({al.metric_name})
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-500 dark:text-slate-400">
                        {al.threshold_value}
                      </td>
                      <td className="py-3 px-4 text-slate-500 dark:text-slate-400 text-[11px] font-mono">
                        {new Date(al.created_at).toLocaleTimeString()}
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={al.status} size="xs" />
                      </td>
                      <td className="py-3 px-4 text-right">
                        {al.status === 'active' ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              disabled={actionLoading}
                              onClick={() => handleUpdateAlertStatus(al.id, 'acknowledged')}
                              className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-[11px] font-semibold text-slate-700 dark:text-slate-300 transition"
                            >
                              Ack
                            </button>
                            <button
                              disabled={actionLoading}
                              onClick={() => handleUpdateAlertStatus(al.id, 'resolved')}
                              className="px-2.5 py-1 rounded-lg bg-emerald-100 dark:bg-emerald-950/80 hover:bg-emerald-200 dark:hover:bg-emerald-900 border border-emerald-300 dark:border-emerald-500/30 text-[11px] font-bold text-emerald-800 dark:text-emerald-300 transition"
                            >
                              Resolve
                            </button>
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-400 dark:text-slate-500 font-mono font-medium">Resolved</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
