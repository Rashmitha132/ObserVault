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
    <div className="h-full flex flex-col justify-between p-4 space-y-6">
      {/* Navigation Group */}
      <div className="space-y-4">
        {/* Mobile Header with close button */}
        <div className="flex md:hidden items-center justify-between pb-3 border-b border-slate-200 dark:border-white/10">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-white">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <span className="font-extrabold text-sm text-slate-900 dark:text-white">ObserveVault</span>
          </div>
          <button
            onClick={onCloseMobile}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div>
          <p className="px-3 text-[10px] uppercase font-bold text-slate-400 dark:text-slate-500 tracking-wider">
            Monitoring & Telemetry
          </p>
          <nav className="mt-2 space-y-1">
            {/* AI Copilot Nav Trigger */}
            <button
              onClick={() => {
                layoutCtx?.setCopilotOpen(true);
                onCloseMobile?.();
              }}
              className="w-full flex items-center justify-between px-3 py-2.5 mb-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-md shadow-indigo-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] group"
            >
              <div className="flex items-center gap-3">
                <Sparkles className="w-4 h-4 fill-current text-indigo-200 transition-transform group-hover:rotate-12" />
                <span>AI SRE Copilot</span>
              </div>
              <span className="text-[9px] font-mono uppercase bg-white/20 px-1.5 py-0.5 rounded-full font-bold">
                Live
              </span>
            </button>
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={onCloseMobile}
                  className={({ isActive }) => `
                    flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 group
                    ${isActive 
                      ? 'bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 text-white shadow-md shadow-blue-500/25' 
                      : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-900/60'}
                  `}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4 transition-transform group-hover:scale-110 shrink-0" />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950/80 text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-500/40 font-bold tracking-tight">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Bottom AI-Powered Observability Card */}
      <div className="p-4 rounded-2xl bg-gradient-to-br from-indigo-50 via-blue-50 to-cyan-50 dark:from-slate-900 dark:via-slate-950 dark:to-cyan-950/40 border border-indigo-100 dark:border-cyan-500/20 shadow-soft-sm space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-indigo-600 text-white shadow-sm">
              <ShieldCheck className="w-3.5 h-3.5" />
            </span>
            <span className="text-xs font-bold text-slate-900 dark:text-white">Privacy Engine</span>
          </div>
          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 font-bold">
            ACTIVE
          </span>
        </div>
        <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
          Zero raw credentials or tokens leave your network. Telemetry is verified at the edge.
        </p>
        <div className="pt-1 flex items-center justify-between text-[11px] font-semibold text-indigo-700 dark:text-cyan-400 hover:underline">
          <span>View Egress Proof</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="w-64 border-r border-slate-200/80 dark:border-white/5 glass-panel min-h-[calc(100vh-4rem)] hidden md:block shrink-0">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop & Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div 
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity" 
            onClick={onCloseMobile} 
          />
          <div className="relative w-72 max-w-[80vw] bg-white dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 shadow-2xl z-10 animate-fadeIn">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
