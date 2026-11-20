// frontend/src/components/Navbar.jsx
import React, { useState, useContext, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { LayoutContext } from '../App';
import { 
  Shield, 
  Zap, 
  LogOut, 
  Building2, 
  RefreshCw, 
  Sun, 
  Moon, 
  Search, 
  Bell, 
  Clock, 
  Menu, 
  X,
  ChevronDown,
  Check,
  AlertTriangle,
  Activity,
  Sparkles,
  Brain
} from 'lucide-react';
import SimulatorControlModal from './SimulatorControlModal';

export default function Navbar({ onRefresh, onToggleMobileSidebar }) {
  const { user, login, logout } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  const layoutCtx = useContext(LayoutContext);

  const [showSimModal, setShowSimModal] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showTimeRange, setShowTimeRange] = useState(false);

  const notifRef = useRef(null);
  const timeRef = useRef(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotifications(false);
      }
      if (timeRef.current && !timeRef.current.contains(e.target)) {
        setShowTimeRange(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSwitchTenant = async () => {
    setIsSwitching(true);
    try {
      const isAcme = user?.email?.toLowerCase().includes('acme') || user?.tenantName?.toLowerCase().includes('acme');
      if (isAcme) {
        await login('admin@biohealth.com', 'Password123!');
      } else {
        await login('admin@acme.com', 'Password123!');
      }
      if (onRefresh) onRefresh();
      window.location.reload();
    } catch (err) {
      console.error('Failed to switch demo tenant', err);
    } finally {
      setIsSwitching(false);
    }
  };

  const timeRanges = ['Last 15m', 'Last 1h', 'Last 6h', 'Last 24h', 'Last 7d'];

  return (
    <>
      <header className="h-16 shrink-0 border-b border-slate-200/80 dark:border-white/5 glass-panel sticky top-0 z-40 px-4 sm:px-6 flex items-center justify-between gap-3">
        {/* Left: Mobile Menu + Brand Logo */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleMobileSidebar}
            className="md:hidden p-2 rounded-xl text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            aria-label="Toggle navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center shadow-md shadow-cyan-500/20 text-white shrink-0">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div className="hidden sm:block">
              <div className="flex items-center gap-1.5 leading-none">
                <span className="font-extrabold text-slate-900 dark:text-white text-base tracking-tight">
                  ObserveVault
                </span>
                <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-100 text-cyan-800 border border-cyan-200 dark:bg-cyan-950 dark:text-cyan-400 dark:border-cyan-500/30">
                  ENTERPRISE
                </span>
              </div>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium tracking-tight mt-0.5">
                Observe · Analyze · Optimize
              </p>
            </div>
          </div>
        </div>

        {/* Center: Global Search Bar */}
        <div className="hidden md:flex items-center flex-1 max-w-xs lg:max-w-sm mx-2">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search servers, metrics, alerts..."
              value={layoutCtx?.searchQuery || ''}
              onChange={(e) => layoutCtx?.setSearchQuery(e.target.value)}
              className="w-full bg-slate-100 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 rounded-xl pl-9 pr-9 py-1.5 text-xs text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/20 transition shadow-inner"
            />
            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-[9px] font-mono text-slate-400 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 shadow-sm pointer-events-none">
              ⌘K
            </kbd>
          </div>
        </div>

        {/* Right Actions: Tenant, Time Range, Anomaly Sim, Notifs, Theme, Profile */}
        <div className="flex items-center gap-2 sm:gap-2.5">
          {/* Tenant Switcher Button */}
          <button
            onClick={handleSwitchTenant}
            disabled={isSwitching}
            title="Click to toggle demo organizations (Acme FinTech vs BioHealth Global)"
            className="hidden lg:flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-cyan-500/40 text-xs text-slate-700 dark:text-slate-200 transition group shadow-sm"
          >
            <Building2 className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 group-hover:scale-110 transition" />
            <span className="font-semibold truncate max-w-[120px]">
              {user?.tenantName || 'Acme FinTech'}
            </span>
            <span className="text-[9px] px-1 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono">
              Switch
            </span>
          </button>

          {/* Time Range Selector */}
          <div className="relative" ref={timeRef}>
            <button
              onClick={() => setShowTimeRange(!showTimeRange)}
              className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-xs text-slate-700 dark:text-slate-300 transition shadow-sm"
            >
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-medium">{layoutCtx?.timeRange || 'Last 15m'}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {showTimeRange && (
              <div className="absolute right-0 mt-1.5 w-32 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl py-1 z-50 animate-fadeIn">
                {timeRanges.map((tr) => (
                  <button
                    key={tr}
                    onClick={() => {
                      layoutCtx?.setTimeRange(tr);
                      setShowTimeRange(false);
                    }}
                    className={`w-full text-left px-3 py-1.5 text-xs flex items-center justify-between hover:bg-slate-100 dark:hover:bg-slate-800 transition ${
                      layoutCtx?.timeRange === tr
                        ? 'text-cyan-600 dark:text-cyan-400 font-bold'
                        : 'text-slate-600 dark:text-slate-300'
                    }`}
                  >
                    <span>{tr}</span>
                    {layoutCtx?.timeRange === tr && <Check className="w-3 h-3" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* AI Copilot Button */}
          <button
            onClick={() => layoutCtx?.setCopilotOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs shadow-md shadow-indigo-500/20 transition-all hover:scale-105 active:scale-95 shrink-0"
            title="Open AI Observability Copilot"
          >
            <Sparkles className="w-3.5 h-3.5 fill-current" />
            <span className="hidden sm:inline">AI Copilot</span>
          </button>

          {/* Simulate Anomaly Button */}
          <button
            onClick={() => setShowSimModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs shadow-md shadow-cyan-500/20 transition-all hover:scale-105 active:scale-95 shrink-0"
          >
            <Zap className="w-3.5 h-3.5 fill-current" />
            <span className="hidden sm:inline">Simulate Anomaly</span>
          </button>

          {/* Notifications Dropdown */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="p-2 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition relative shadow-sm"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 text-white text-[9px] font-bold flex items-center justify-center animate-pulse">
                2
              </span>
            </button>

            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-4 z-50 animate-fadeIn space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/5 pb-2.5">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white">Active Alerts & Notifications</h4>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 font-bold">
                    2 Unresolved
                  </span>
                </div>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  <div className="p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200/80 dark:border-amber-500/20 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-amber-800 dark:text-amber-300 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" /> High CPU Utilisation
                      </span>
                      <span className="text-[10px] text-slate-500">2m ago</span>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-300">
                      prod-api-gateway CPU reached 94.2% (Threshold: 90.0%).
                    </p>
                  </div>

                  <div className="p-2.5 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200/80 dark:border-purple-500/20 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-purple-800 dark:text-purple-300 flex items-center gap-1">
                        <Activity className="w-3.5 h-3.5" /> Authentication Anomaly
                      </span>
                      <span className="text-[10px] text-slate-500">6m ago</span>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-300">
                      7 failed login attempts recorded. Local credentials sanitized; only counts egressed.
                    </p>
                  </div>
                </div>
                <div className="pt-2 border-t border-slate-100 dark:border-white/5 text-center">
                  <span className="text-[11px] text-cyan-600 dark:text-cyan-400 font-semibold cursor-pointer hover:underline">
                    View All in Alerts & Incidents →
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Theme Toggle (Sun / Moon) */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-cyan-600 dark:hover:text-cyan-400 transition shadow-sm"
            title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
            aria-label="Toggle visual theme"
          >
            {isDark ? (
              <Sun className="w-4 h-4 text-amber-400 hover:rotate-45 transition-transform" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-600 hover:-rotate-12 transition-transform" />
            )}
          </button>

          {/* Refresh Data */}
          {onRefresh && (
            <button
              onClick={onRefresh}
              title="Refresh Live Telemetry"
              className="p-2 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}

          {/* User Profile & Logout */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-200 dark:border-white/10">
            <div className="text-right hidden xl:block">
              <p className="text-xs font-bold text-slate-900 dark:text-slate-200 leading-none">
                {user?.fullName || 'Sarah Jenkins'}
              </p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 capitalize mt-0.5 font-medium">
                {user?.role || 'admin'} • {user?.email || 'admin@acme.com'}
              </p>
            </div>
            <button
              onClick={logout}
              title="Sign Out"
              className="p-2 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-rose-300 dark:hover:border-rose-500/40 text-slate-500 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-400 transition shadow-sm"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Anomaly Simulator Modal */}
      <SimulatorControlModal 
        isOpen={showSimModal} 
        onClose={() => setShowSimModal(false)}
        onScenarioTriggered={() => {
          if (onRefresh) onRefresh();
        }}
      />
    </>
  );
}
