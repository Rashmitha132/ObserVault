// frontend/src/pages/CollectorManagementPage.jsx
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import { 
  Cpu, 
  Radio, 
  Database, 
  RefreshCw, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  HardDrive,
  Activity,
  Terminal,
  ShieldCheck,
  Plus,
  Copy,
  Check,
  Trash2,
  Monitor,
  Server,
  Info,
  X,
  ChevronRight,
  AlertTriangle,
  KeyRound,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';

export default function CollectorManagementPage() {
  const [collectors, setCollectors] = useState([]);
  const [stats, setStats] = useState({
    total_devices: 0,
    online_devices: 0,
    offline_devices: 0,
    pending_devices: 0,
    revoked_devices: 0
  });
  const [loading, setLoading] = useState(true);

  // Onboarding Wizard state
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(1); // 1: Register, 2: Token & Script, 3: Waiting Room
  const [deviceName, setDeviceName] = useState('');
  const [osType, setOsType] = useState('windows');
  const [environment, setEnvironment] = useState('production');
  const [description, setDescription] = useState('');
  const [registering, setRegistering] = useState(false);
  const [registeredData, setRegisteredData] = useState(null);
  const [copiedToken, setCopiedToken] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState(false);
  const [waitingSuccess, setWaitingSuccess] = useState(null);

  // Device Detail Modal state
  const [selectedCollector, setSelectedCollector] = useState(null);
  const [deviceDetails, setDeviceDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailTab, setDetailTab] = useState('metrics'); // 'metrics' | 'audit'
  const [revoking, setRevoking] = useState(false);
  const [showRevokeConfirm, setShowRevokeConfirm] = useState(false);

  const fetchCollectors = async () => {
    try {
      setLoading(true);
      const [listRes, statsRes] = await Promise.all([
        api.getCollectors(),
        api.getCollectorStats().catch(() => null)
      ]);
      setCollectors(listRes || []);
      if (statsRes) {
        setStats(statsRes);
      } else {
        const total = listRes.length;
        const online = listRes.filter(c => c.status === 'online').length;
        const offline = listRes.filter(c => c.status === 'offline').length;
        const pending = listRes.filter(c => c.status === 'pending').length;
        const revoked = listRes.filter(c => c.status === 'revoked' || c.is_revoked).length;
        setStats({
          total_devices: total,
          online_devices: online,
          offline_devices: offline,
          pending_devices: pending,
          revoked_devices: revoked
        });
      }
    } catch (err) {
      console.error('Failed to load collectors', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCollectors();
    const interval = setInterval(fetchCollectors, 8000);
    return () => clearInterval(interval);
  }, []);

  // Waiting room polling when on Step 3
  useEffect(() => {
    let waitInterval = null;
    if (wizardOpen && wizardStep === 3 && registeredData) {
      waitInterval = setInterval(async () => {
        try {
          const list = await api.getCollectors();
          const target = list.find(c => c.name === registeredData.device_name && c.status === 'online');
          if (target) {
            setWaitingSuccess(target);
            fetchCollectors();
          }
        } catch (e) {
          console.error(e);
        }
      }, 3000);
    }
    return () => {
      if (waitInterval) clearInterval(waitInterval);
    };
  }, [wizardOpen, wizardStep, registeredData]);

  // Handle Device Registration (Step 1 -> Step 2)
  const handleRegisterDevice = async (e) => {
    e.preventDefault();
    if (!deviceName.trim()) return;

    try {
      setRegistering(true);
      const res = await api.registerDevice({
        device_name: deviceName.trim(),
        os_type: osType,
        environment: environment,
        description: description.trim() || undefined
      });
      setRegisteredData(res);
      setWizardStep(2);
      fetchCollectors();
    } catch (err) {
      alert(`Registration error: ${err.message || 'Failed to register device'}`);
    } finally {
      setRegistering(false);
    }
  };

  // Open Device Details Modal
  const handleOpenDetails = async (collector) => {
    setSelectedCollector(collector);
    setShowRevokeConfirm(false);
    setDetailTab('metrics');
    try {
      setLoadingDetails(true);
      const details = await api.getDeviceDetails(collector.id);
      setDeviceDetails(details);
    } catch (err) {
      console.error('Failed to load device details', err);
    } finally {
      setLoadingDetails(false);
    }
  };

  // Handle Revocation
  const handleRevoke = async () => {
    if (!selectedCollector) return;
    try {
      setRevoking(true);
      await api.revokeDevice(selectedCollector.id);
      await fetchCollectors();
      const updatedDetails = await api.getDeviceDetails(selectedCollector.id);
      setDeviceDetails(updatedDetails);
      setShowRevokeConfirm(false);
    } catch (err) {
      alert(`Revocation failed: ${err.message || 'Error revoking device'}`);
    } finally {
      setRevoking(false);
    }
  };

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    if (type === 'token') {
      setCopiedToken(true);
      setTimeout(() => setCopiedToken(false), 2500);
    } else {
      setCopiedCmd(true);
      setTimeout(() => setCopiedCmd(false), 2500);
    }
  };

  const resetWizard = () => {
    setWizardOpen(false);
    setWizardStep(1);
    setDeviceName('');
    setDescription('');
    setRegisteredData(null);
    setWaitingSuccess(null);
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-cyan-50 dark:bg-cyan-950/60 text-cyan-600 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-800/40">
              <Cpu className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Tier-1 Edge Collector Management
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Monitor on-premises collector daemon health, heartbeat signaling, local SQLite buffering, and egress retry queues.
          </p>
        </div>
        
        {/* Action Button Group */}
        <div className="flex items-center gap-3">
          <button 
            onClick={fetchCollectors}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 transition shadow-xs active:scale-[0.98] disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-500' : ''}`} />
            Poll Collectors
          </button>
          
          <button
            onClick={() => {
              resetWizard();
              setWizardOpen(true);
            }}
            id="btn-add-new-device"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold transition shadow-md shadow-cyan-500/25 hover:shadow-cyan-500/40 active:scale-[0.98] ring-2 ring-cyan-500/20"
          >
            <Plus className="w-4 h-4 stroke-[2.5]" />
            + Add New Device
          </button>
        </div>
      </div>

      {/* Collector Architecture Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-5">
        <div className="glass-card rounded-2xl p-5 shadow-soft space-y-2.5">
          <div className="flex items-center gap-2 text-cyan-600 dark:text-cyan-400 text-xs font-bold uppercase tracking-wider">
            <span className="p-1.5 rounded-lg bg-cyan-50 dark:bg-cyan-950/80 border border-cyan-200 dark:border-cyan-500/30">
              <Radio className="w-4 h-4" />
            </span>
            <span>Heartbeat Polling</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            Collectors send an authenticated cryptographic heartbeat every 15 seconds. If no heartbeat is received within 60s, the platform alerts operations automatically.
          </p>
        </div>

        <div className="glass-card rounded-2xl p-5 shadow-soft space-y-2.5">
          <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 text-xs font-bold uppercase tracking-wider">
            <span className="p-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/80 border border-amber-200 dark:border-amber-500/30">
              <Database className="w-4 h-4" />
            </span>
            <span>SQLite Offline Buffer</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            If cloud connectivity drops, approved outbound records are staged in the edge collector's local SQLite database. Once restored, telemetry flushes with zero record loss.
          </p>
        </div>

        <div className="glass-card rounded-2xl p-5 shadow-soft space-y-2.5">
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-xs font-bold uppercase tracking-wider">
            <span className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-200 dark:border-emerald-500/30">
              <ShieldCheck className="w-4 h-4" />
            </span>
            <span>Pre-Egress Sanitization</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            Every record passes through the metadata allow-list BEFORE entering the buffer or transmission queue. Credentials are mathematically excluded from flight.
          </p>
        </div>
      </div>

      {/* KPI Stats Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 sm:gap-4">
        <div className="glass-card rounded-2xl p-4 shadow-soft">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-medium">
            <span>Total Registered</span>
            <Monitor className="w-4 h-4 text-slate-400" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 dark:text-white font-mono">
            {stats.total_devices}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 shadow-soft border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between text-xs text-emerald-600 dark:text-emerald-400 font-medium">
            <span>Online Active</span>
            <Radio className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-emerald-600 dark:text-emerald-400 font-mono">
            {stats.online_devices}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 shadow-soft border-l-4 border-l-slate-400">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-medium">
            <span>Offline Devices</span>
            <Clock className="w-4 h-4 text-slate-400" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-700 dark:text-slate-300 font-mono">
            {stats.offline_devices}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 shadow-soft border-l-4 border-l-amber-500">
          <div className="flex items-center justify-between text-xs text-amber-600 dark:text-amber-400 font-medium">
            <span>Pending Handshake</span>
            <KeyRound className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-amber-600 dark:text-amber-400 font-mono">
            {stats.pending_devices}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-4 shadow-soft border-l-4 border-l-rose-500 col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-xs text-rose-600 dark:text-rose-400 font-medium">
            <span>Revoked</span>
            <ShieldAlert className="w-4 h-4 text-rose-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-rose-600 dark:text-rose-400 font-mono">
            {stats.revoked_devices}
          </div>
        </div>
      </div>

      {/* Collectors List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Registered Edge Collectors</h3>
          <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            {collectors.length} Deployed
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {collectors.length === 0 ? (
            <div className="glass-card rounded-2xl p-10 text-center text-slate-400 shadow-soft">
              <AlertCircle className="w-8 h-8 text-slate-400 mx-auto mb-2 opacity-60" />
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
                No collectors currently registered for this tenant. Click "+ Add New Device" above to onboard your first machine.
              </p>
            </div>
          ) : (
            collectors.map((c) => {
              const isRevoked = c.status === 'revoked' || c.is_revoked;
              const isPending = c.status === 'pending';
              const isOnline = c.status === 'online';

              return (
                <div 
                  key={c.id} 
                  className={`glass-card rounded-2xl p-6 shadow-soft transition-all duration-200 space-y-5 ${
                    isRevoked 
                      ? 'opacity-70 bg-rose-950/5 border-rose-200/50 dark:border-rose-900/40' 
                      : 'hover:border-cyan-400/50 dark:hover:border-cyan-500/40'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800/80 pb-4">
                    <div className="flex items-center gap-3.5">
                      <div className={`p-3 rounded-2xl border ${
                        isOnline 
                          ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30' 
                          : isPending
                          ? 'bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-500/30 animate-pulse'
                          : isRevoked
                          ? 'bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-500/30'
                          : 'bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-500/30'
                      }`}>
                        {c.os_type === 'linux' ? <Server className="w-6 h-6" /> : <Cpu className="w-6 h-6" />}
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="text-base font-bold text-slate-900 dark:text-white">{c.name}</h4>
                          <StatusBadge status={c.status} />
                          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-cyan-50 dark:bg-cyan-950/60 text-cyan-600 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-800/40">
                            {c.os_type || 'Windows'}
                          </span>
                          <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                            v{c.version}
                          </span>
                        </div>
                        <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
                          ID: <span className="text-slate-700 dark:text-slate-300">{c.id}</span> • Host: <span className="text-slate-700 dark:text-slate-300">{c.hostname}</span> • IP: <span className="text-slate-700 dark:text-slate-300">{c.ip_address || 'Unassigned'}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start sm:self-auto">
                      <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 font-mono bg-slate-50 dark:bg-slate-950/50 px-3 py-1.5 rounded-xl border border-slate-200/80 dark:border-slate-800/80 w-fit">
                        <Clock className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                        <span>Interval: {c.collection_interval}s</span>
                      </div>
                      
                      <button
                        onClick={() => handleOpenDetails(c)}
                        className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 transition"
                      >
                        Details & Telemetry
                      </button>
                    </div>
                  </div>

                  {/* Status Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 text-xs">
                    <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Last Heartbeat</span>
                      <p className="font-mono text-slate-800 dark:text-slate-200 font-bold">
                        {c.last_heartbeat ? new Date(c.last_heartbeat).toLocaleTimeString() : 'Never'}
                      </p>
                    </div>
                    <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Last Transmission</span>
                      <p className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                        {c.last_successful_transmission ? new Date(c.last_successful_transmission).toLocaleTimeString() : 'Never'}
                      </p>
                    </div>
                    <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Local Buffered Records</span>
                      <p className="font-mono text-amber-600 dark:text-amber-400 font-bold">
                        {c.buffered_records_count || 0} in SQLite
                      </p>
                    </div>
                    <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">Failed Transmissions</span>
                      <p className="font-mono text-rose-600 dark:text-rose-400 font-bold">
                        {c.failed_transmissions_count || 0}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ONBOARDING WIZARD MODAL */}
      {wizardOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fadeIn">
          <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl p-6 sm:p-8 space-y-6 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <span className="p-2 rounded-xl bg-cyan-50 dark:bg-cyan-950/80 text-cyan-600 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-800/50">
                  <Monitor className="w-5 h-5" />
                </span>
                <div>
                  <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                    Onboard New Device
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Step {wizardStep} of 3: {
                      wizardStep === 1 ? 'Device Metadata' :
                      wizardStep === 2 ? 'Secure Credential & Command' :
                      'Live Waiting Room'
                    }
                  </p>
                </div>
              </div>
              <button 
                onClick={resetWizard}
                className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Stepper Indicator */}
            <div className="grid grid-cols-3 gap-2 text-xs font-semibold">
              <div className={`p-2 rounded-xl border text-center transition ${
                wizardStep >= 1 ? 'bg-cyan-50 dark:bg-cyan-950/60 border-cyan-500 text-cyan-600 dark:text-cyan-400 font-bold' : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-400'
              }`}>
                1. Register
              </div>
              <div className={`p-2 rounded-xl border text-center transition ${
                wizardStep >= 2 ? 'bg-cyan-50 dark:bg-cyan-950/60 border-cyan-500 text-cyan-600 dark:text-cyan-400 font-bold' : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-400'
              }`}>
                2. Install & Token
              </div>
              <div className={`p-2 rounded-xl border text-center transition ${
                wizardStep >= 3 ? 'bg-cyan-50 dark:bg-cyan-950/60 border-cyan-500 text-cyan-600 dark:text-cyan-400 font-bold' : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-400'
              }`}>
                3. Online Verify
              </div>
            </div>

            {/* STEP 1: Registration Form */}
            {wizardStep === 1 && (
              <form onSubmit={handleRegisterDevice} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-200">
                    Device Hostname / Display Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Win11-Workstation-01 or Edge-Host-Win"
                    value={deviceName}
                    onChange={(e) => setDeviceName(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-700 dark:text-slate-200">
                      Target Operating System
                    </label>
                    <select
                      value={osType}
                      onChange={(e) => setOsType(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-cyan-500 focus:outline-none font-semibold"
                    >
                      <option value="windows">Windows 10 / 11 (Supported)</option>
                      <option value="linux">Linux POSIX (Architecture Ready)</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-700 dark:text-slate-200">
                      Environment Tier
                    </label>
                    <select
                      value={environment}
                      onChange={(e) => setEnvironment(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-cyan-500 focus:outline-none font-semibold"
                    >
                      <option value="production">Production</option>
                      <option value="staging">Staging</option>
                      <option value="development">Development / Testing</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-200">
                    Description (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Primary developer workstation in engineering lab"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                  />
                </div>

                <div className="p-3.5 rounded-xl bg-cyan-50/50 dark:bg-cyan-950/30 border border-cyan-200/60 dark:border-cyan-800/40 flex items-start gap-2.5 text-xs text-slate-600 dark:text-slate-300">
                  <ShieldCheck className="w-4 h-4 text-cyan-600 dark:text-cyan-400 shrink-0 mt-0.5" />
                  <p>
                    <strong className="text-cyan-700 dark:text-cyan-300">Zero-Trust Isolation:</strong> The device will be strictly locked to your organization tenant. Frontend-supplied tenant IDs are rejected.
                  </p>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={registering || !deviceName.trim()}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold transition shadow-md shadow-cyan-500/20 active:scale-[0.98] disabled:opacity-50"
                  >
                    {registering ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
                    Generate Enrollment Token
                  </button>
                </div>
              </form>
            )}

            {/* STEP 2: Token Generation & Copyable PowerShell Command */}
            {wizardStep === 2 && registeredData && (
              <div className="space-y-4">
                <div className="p-3.5 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700/60 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-bold">Security Notice: Single-Use Credential</strong>
                    <p className="mt-0.5 text-slate-600 dark:text-slate-300">
                      This enrollment token expires in 15 minutes and will never be presented again. Upon execution, the collector securely exchanges it for permanent operational keys.
                    </p>
                  </div>
                </div>

                {/* Token Box */}
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-200">
                    One-Time Enrollment Token
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={registeredData.enrollment_token}
                      className="flex-1 font-mono text-xs px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 select-all"
                    />
                    <button
                      onClick={() => copyToClipboard(registeredData.enrollment_token, 'token')}
                      className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 transition"
                      title="Copy Token"
                    >
                      {copiedToken ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Copyable PowerShell Script Box */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-200">
                    <span className="flex items-center gap-1.5">
                      <Terminal className="w-4 h-4 text-cyan-500" />
                      Windows PowerShell Enrollment Command
                    </span>
                    <span className="text-[10px] text-slate-400 font-normal">Run in Windows Terminal</span>
                  </div>
                  
                  <div className="relative">
                    <pre className="p-4 rounded-2xl bg-slate-950 text-cyan-400 font-mono text-xs overflow-x-auto border border-slate-800 leading-relaxed">
                      {registeredData.powershell_command}
                    </pre>
                    <button
                      onClick={() => copyToClipboard(registeredData.powershell_command, 'cmd')}
                      className="absolute top-3 right-3 px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-white text-xs font-bold border border-slate-700 flex items-center gap-1.5 transition"
                    >
                      {copiedCmd ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedCmd ? 'Copied' : 'Copy Command'}</span>
                    </button>
                  </div>
                </div>

                {/* Alternative Python CLI */}
                <div className="space-y-1.5 pt-1">
                  <label className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                    Alternative: Run via Python CLI
                  </label>
                  <pre className="p-3 rounded-xl bg-slate-100 dark:bg-slate-950 text-slate-800 dark:text-slate-300 font-mono text-xs overflow-x-auto border border-slate-200 dark:border-slate-800">
                    {registeredData.enroll_cli_command}
                  </pre>
                </div>

                <div className="flex justify-between items-center pt-3 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={() => setWizardStep(1)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition"
                  >
                    Back
                  </button>

                  <button
                    onClick={() => setWizardStep(3)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold transition shadow-md shadow-emerald-500/20 active:scale-[0.98]"
                  >
                    <span>I've Run the Script: Listen for Device</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: Live Verification Waiting Room */}
            {wizardStep === 3 && (
              <div className="space-y-6 text-center py-4">
                {!waitingSuccess ? (
                  <div className="space-y-4">
                    <div className="relative mx-auto w-16 h-16 flex items-center justify-center">
                      <div className="absolute inset-0 rounded-full border-4 border-cyan-500/20 animate-ping" />
                      <div className="relative p-4 rounded-full bg-cyan-50 dark:bg-cyan-950/80 border border-cyan-500 text-cyan-500">
                        <Radio className="w-8 h-8 animate-pulse" />
                      </div>
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900 dark:text-white">
                        Listening for Initial Device Signal...
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto">
                        Waiting for <strong className="text-cyan-600 dark:text-cyan-400">{registeredData?.device_name}</strong> to execute the PowerShell script and complete the enrollment handshake.
                      </p>
                    </div>

                    <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 max-w-md mx-auto text-left space-y-2 text-xs">
                      <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                        <span>Registration State:</span>
                        <span className="font-mono font-bold text-amber-500">PENDING_HANDSHAKE</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                        <span>Expected OS:</span>
                        <span className="font-mono font-bold text-slate-700 dark:text-slate-200 capitalize">{registeredData?.os_type}</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                        <span>Poll Interval:</span>
                        <span className="font-mono text-slate-500">Every 3 seconds</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-5 animate-fadeIn">
                    <div className="mx-auto w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-950/80 border-2 border-emerald-500 flex items-center justify-center text-emerald-500">
                      <CheckCircle2 className="w-10 h-10" />
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-slate-900 dark:text-white">
                        Device Successfully Enrolled & Online!
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        First cryptographic heartbeat and kernel telemetry batch successfully ingested.
                      </p>
                    </div>

                    <div className="p-4 rounded-2xl bg-emerald-50/50 dark:bg-emerald-950/30 border border-emerald-300 dark:border-emerald-700/50 max-w-md mx-auto text-left space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-600 dark:text-slate-300">Assigned Collector ID:</span>
                        <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">{waitingSuccess.id}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-600 dark:text-slate-300">Reported Hostname:</span>
                        <span className="font-mono font-bold text-slate-800 dark:text-slate-100">{waitingSuccess.hostname}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-600 dark:text-slate-300">Status:</span>
                        <span className="font-mono font-bold text-emerald-500 uppercase">ONLINE</span>
                      </div>
                    </div>

                    <div className="pt-2 flex justify-center gap-3">
                      <button
                        onClick={() => {
                          resetWizard();
                          handleOpenDetails(waitingSuccess);
                        }}
                        className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold transition shadow-md shadow-cyan-500/20"
                      >
                        Open Device Details & Telemetry
                      </button>
                      <button
                        onClick={resetWizard}
                        className="px-4 py-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-200 dark:hover:bg-slate-700 transition"
                      >
                        Done
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* DEVICE DETAILS & AUDIT MODAL */}
      {selectedCollector && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fadeIn">
          <div className="relative w-full max-w-3xl bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl p-6 sm:p-8 space-y-6 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
              <div className="flex items-center gap-3.5">
                <div className={`p-3 rounded-2xl border ${
                  selectedCollector.status === 'online'
                    ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30'
                    : selectedCollector.status === 'revoked'
                    ? 'bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-500/30'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500 border-slate-200 dark:border-slate-700'
                }`}>
                  <Monitor className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                      {selectedCollector.name}
                    </h2>
                    <StatusBadge status={selectedCollector.status} />
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      v{selectedCollector.version}
                    </span>
                  </div>
                  <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
                    Collector ID: {selectedCollector.id}
                  </p>
                </div>
              </div>

              <button 
                onClick={() => setSelectedCollector(null)}
                className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tab navigation */}
            <div className="flex gap-2 border-b border-slate-100 dark:border-slate-800 pb-2">
              <button
                onClick={() => setDetailTab('metrics')}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition ${
                  detailTab === 'metrics'
                    ? 'bg-cyan-50 dark:bg-cyan-950/60 text-cyan-600 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-800/40'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                Live Metrics & Specifications
              </button>
              <button
                onClick={() => setDetailTab('audit')}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition ${
                  detailTab === 'audit'
                    ? 'bg-cyan-50 dark:bg-cyan-950/60 text-cyan-600 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-800/40'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                Authentication & Audit History
              </button>
            </div>

            {/* TAB CONTENT: Metrics & Specifications */}
            {detailTab === 'metrics' && (
              <div className="space-y-5">
                {/* Hardware & Identity details */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-bold">OS Version</span>
                    <p className="font-mono font-bold text-slate-800 dark:text-slate-200 truncate mt-0.5">
                      {deviceDetails?.server?.os_info || deviceDetails?.collector?.os_type || 'Windows 11'}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-bold">Hostname</span>
                    <p className="font-mono font-bold text-slate-800 dark:text-slate-200 truncate mt-0.5">
                      {selectedCollector.hostname}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-bold">IP Address</span>
                    <p className="font-mono font-bold text-slate-800 dark:text-slate-200 truncate mt-0.5">
                      {selectedCollector.ip_address || '127.0.0.1'}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-bold">Environment</span>
                    <p className="font-mono font-bold text-cyan-600 dark:text-cyan-400 capitalize mt-0.5">
                      {deviceDetails?.collector?.environment || 'Production'}
                    </p>
                  </div>
                </div>

                {/* Real-Time Telemetry Gauges */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">
                      Actual Host Telemetry (via psutil)
                    </h4>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40">
                      Authentic Kernel Telemetry
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-center">
                      <span className="text-[10px] uppercase font-bold text-slate-400">CPU Usage</span>
                      <div className="mt-1 text-2xl font-black text-cyan-600 dark:text-cyan-400 font-mono">
                        {deviceDetails?.latest_metrics?.cpu_percent ?? selectedCollector.last_cpu ?? 0}%
                      </div>
                    </div>

                    <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-center">
                      <span className="text-[10px] uppercase font-bold text-slate-400">RAM Usage</span>
                      <div className="mt-1 text-2xl font-black text-indigo-600 dark:text-indigo-400 font-mono">
                        {deviceDetails?.latest_metrics?.memory_percent ?? selectedCollector.last_memory ?? 0}%
                      </div>
                    </div>

                    <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-center">
                      <span className="text-[10px] uppercase font-bold text-slate-400">Primary Disk</span>
                      <div className="mt-1 text-2xl font-black text-emerald-600 dark:text-emerald-400 font-mono">
                        {deviceDetails?.latest_metrics?.disk_percent ?? selectedCollector.last_disk ?? 0}%
                      </div>
                    </div>

                    <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-center">
                      <span className="text-[10px] uppercase font-bold text-slate-400">Network Latency</span>
                      <div className="mt-1 text-2xl font-black text-amber-600 dark:text-amber-400 font-mono">
                        {deviceDetails?.latest_metrics?.network_latency_ms ?? 0} ms
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB CONTENT: Audit Trail */}
            {detailTab === 'audit' && (
              <div className="space-y-4">
                <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">
                  Device Lifecycle & Security Audit Trail
                </h4>
                
                {(!deviceDetails?.audit_logs || deviceDetails.audit_logs.length === 0) ? (
                  <p className="text-xs text-slate-400 text-center py-6">No audit records found.</p>
                ) : (
                  <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                    {deviceDetails.audit_logs.map((a) => (
                      <div 
                        key={a.id} 
                        className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs flex items-center justify-between"
                      >
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                              a.action === 'ENROLLED' ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400' :
                              a.action === 'REVOKED' ? 'bg-rose-100 dark:bg-rose-950 text-rose-600 dark:text-rose-400' :
                              'bg-cyan-100 dark:bg-cyan-950 text-cyan-600 dark:text-cyan-400'
                            }`}>
                              {a.action}
                            </span>
                            <span className="font-semibold text-slate-700 dark:text-slate-200">
                              Actor: {a.actor}
                            </span>
                          </div>
                          {a.details_json && (
                            <p className="font-mono text-[10px] text-slate-500 truncate max-w-md">
                              {a.details_json}
                            </p>
                          )}
                        </div>
                        <span className="text-[10px] font-mono text-slate-400 shrink-0">
                          {new Date(a.timestamp).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Action Bar & Revoke Danger Zone */}
            <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <div>
                {selectedCollector.status !== 'revoked' && !selectedCollector.is_revoked && (
                  !showRevokeConfirm ? (
                    <button
                      onClick={() => setShowRevokeConfirm(true)}
                      className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 text-xs font-bold transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Revoke Device Access
                    </button>
                  ) : (
                    <div className="flex items-center gap-2 animate-fadeIn">
                      <span className="text-xs font-semibold text-rose-600 dark:text-rose-400">
                        Confirm permanent revocation?
                      </span>
                      <button
                        onClick={handleRevoke}
                        disabled={revoking}
                        className="px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition shadow-xs"
                      >
                        {revoking ? 'Revoking...' : 'Yes, Revoke'}
                      </button>
                      <button
                        onClick={() => setShowRevokeConfirm(false)}
                        className="px-2.5 py-1.5 rounded-xl text-slate-400 hover:text-slate-600 text-xs"
                      >
                        Cancel
                      </button>
                    </div>
                  )
                )}
              </div>

              <button
                onClick={() => setSelectedCollector(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-200 dark:hover:bg-slate-700 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
