// frontend/src/components/StatCard.jsx
import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'cyan', badge, trend }) {
  const colorMap = {
    cyan: 'bg-cyan-50 text-cyan-700 border-cyan-200/90 dark:bg-cyan-950/50 dark:text-cyan-300 dark:border-cyan-500/30',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200/90 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-500/30',
    amber: 'bg-amber-50 text-amber-700 border-amber-200/90 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-500/30',
    rose: 'bg-rose-50 text-rose-700 border-rose-200/90 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-500/30',
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-200/90 dark:bg-indigo-950/50 dark:text-indigo-300 dark:border-indigo-500/30',
  };

  const activeColor = colorMap[color] || colorMap.cyan;

  return (
    <div className="glass-card rounded-2xl p-5 relative overflow-hidden group">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1.5 flex-1 min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {title}
          </p>
          <div className="flex items-baseline gap-2 flex-wrap">
            <h3 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {value}
            </h3>
            {badge && (
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700">
                {badge}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-slate-500 dark:text-slate-400 truncate leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>

        {Icon && (
          <div className={`p-3 rounded-xl border shadow-sm transition-transform duration-200 group-hover:scale-110 shrink-0 ${activeColor}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {/* Subtle bottom border gradient accent */}
      <div className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
    </div>
  );
}
