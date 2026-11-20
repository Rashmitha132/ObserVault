// frontend/src/components/PrivacyFlowGraphic.jsx
import React from 'react';
import { 
  ShieldCheck, 
  Lock, 
  FileCheck, 
  ArrowRight, 
  Cloud, 
  Server, 
  EyeOff,
  Database
} from 'lucide-react';

export default function PrivacyFlowGraphic() {
  const steps = [
    {
      step: '01',
      title: 'Local Infrastructure',
      subtitle: 'Raw Metrics & Traces',
      icon: Server,
      lightColor: 'border-slate-200 bg-slate-50/80 text-slate-700',
      darkColor: 'dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300',
      badge: 'On-Prem'
    },
    {
      step: '02',
      title: 'Edge Privacy Engine',
      subtitle: 'Credential Purging',
      icon: EyeOff,
      lightColor: 'border-purple-200 bg-purple-50/80 text-purple-700',
      darkColor: 'dark:border-purple-500/30 dark:bg-purple-950/40 dark:text-purple-300',
      badge: 'Scrub Secrets'
    },
    {
      step: '03',
      title: 'Explicit Allow-List',
      subtitle: 'Strict Field Validation',
      icon: FileCheck,
      lightColor: 'border-cyan-200 bg-cyan-50/80 text-cyan-700',
      darkColor: 'dark:border-cyan-500/30 dark:bg-cyan-950/40 dark:text-cyan-300',
      badge: 'Drop Unknown'
    },
    {
      step: '04',
      title: 'SQLite Local Buffer',
      subtitle: 'Offline Resilience',
      icon: Database,
      lightColor: 'border-amber-200 bg-amber-50/80 text-amber-700',
      darkColor: 'dark:border-amber-500/30 dark:bg-amber-950/40 dark:text-amber-300',
      badge: 'Zero Drop'
    },
    {
      step: '05',
      title: 'Authenticated TLS',
      subtitle: 'HMAC Header Egress',
      icon: Lock,
      lightColor: 'border-emerald-200 bg-emerald-50/80 text-emerald-700',
      darkColor: 'dark:border-emerald-500/30 dark:bg-emerald-950/40 dark:text-emerald-300',
      badge: 'Encrypted'
    },
    {
      step: '06',
      title: 'SaaS Cloud Hub',
      subtitle: 'AI Incident Correlation',
      icon: Cloud,
      lightColor: 'border-blue-200 bg-blue-50/80 text-blue-700',
      darkColor: 'dark:border-indigo-500/30 dark:bg-indigo-950/40 dark:text-indigo-300',
      badge: 'Cloud Intelligence'
    }
  ];

  return (
    <div className="glass-card rounded-2xl p-5 sm:p-6 relative overflow-hidden">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-cyan-100 text-cyan-800 dark:bg-cyan-950/80 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-500/30 shadow-sm">
              <ShieldCheck className="w-4 h-4" />
            </span>
            <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white tracking-tight">
              Two-Tier Privacy-Preserving Architecture Flow
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Zero raw logs, credentials, or tokens cross the corporate perimeter. Telemetry is verified locally before egress.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-emerald-100 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-400 dark:border-emerald-500/30 font-semibold shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400 animate-pulse" />
            Tier-1 Perimeter Active
          </span>
        </div>
      </div>

      {/* Visual Pipeline Steps */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 relative">
        {steps.map((s, idx) => {
          const Icon = s.icon;
          return (
            <div 
              key={s.step} 
              className={`p-4 rounded-xl border ${s.lightColor} ${s.darkColor} relative flex flex-col justify-between group hover:scale-[1.03] transition-all duration-150 shadow-sm`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono font-bold text-slate-400 dark:text-slate-500">
                    {s.step}
                  </span>
                  <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-white/70 dark:bg-black/40 border border-black/5 dark:border-white/5 text-slate-600 dark:text-slate-400 font-bold">
                    {s.badge}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-white/60 dark:bg-black/20 w-fit mb-2.5 shadow-xs">
                  <Icon className="w-4 h-4" />
                </div>
                <h4 className="text-xs font-bold text-slate-900 dark:text-white leading-tight">{s.title}</h4>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-snug">{s.subtitle}</p>
              </div>

              {idx < steps.length - 1 && (
                <div className="hidden lg:block absolute -right-2.5 top-1/2 -translate-y-1/2 z-10 text-cyan-600 dark:text-cyan-400/60">
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Assurance Legend Bar */}
      <div className="mt-6 pt-4 border-t border-slate-100 dark:border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
        <div className="flex flex-wrap items-center gap-4">
          <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300 font-medium">
            <span className="w-2 h-2 rounded-full bg-cyan-500" />
            Approved Outbound: 16 strict numerical & categorical fields
          </span>
          <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300 font-medium">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            Dropped Locally: Passwords, tokens, API keys, cookies, usernames
          </span>
        </div>
        <span className="font-mono text-[11px] text-cyan-600 dark:text-cyan-400 font-bold">
          TLS 1.3 / Key-Authenticated Ingestion
        </span>
      </div>
    </div>
  );
}
