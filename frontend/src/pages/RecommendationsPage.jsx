// frontend/src/pages/RecommendationsPage.jsx
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import { 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  RefreshCw, 
  ExternalLink, 
  Clock, 
  UserCheck,
  Check,
  XCircle,
  HelpCircle,
  Lightbulb
} from 'lucide-react';

export default function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      const res = await api.getRecommendations(severityFilter, statusFilter);
      setRecommendations(res);
    } catch (err) {
      console.error('Failed to load recommendations', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [severityFilter, statusFilter]);

  const handleUpdateStatus = async (id, status) => {
    setActionLoading(true);
    try {
      await api.updateRecommendationStatus(id, status);
      await fetchRecommendations();
    } catch (err) {
      console.error('Failed to update recommendation', err);
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
              <Lightbulb className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Actionable Intelligent Recommendations
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Engineered operational advice tied to active incidents and breaches. Strictly requires human-in-the-loop review.
          </p>
        </div>
        <button 
          onClick={fetchRecommendations}
          disabled={loading}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 transition shadow-xs active:scale-[0.98] disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-500' : ''}`} />
          Refresh Recommendations
        </button>
      </div>

      {/* Safety Guardrail Banner */}
      <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-cyan-50 via-sky-50/50 to-blue-50 dark:from-cyan-950/50 dark:via-blue-950/30 dark:to-slate-950/50 border border-cyan-200 dark:border-cyan-500/30 flex flex-col sm:flex-row items-start sm:items-center gap-4 shadow-soft">
        <div className="p-2.5 rounded-xl bg-cyan-600 text-white shadow-md shadow-cyan-600/20 shrink-0">
          <UserCheck className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-900 dark:text-cyan-300">
            Safety Guardrail: Human-in-the-Loop Remediations Only
          </h3>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed max-w-4xl">
            ObserveVault strictly adheres to safe operational principles. The system will never execute destructive or speculative commands (such as node restarts, configuration overrides, or firewall drops) autonomously. Every recommendation provides transparent rationale, affected components, and requires explicit engineer approval.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-3.5 rounded-2xl glass-card text-xs shadow-soft">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-500 dark:text-slate-400 font-semibold">Severity:</span>
          {['', 'critical', 'high', 'medium', 'informational'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-3 py-1 rounded-lg capitalize font-medium transition ${
                severityFilter === sev 
                  ? 'bg-cyan-500 text-white shadow-xs font-semibold' 
                  : 'bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {sev || 'All'}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-500 dark:text-slate-400 font-semibold">Status:</span>
          {['', 'pending', 'acknowledged', 'completed', 'dismissed'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded-lg capitalize font-medium transition ${
                statusFilter === st 
                  ? 'bg-slate-900 dark:bg-slate-700 text-white shadow-xs font-semibold' 
                  : 'bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {st || 'All'}
            </button>
          ))}
        </div>
      </div>

      {/* Recommendations Cards List */}
      <div className="space-y-4">
        {loading ? (
          <div className="glass-card rounded-2xl p-12 text-center text-slate-400 shadow-soft">
            <div className="flex items-center justify-center gap-2 text-xs">
              <div className="w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
              Loading recommendations...
            </div>
          </div>
        ) : recommendations.length === 0 ? (
          <div className="glass-card rounded-2xl p-12 text-center text-slate-400 shadow-soft">
            <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3 opacity-90" />
            <p className="text-sm font-bold text-slate-800 dark:text-slate-200">No pending recommendations</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">All infrastructure components are operating within nominal thresholds.</p>
          </div>
        ) : (
          recommendations.map((rec) => (
            <div 
              key={rec.id} 
              className="glass-card rounded-2xl p-6 shadow-soft hover:border-cyan-400/50 dark:hover:border-cyan-500/40 transition-all duration-200 space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-slate-100 dark:border-slate-800/80 pb-4">
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={rec.severity} size="xs" />
                    <span className="text-[10px] uppercase font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      {rec.category}
                    </span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-500/30 flex items-center gap-1">
                      <UserCheck className="w-3 h-3" />
                      Human Approval Required
                    </span>
                  </div>
                  <h3 className="text-base font-extrabold text-slate-900 dark:text-white pt-1">{rec.title}</h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{rec.description}</p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <StatusBadge status={rec.status} />
                  {rec.status === 'pending' && (
                    <div className="flex items-center gap-1.5 ml-2">
                      <button
                        disabled={actionLoading}
                        onClick={() => handleUpdateStatus(rec.id, 'acknowledged')}
                        className="px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 transition shadow-xs"
                      >
                        Ack
                      </button>
                      <button
                        disabled={actionLoading}
                        onClick={() => handleUpdateStatus(rec.id, 'completed')}
                        className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white transition flex items-center gap-1 shadow-md shadow-emerald-600/20"
                      >
                        <Check className="w-3 h-3" />
                        Complete
                      </button>
                      <button
                        disabled={actionLoading}
                        onClick={() => handleUpdateStatus(rec.id, 'dismissed')}
                        className="p-1.5 rounded-xl hover:bg-rose-50 dark:hover:bg-rose-950/50 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 transition"
                        title="Dismiss"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Rationale */}
              <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 space-y-1">
                <span className="text-[10px] font-mono uppercase font-bold text-slate-500 dark:text-slate-400">
                  Underlying Anomaly Rationale
                </span>
                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
                  {rec.rationale}
                </p>
              </div>

              {/* Action Steps */}
              {rec.action_steps?.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[10px] font-mono uppercase font-bold text-slate-500 dark:text-slate-400">
                    Recommended Implementation Protocol
                  </span>
                  <div className="space-y-1.5">
                    {rec.action_steps.map((step, idx) => (
                      <div key={idx} className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50/60 dark:bg-slate-950/50 border border-slate-200/60 dark:border-slate-800/60 text-xs text-slate-700 dark:text-slate-300">
                        <span className="w-5 h-5 rounded-full bg-cyan-100 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-400 border border-cyan-300 dark:border-cyan-500/30 flex items-center justify-center font-mono text-[10px] font-bold shrink-0 mt-0.5">
                          {idx + 1}
                        </span>
                        <span className="leading-relaxed">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
