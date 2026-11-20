// frontend/src/components/Sidebar.jsx
import React, { useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutContext } from '../App';
import { 
  LayoutDashboard, 
  Server, 
  Activity, 
  ShieldAlert, 
  AlertTriangle, 
  Cpu, 
  EyeOff, 
  Sparkles, 
  Settings,
  ShieldCheck,
  X,
  Lock,
  ArrowUpRight,
  GitCommit,
  Brain,
  Compass,
  TrendingUp,
  Blocks
} from 'lucide-react';

export default function Sidebar({ mobileOpen, onCloseMobile }) {
  const layoutCtx = useContext(LayoutContext);
  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/infrastructure', label: 'Infrastructure', icon: Server },
    { to: '/applications', label: 'Applications & Tracing', icon: GitCommit, badge: 'OTel' },
    { to: '/ml-insights', label: 'AI/ML Insights', icon: Brain, badge: 'ML' },
    { to: '/network', label: 'Network Observability', icon: Activity },
    { to: '/security', label: 'Security Events', icon: ShieldAlert },
    { to: '/alerts', label: 'Alerts & Incidents', icon: AlertTriangle },
    { to: '/rca', label: 'Root Cause (RCA)', icon: Compass, badge: 'AIOps' },
    { to: '/predictive', label: 'Predictive & SLOs', icon: TrendingUp, badge: 'Forecast' },
    { to: '/integrations', label: 'Integrations Hub', icon: Blocks, badge: 'Real' },
    { to: '/collectors', label: 'Collector Health', icon: Cpu },
    { 
      to: '/privacy-egress', 
      label: 'Privacy & Access', 
      icon: EyeOff, 
      highlight: true,
      badge: 'Core USP' 
    },
    { to: '/recommendations', label: 'Recommendations', icon: Sparkles },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  const sidebarContent = (
    <div className="h-full flex flex-col justify-between p-2.5 overflow-hidden">
      {/* Navigation Group */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Mobile Header with close button */}
        <div className="flex md:hidden items-center justify-between pb-2 mb-2 border-b border-slate-200 dark:border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-white">
              <ShieldCheck className="w-3.5 h-3.5" />
            </div>
            <span className="font-extrabold text-xs text-slate-900 dark:text-white">ObserveVault</span>
          </div>
          <button
            onClick={onCloseMobile}
            className="p-1 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            aria-label="Close menu"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* AI Copilot Nav Trigger - High Visibility */}
        <div className="shrink-0 mb-1.5">
          <button
            onClick={() => {
              layoutCtx?.setCopilotOpen(true);
              onCloseMobile?.();
            }}
            className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-semibold text-white bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-sm shadow-indigo-500/20 transition-all hover:scale-[1.01] active:scale-[0.99] group"
          >
            <div className="flex items-center gap-2.5">
              <Sparkles className="w-3.5 h-3.5 fill-current text-indigo-200 transition-transform group-hover:rotate-12" />
              <span>AI SRE Copilot</span>
            </div>
            <span className="text-[8px] font-mono uppercase bg-white/20 px-1.5 py-0.5 rounded-full font-bold">
              Live
            </span>
          </button>
        </div>

        {/* Scrollable Navigation List */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-0.5">
          <p className="px-2 pt-1 pb-1 text-[9px] uppercase font-bold text-slate-400 dark:text-slate-500 tracking-wider">
            Monitoring & Controls
          </p>
          <nav className="space-y-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={onCloseMobile}
                  className={({ isActive }) => `
                    flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 group
                    ${isActive 
                      ? 'bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 text-white font-semibold shadow-sm shadow-blue-500/20' 
                      : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-900/60'}
                  `}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Icon className="w-3.5 h-3.5 transition-transform group-hover:scale-110 shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[8px] uppercase font-mono px-1.5 py-0.2 rounded bg-cyan-100 dark:bg-cyan-950/80 text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-500/40 font-bold tracking-tight shrink-0 ml-1">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Compact Privacy & Security Status Badge */}
      <div className="pt-2 mt-1 border-t border-slate-200/70 dark:border-white/5 shrink-0">
        <NavLink
          to="/privacy-egress"
          onClick={onCloseMobile}
          className="flex items-center justify-between p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 hover:bg-slate-100 dark:hover:bg-slate-800/80 border border-slate-200/60 dark:border-white/5 transition-all group shadow-xs"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="p-1 rounded-md bg-indigo-600 text-white shadow-xs shrink-0">
              <ShieldCheck className="w-3.5 h-3.5" />
            </span>
            <div className="min-w-0">
              <div className="text-[10px] font-bold text-slate-900 dark:text-white leading-tight truncate">Privacy Engine</div>
              <div className="text-[8px] text-slate-500 dark:text-slate-400 truncate">Zero-Egress Active</div>
            </div>
          </div>
          <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 font-bold shrink-0 ml-1">
            ACTIVE
          </span>
        </NavLink>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="w-60 border-r border-slate-200/80 dark:border-white/5 glass-panel h-full hidden md:flex flex-col shrink-0 overflow-hidden">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop & Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div 
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity" 
            onClick={onCloseMobile} 
          />
          <div className="relative w-64 max-w-[80vw] h-full bg-white dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 shadow-2xl z-10 flex flex-col overflow-hidden animate-fadeIn">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
