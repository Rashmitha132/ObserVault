// frontend/src/components/StatusBadge.jsx
import React from 'react';

export default function StatusBadge({ status, size = 'sm' }) {
  const norm = (status || '').toLowerCase();
  
  let styles = 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/80 dark:text-slate-400 dark:border-slate-700';
  let dotColor = 'bg-slate-400 dark:bg-slate-500';

  if (['healthy', 'optimal', 'online', 'delivered', 'completed', 'resolved', 'up'].includes(norm)) {
    styles = 'bg-emerald-50 text-emerald-800 border-emerald-200/80 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-500/30';
    dotColor = 'bg-emerald-500 dark:bg-emerald-400';
  } else if (['warning', 'medium', 'investigating', 'acknowledged', 'degraded'].includes(norm)) {
    styles = 'bg-amber-50 text-amber-800 border-amber-200/80 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-500/30';
    dotColor = 'bg-amber-500 dark:bg-amber-400 animate-pulse';
  } else if (['critical', 'danger', 'failed', 'down', 'open', 'high'].includes(norm)) {
    styles = 'bg-rose-50 text-rose-800 border-rose-200/80 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-500/30';
    dotColor = 'bg-rose-500 dark:bg-rose-400 animate-ping';
  } else if (['offline', 'disconnected', 'pending'].includes(norm)) {
    styles = 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700';
    dotColor = 'bg-slate-400 dark:bg-slate-500';
  }

  const sizeClass = size === 'xs' 
    ? 'px-2 py-0.5 text-[10px]' 
    : 'px-2.5 py-1 text-xs';

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full border shadow-sm transition-colors duration-150 ${styles} ${sizeClass}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      <span className="capitalize tracking-tight font-semibold">{status}</span>
    </span>
  );
}
