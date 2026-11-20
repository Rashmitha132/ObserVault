// frontend/src/components/ai/AIExplanationCard.jsx
import React, { useState } from 'react';
import {
  Sparkles,
  Brain,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Terminal,
  Copy,
  Check,
  RefreshCw,
  Info,
  ChevronDown,
  ChevronUp,
  Activity,
  Flame,
  HelpCircle
} from 'lucide-react';

export default function AIExplanationCard({
  title = "AI Incident Explanation",
  subtitle = "Grounded narrative synthesis powered by Groq",
  data = null,
  loading = false,
  error = null,
  onRefresh = null,
  type = "incident" // 'incident' | 'rca' | 'predictive'
}) {
  const [showRawNarrative, setShowRawNarrative] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="rounded-2xl border border-indigo-200/80 dark:border-indigo-500/20 bg-gradient-to-br from-white via-indigo-50/20 to-slate-50 dark:from-slate-900/90 dark:via-indigo-950/20 dark:to-slate-900/90 shadow-sm overflow-hidden transition-all duration-200">
      {/* Header Banner */}
      <div className="p-4 sm:p-5 border-b border-indigo-100 dark:border-indigo-500/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 text-white shadow-md shadow-indigo-500/20 shrink-0">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 tracking-tight">
                {title}
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-700/50 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" />
                Groq AI
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {subtitle}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 self-end sm:self-auto">
          {data?.model_used && (
            <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 hidden md:inline">
              Model: {data.model_used}
            </span>
          )}
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-500 text-slate-700 dark:text-slate-200 transition shadow-xs disabled:opacity-50"
              title="Regenerate Analysis"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-500' : ''}`} />
              <span>{loading ? 'Synthesizing...' : 'Regenerate'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Content Area */}
      <div className="p-4 sm:p-6 space-y-5">
        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
            <div className="relative flex items-center justify-center">
              <div className="w-10 h-10 border-2 border-indigo-500/20 border-t-indigo-600 rounded-full animate-spin" />
              <Sparkles className="w-4 h-4 text-indigo-500 absolute animate-pulse" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                Grounding AI context on verified observability records...
              </p>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 font-mono">
                Querying Groq with strict privacy filters and anti-hallucination bounds
              </p>
            </div>
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-50/80 dark:bg-rose-950/20 border border-rose-200/80 dark:border-rose-900/40 text-xs space-y-2">
            <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 font-bold">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>AI Synthesis Notice</span>
            </div>
            <p className="text-slate-700 dark:text-slate-300 leading-relaxed font-mono">
              {error}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Note: Ensure <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">GROQ_API_KEY</code> is configured in your server environment to enable live AI intelligence.
            </p>
          </div>
        ) : !data ? (
          <div className="py-8 text-center text-xs text-slate-400 dark:text-slate-500 space-y-2">
            <Info className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto" />
            <p>Click "Explain with AI" to generate a grounded explanation from verified telemetry.</p>
          </div>
        ) : (
          <div className="space-y-5 animate-fadeIn">
            {/* Heuristic Root Cause Score Banner (for RCA type) */}
            {type === 'rca' && data.primary_root_cause && (
              <div className="p-4 rounded-xl bg-slate-900 text-white border border-indigo-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                    <span className="text-xs uppercase font-mono tracking-wider text-cyan-300 font-bold">
                      Primary Suspect (Heuristic Score)
                    </span>
                  </div>
                  <h4 className="text-lg font-black tracking-tight text-white font-mono">
                    {data.primary_root_cause}
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {data.explanation}
                  </p>
                </div>

                <div className="flex items-center gap-3 shrink-0 self-end sm:self-auto">
                  <div className="text-right">
                    <div className="text-2xl font-black text-cyan-400 font-mono">
                      {data.root_cause_score}%
                    </div>
                    <div className="text-[9px] uppercase font-mono text-slate-400">
                      Heuristic Ranking
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Tripartite Breakdown: Facts vs Hypotheses */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* 1. Confirmed Facts */}
              <div className="p-4 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/10 border border-emerald-200/70 dark:border-emerald-500/20 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5 uppercase tracking-wide">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Confirmed Empirical Facts
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 font-bold">
                    VERIFIED
                  </span>
                </div>
                <ul className="space-y-1.5">
                  {(data.confirmed_facts || []).map((fact, idx) => (
                    <li key={idx} className="text-xs text-slate-700 dark:text-slate-300 flex items-start gap-2 leading-relaxed">
                      <span className="text-emerald-600 dark:text-emerald-400 font-bold mt-0.5">•</span>
                      <span>{fact}</span>
                    </li>
                  ))}
                  {(!data.confirmed_facts || data.confirmed_facts.length === 0) && (
                    <li className="text-xs text-slate-400 italic">No explicit empirical breaches isolated.</li>
                  )}
                </ul>
              </div>

              {/* 2. Causal Hypotheses */}
              <div className="p-4 rounded-xl bg-amber-50/50 dark:bg-amber-950/10 border border-amber-200/70 dark:border-amber-500/20 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-800 dark:text-amber-300 flex items-center gap-1.5 uppercase tracking-wide">
                    <Activity className="w-3.5 h-3.5" /> Causal Hypotheses (Uncertain)
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 font-bold">
                    HYPOTHESIS
                  </span>
                </div>
                <ul className="space-y-1.5">
                  {(data.causal_hypotheses || []).map((hypo, idx) => (
                    <li key={idx} className="text-xs text-slate-700 dark:text-slate-300 flex items-start gap-2 leading-relaxed">
                      <span className="text-amber-600 dark:text-amber-400 font-bold mt-0.5">➔</span>
                      <span>{hypo}</span>
                    </li>
                  ))}
                  {(!data.causal_hypotheses || data.causal_hypotheses.length === 0) && (
                    <li className="text-xs text-slate-400 italic">Hypothesis under SRE investigation.</li>
                  )}
                </ul>
              </div>
            </div>

            {/* Alternative Hypotheses Evaluated (if RCA) */}
            {type === 'rca' && data.alternative_hypotheses && data.alternative_hypotheses.length > 0 && (
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Alternative Hypotheses Evaluated & Contrasted
                </span>
                <div className="space-y-1">
                  {data.alternative_hypotheses.map((alt, idx) => (
                    <div key={idx} className="text-xs text-slate-600 dark:text-slate-400 font-mono">
                      {alt}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Supporting Telemetry Evidence */}
            {data.supporting_evidence && data.supporting_evidence.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-indigo-500" /> Grounded Observability Evidence
                </span>
                <div className="flex flex-wrap gap-2">
                  {data.supporting_evidence.map((ev, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg text-xs font-mono bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 shadow-2xs"
                    >
                      {ev}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested Investigation Steps */}
            {(data.investigation_suggestions || data.investigation_steps) && (
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-cyan-500" /> SRE Diagnostic Next Steps (Read-Only)
                </span>
                <div className="space-y-1.5">
                  {(data.investigation_suggestions || data.investigation_steps).map((step, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/70 border border-slate-200/80 dark:border-slate-800 font-mono text-xs text-slate-800 dark:text-slate-200"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="w-4 h-4 rounded-full bg-cyan-100 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-400 text-[10px] font-bold flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        <span className="truncate">{step}</span>
                      </div>
                      <button
                        onClick={() => handleCopy(step, idx)}
                        className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition shrink-0 ml-2"
                        title="Copy diagnostic query"
                      >
                        {copiedIndex === idx ? (
                          <Check className="w-3.5 h-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Expandable Full Raw Narrative */}
            {data.raw_narrative && (
              <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800/60">
                <button
                  onClick={() => setShowRawNarrative(!showRawNarrative)}
                  className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                >
                  {showRawNarrative ? (
                    <>Hide Full Narrative <ChevronUp className="w-3 h-3" /></>
                  ) : (
                    <>View Full AI Narrative & Context <ChevronDown className="w-3 h-3" /></>
                  )}
                </button>
                {showRawNarrative && (
                  <div className="mt-3 p-4 rounded-xl bg-slate-100 dark:bg-slate-950 text-xs font-mono text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed border border-slate-200 dark:border-slate-800 max-h-80 overflow-y-auto">
                    {data.raw_narrative}
                  </div>
                )}
              </div>
            )}

            {/* Disclaimer Footer */}
            <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between text-[11px] text-slate-400 dark:text-slate-500 gap-1 font-sans">
              <span className="flex items-center gap-1">
                <Info className="w-3 h-3" />
                {data.disclaimer || "Heuristic scoring and advisory recommendations require human engineer validation."}
              </span>
              {data.latency_ms && (
                <span className="font-mono text-[10px]">
                  Latency: {data.latency_ms.toFixed(0)}ms
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
