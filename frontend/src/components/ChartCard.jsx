// frontend/src/components/ChartCard.jsx
import React from 'react';

export default function ChartCard({ title, subtitle, children, actions, badge }) {
  return (
    <div className="glass-card rounded-2xl p-5 sm:p-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 dark:border-white/5 pb-3.5">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white tracking-tight">
              {title}
            </h3>
            {badge && (
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200 dark:bg-cyan-950/60 dark:text-cyan-400 dark:border-cyan-500/20">
                {badge}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {subtitle}
            </p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
      </div>
      <div className="w-full">
        {children}
      </div>
    </div>
  );
}
