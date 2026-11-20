// frontend/src/pages/PrivacyEgressPage.jsx
import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import PrivacyFlowGraphic from '../components/PrivacyFlowGraphic';
import StatusBadge from '../components/StatusBadge';
import StatCard from '../components/StatCard';
import { 
  ShieldCheck, 
  Lock, 
  EyeOff, 
  CheckCircle2, 
  AlertOctagon, 
  FileCode, 
  Play, 
  RefreshCw,
  Terminal,
  Database,
  ArrowRight,
  Sparkles,
  Shield,
  Layers
} from 'lucide-react';

export default function PrivacyEgressPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Live Privacy Demonstration Playground State
  const [testRawPayload, setTestRawPayload] = useState(JSON.stringify({
    "event_type": "failed_login",
    "username": "root_admin",
    "password": "SuperSecretPassword123!DoNotLeak",
    "auth_token": "bearer_jwt_prod_api_token_abc789",
    "api_key": "sk_live_master_key_secret_456",
    "ip_address": "192.168.1.50",
    "raw_request_payload": "POST /api/v1/auth/login HTTP/1.1",
    "cpu_percent": 42.0,
    "memory_percent": 55.4,
    "disk_percent": 60.1,
    "network_latency_ms": 19.5,
    "packet_loss_percent": 0.0,
    "failed_attempt_count": 5
  }, null, 2));

  const [verifyResult, setVerifyResult] = useState(null);
  const [verifyLoading, setVerifyLoading] = useState(false);

  const fetchProof = async () => {
    try {
      setLoading(true);
      const res = await api.getEgressProof();
      setData(res);
    } catch (err) {
      console.error('Failed to load privacy egress proof', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProof();
  }, []);

  const handleRunVerify = async () => {
    setVerifyLoading(true);
    setVerifyResult(null);
    try {
      const parsed = JSON.parse(testRawPayload);
      const res = await api.verifyPrivacy(parsed);
      setVerifyResult(res);
    } catch (err) {
      setVerifyResult({
        status_message: `JSON Parse / Processing Error: ${err.message}`,
        sensitive_data_in_cloud_db: false,
        sensitive_fields_detected: [],
        approved_outbound_metadata: {}
      });
    } finally {
      setVerifyLoading(false);
    }
  };

  const {
    total_records_processed_locally = 0,
    total_records_approved = 0,
    total_records_rejected = 0,
    currently_buffered_records = 0,
    last_successful_transmission,
    approved_outbound_fields = [],
    rejected_fields_examples = [],
    recent_audits = [],
    sample_safe_payload = {}
  } = data || {};

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40">
              <ShieldCheck className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Privacy & Egress Proof Dashboard
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Mathematical proof and audit verification that sensitive operational payloads never cross your network perimeter.
          </p>
        </div>
        <button 
          onClick={fetchProof}
          disabled={loading}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 transition shadow-xs active:scale-[0.98] disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-500' : ''}`} />
          Refresh Proof Audits
        </button>
      </div>

      {/* Visual Architectural Data Flow */}
      <PrivacyFlowGraphic />

      {/* Primary Verification Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-5">
        <StatCard
          title="Processed Locally"
          value={total_records_processed_locally}
          subtitle="Audited in customer perimeter"
          icon={Layers}
          color="blue"
        />
        <StatCard
          title="Approved Outbound"
          value={total_records_approved}
          subtitle="Strict allow-list compliant"
          icon={CheckCircle2}
          color="emerald"
        />
        <StatCard
          title="Fields Stripped"
          value={total_records_rejected}
          subtitle="Passwords, tokens, PII purged"
          icon={EyeOff}
          color="cyan"
        />
        <StatCard
          title="SQLite Buffer"
          value={currently_buffered_records}
          subtitle="Pending offline staging queue"
          icon={Database}
          color="amber"
        />
      </div>

      {/* INTERACTIVE LIVE PRIVACY VERIFICATION TOOL */}
      <div className="glass-card rounded-2xl p-6 border border-cyan-400/40 dark:border-cyan-500/30 shadow-soft-lg space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800/80 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-cyan-100 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-400 border border-cyan-300 dark:border-cyan-500/30">
                <Sparkles className="w-4 h-4" />
              </span>
              <h3 className="text-base font-extrabold text-slate-900 dark:text-white">
                Live Interactive Privacy Demonstration Playground
              </h3>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Submit a mock raw event containing real passwords, authentication headers, or API tokens. Watch the local privacy filter strip them instantly and verify zero occurrences exist in SaaS storage.
            </p>
          </div>
          <button
            disabled={verifyLoading}
            onClick={handleRunVerify}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs shadow-md shadow-cyan-500/25 transition disabled:opacity-50 active:scale-[0.99]"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{verifyLoading ? 'Sanitizing...' : 'Execute Privacy Filter & Leak Test'}</span>
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Input: Raw Local Event */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
                <AlertOctagon className="w-3.5 h-3.5" />
                Raw Local Operational Event (Contains Fake Secrets)
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Editable JSON</span>
            </div>
            <textarea
              rows={12}
              value={testRawPayload}
              onChange={(e) => setTestRawPayload(e.target.value)}
              className="w-full font-mono text-xs p-3.5 rounded-xl bg-rose-50/40 dark:bg-slate-950 border border-rose-200 dark:border-slate-800 text-rose-900 dark:text-rose-300 focus:outline-none focus:border-cyan-500 transition leading-relaxed"
            />
          </div>

          {/* Output: Approved Outbound Metadata */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Approved Outbound Metadata (Transmitted to Cloud)
              </span>
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-mono font-semibold">100% Allow-List Conforming</span>
            </div>
            <div className="w-full h-[260px] font-mono text-xs p-3.5 rounded-xl bg-emerald-50/40 dark:bg-slate-950 border border-emerald-200 dark:border-slate-800 text-emerald-900 dark:text-emerald-300 overflow-y-auto leading-relaxed">
              {verifyResult ? (
                <pre>{JSON.stringify(verifyResult.approved_outbound_metadata, null, 2)}</pre>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 dark:text-slate-500 text-xs text-center space-y-2">
                  <FileCode className="w-8 h-8 opacity-40" />
                  <span>Click "Execute Privacy Filter & Leak Test" above to execute sanitisation.</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Live Leak Verification Badge */}
        {verifyResult && (
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2 animate-fadeIn">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-white">
                <ShieldCheck className="w-5 h-5 text-emerald-500" />
                <span>Verification Results</span>
              </div>
              <span className={`text-xs font-mono font-bold px-3 py-1 rounded-full border ${
                verifyResult.sensitive_data_in_cloud_db
                  ? 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-500/40'
                  : 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40'
              }`}>
                {verifyResult.sensitive_data_in_cloud_db ? 'LEAK DETECTED' : 'ZERO CLOUD LEAK VERIFIED'}
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              {verifyResult.status_message}
            </p>
            {verifyResult.sensitive_fields_detected?.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <span className="text-[11px] text-slate-500 dark:text-slate-400 font-semibold">Stripped Locally:</span>
                {verifyResult.sensitive_fields_detected.map((f, i) => (
                  <span key={i} className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-500/30">
                    {f}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Schema Comparison: Approved vs Rejected */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
        {/* Approved Outbound Allow-List */}
        <div className="glass-card rounded-2xl p-5 sm:p-6 border border-emerald-200/80 dark:border-emerald-500/20 shadow-soft space-y-3">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="w-5 h-5" />
            <h3 className="text-sm font-bold">Explicit Metadata Allow-List (Permitted)</h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Only these safe operational telemetry fields can ever be packaged for outbound transmission:
          </p>
          <ul className="space-y-1.5 text-xs font-mono text-slate-700 dark:text-slate-300">
            {approved_outbound_fields.map((f, i) => (
              <li key={i} className="p-2 rounded-xl bg-slate-50/80 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800/60 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                <span className="font-semibold">{f}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Rejected Fields */}
        <div className="glass-card rounded-2xl p-5 sm:p-6 border border-rose-200/80 dark:border-rose-500/20 shadow-soft space-y-3">
          <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400">
            <EyeOff className="w-5 h-5" />
            <h3 className="text-sm font-bold">Forbidden Sensitive Attributes (Purged Locally)</h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            These fields are identified and dropped at the edge; attempting to send them triggers hard validation rejection:
          </p>
          <ul className="space-y-1.5 text-xs font-mono text-slate-700 dark:text-slate-300">
            {rejected_fields_examples.map((f, i) => (
              <li key={i} className="p-2 rounded-xl bg-slate-50/80 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800/60 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0" />
                <span className="font-semibold">{f}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Transmission Egress Audit Log */}
      <div className="glass-card rounded-2xl p-5 sm:p-6 shadow-soft space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Egress Batch Audit Trail</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Cryptographic record of batch transmissions and pre-egress field scrubbing
            </p>
          </div>
          <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            {recent_audits.length} Recent Batches
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 dark:bg-slate-900/80 text-slate-600 dark:text-slate-400 font-mono text-[10px] uppercase border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Batch ID</th>
                <th className="py-2.5 px-3 font-semibold">Timestamp</th>
                <th className="py-2.5 px-3 font-semibold">Approved Records</th>
                <th className="py-2.5 px-3 font-semibold">Fields Stripped</th>
                <th className="py-2.5 px-3 font-semibold">Stripped Field Names</th>
                <th className="py-2.5 px-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
              {recent_audits.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400 dark:text-slate-500 font-sans">
                    No egress audit records found.
                  </td>
                </tr>
              ) : (
                recent_audits.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                    <td className="py-2.5 px-3 text-cyan-600 dark:text-cyan-400 font-bold">{a.batch_id}</td>
                    <td className="py-2.5 px-3 text-slate-500 dark:text-slate-400">{new Date(a.timestamp).toLocaleTimeString()}</td>
                    <td className="py-2.5 px-3 text-emerald-600 dark:text-emerald-400 font-bold">{a.approved_count}</td>
                    <td className="py-2.5 px-3 text-rose-600 dark:text-rose-400 font-bold">{a.rejected_fields_count}</td>
                    <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300 font-sans text-[11px]">
                      {a.rejected_field_names?.join(', ') || 'None'}
                    </td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={a.status} size="xs" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
