// frontend/src/components/SimulatorControlModal.jsx
import React, { useState } from 'react';
import { api } from '../services/api';
import { 
  Play, 
  Cpu, 
  WifiOff, 
  ShieldAlert, 
  AlertOctagon, 
  Radio, 
  CheckCircle2, 
  X,
  Server,
  Zap,
  Activity
} from 'lucide-react';

export default function SimulatorControlModal({ isOpen, onClose, onScenarioTriggered }) {
  const [loading, setLoading] = useState(false);
  const [resultMsg, setResultMsg] = useState(null);
  const [targetServer, setTargetServer] = useState('prod-api-gateway');

  if (!isOpen) return null;

  const scenarios = [
    {
      id: 'normal',
      name: 'Normal Operations',
      desc: 'Balanced CPU, standard memory footprint, nominal sub-35ms latency.',
      icon: CheckCircle2,
      lightColor: 'text-emerald-700 bg-emerald-50 border-emerald-200',
      darkColor: 'dark:text-emerald-400 dark:bg-emerald-950/40 dark:border-emerald-500/20',
      badge: 'Baseline'
    },
    {
      id: 'high_cpu',
      name: 'High CPU Resource Spike',
      desc: 'Spikes CPU to 96.8% and triggers high-latency cascading breach.',
      icon: Cpu,
      lightColor: 'text-amber-700 bg-amber-50 border-amber-200',
      darkColor: 'dark:text-amber-400 dark:bg-amber-950/40 dark:border-amber-500/20',
      badge: 'Anomaly Demo'
    },
    {
      id: 'network_failure',
      name: 'Network Route Congestion',
      desc: 'Injects 380ms latency and 18.5% packet loss on interface.',
      icon: WifiOff,
      lightColor: 'text-rose-700 bg-rose-50 border-rose-200',
      darkColor: 'dark:text-rose-400 dark:bg-rose-950/40 dark:border-rose-500/20',
      badge: 'Network Alert'
    },
    {
      id: 'security_spike',
      name: 'Credential Spraying Attack',
      desc: 'Simulates 12 failed logins with local credentials stripping and count audit.',
      icon: ShieldAlert,
      lightColor: 'text-purple-700 bg-purple-50 border-purple-200',
      darkColor: 'dark:text-purple-400 dark:bg-purple-950/40 dark:border-purple-500/20',
      badge: 'Privacy Proof'
    },
    {
      id: 'service_crash',
      name: 'Critical Service Crash',
      desc: 'Sets service status to DOWN, triggers critical incident and recovery plan.',
      icon: AlertOctagon,
      lightColor: 'text-rose-800 bg-rose-100 border-rose-300',
      darkColor: 'dark:text-rose-400 dark:bg-rose-950/60 dark:border-rose-500/40',
      badge: 'Severity Critical'
    },
    {
      id: 'collector_offline',
      name: 'Collector Heartbeat Timeout',
      desc: 'Suppresses collector heartbeat to trigger offline detection within 60s.',
      icon: Radio,
      lightColor: 'text-slate-700 bg-slate-100 border-slate-200',
      darkColor: 'dark:text-slate-400 dark:bg-slate-900 dark:border-slate-700',
      badge: 'Health Check'
    }
  ];

  const handleTrigger = async (scenarioId) => {
    setLoading(true);
    setResultMsg(null);
    try {
      const res = await api.triggerScenario(scenarioId, targetServer);
      setResultMsg({
        type: 'success',
        text: res.message || `Scenario '${scenarioId}' triggered successfully.`
      });
      if (onScenarioTriggered) {
        onScenarioTriggered(scenarioId);
      }
    } catch (err) {
      setResultMsg({
        type: 'error',
        text: err.message || 'Failed to trigger scenario'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-2xl p-6 border border-slate-200 dark:border-white/10 shadow-2xl space-y-6 relative max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between border-b border-slate-100 dark:border-white/5 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-100 text-cyan-800 dark:bg-cyan-950/60 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-500/30">
              <Zap className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                Scenario Demonstration Controller
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-400 font-bold">
                  Live Test Harness
                </span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Trigger live infrastructure anomalies and watch ObserveVault's detection and privacy correlation pipeline in action.
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Server Target Selector */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
            Target Server for Simulation
          </label>
          <select 
            value={targetServer}
            onChange={(e) => setTargetServer(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs font-medium text-slate-900 dark:text-slate-200 focus:outline-none focus:border-cyan-500 shadow-xs"
          >
            <option value="prod-api-gateway">prod-api-gateway (Production Ingress)</option>
            <option value="prod-payment-svc">prod-payment-svc (Financial Core)</option>
            <option value="prod-database-primary">prod-database-primary (Database Node)</option>
            <option value="prod-auth-cluster">prod-auth-cluster (Identity Service)</option>
          </select>
        </div>

        {/* Scenario Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {scenarios.map((sc) => {
            const Icon = sc.icon;
            return (
              <button
                key={sc.id}
                disabled={loading}
                onClick={() => handleTrigger(sc.id)}
                className="text-left p-4 rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50/50 hover:bg-white dark:bg-slate-800/40 dark:hover:bg-slate-800/80 hover:border-cyan-500/40 transition-all duration-150 group space-y-2 relative disabled:opacity-50 shadow-xs hover:shadow-soft-sm"
              >
                <div className="flex items-center justify-between">
                  <div className={`p-2 rounded-lg border ${sc.lightColor} ${sc.darkColor}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 font-bold">
                    {sc.badge}
                  </span>
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-cyan-600 dark:group-hover:text-cyan-300 transition">
                    {sc.name}
                  </h4>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
                    {sc.desc}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        {/* Result Feedback Banner */}
        {resultMsg && (
          <div className={`p-3 rounded-xl text-xs border ${
            resultMsg.type === 'success' 
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-500/30' 
              : 'bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-500/30'
          }`}>
            {resultMsg.text}
          </div>
        )}

        <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-white/5 text-[11px] text-slate-500 dark:text-slate-400">
          <span>* Telemetry is processed via Tier-1 Privacy Sanitiser and tagged as simulated.</span>
          <button 
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition font-bold text-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
