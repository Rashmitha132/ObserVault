// frontend/src/services/api.js
const RAW_BACKEND_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const API_BASE = `${RAW_BACKEND_URL}/api/v1`;

function resolveUrl(path) {
  if (RAW_BACKEND_URL && path.startsWith('/api')) {
    return `${RAW_BACKEND_URL}${path}`;
  }
  return path;
}

function getAuthHeaders() {
  const token = localStorage.getItem('observault_token');
  const headers = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };

  try {
    const res = await fetch(resolveUrl(url), { ...options, headers });
    if (res.status === 401) {
      // Clear token and redirect if unauthorized
      localStorage.removeItem('observault_token');
      localStorage.removeItem('observault_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || data.detail || 'API Request Failed');
    }
    return data;
  } catch (err) {
    console.error(`[API Error: ${endpoint}]`, err);
    throw err;
  }
}

export const api = {
  // Auth
  login: async (email, password) => {
    return request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },
  getCurrentUser: async () => request('/auth/me'),
  logout: async () => request('/auth/logout', { method: 'POST' }),

  // Dashboard
  getDashboardOverview: async () => request('/dashboard/overview'),
  getDashboardSummary: async () => request('/dashboard/summary'),

  // Infrastructure
  getInfrastructure: async (status = '', search = '') => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (search) params.append('search', search);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request(`/infrastructure${query}`);
  },
  getServerDetail: async (serverId) => request(`/infrastructure/${serverId}`),

  // Network
  getNetworkObservability: async () => request('/network'),

  // Security
  getSecurityEvents: async () => request('/security-events'),

  // Alerts
  getAlerts: async (status = '', severity = '') => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (severity) params.append('severity', severity);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request(`/alerts${query}`);
  },
  updateAlertStatus: async (alertId, status) => {
    return request(`/alerts/${alertId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  // Incidents
  getIncidents: async (status = '', severity = '') => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (severity) params.append('severity', severity);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request(`/incidents${query}`);
  },
  getIncident: async (incidentId) => request(`/incidents/${incidentId}`),
  updateIncidentStatus: async (incidentId, status) => {
    return request(`/incidents/${incidentId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  // Collectors & Device Onboarding (Phase 2F)
  getCollectors: async () => request('/collectors'),
  getCollectorStats: async () => request('/collectors/stats'),
  registerDevice: async (deviceData) => {
    return request('/collectors/register', {
      method: 'POST',
      body: JSON.stringify(deviceData),
    });
  },
  revokeDevice: async (collectorId) => {
    return request(`/collectors/${collectorId}/revoke`, {
      method: 'POST',
    });
  },
  getDeviceDetails: async (collectorId) => request(`/collectors/${collectorId}/details`),
  getDeviceAudit: async (collectorId) => request(`/collectors/${collectorId}/audit`),

  // Egress & Privacy Proof
  getEgressProof: async () => request('/egress'),
  verifyPrivacy: async (rawEvent) => {
    return request('/egress/verify-privacy', {
      method: 'POST',
      body: JSON.stringify({ raw_event: rawEvent }),
    });
  },

  // Recommendations
  getRecommendations: async (severity = '', status = '') => {
    const params = new URLSearchParams();
    if (severity) params.append('severity', severity);
    if (status) params.append('status', status);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request(`/recommendations${query}`);
  },
  updateRecommendationStatus: async (id, status) => {
    return request(`/recommendations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  // Tenant & Settings
  getTenantSettings: async () => request('/tenant/settings'),
  updateTenantSettings: async (settings) => {
    return request('/tenant/settings', {
      method: 'PATCH',
      body: JSON.stringify(settings),
    });
  },

  // Demo Simulator Trigger
  triggerScenario: async (scenario, serverTarget = 'srv-prod-api-01') => {
    return request('/simulator/scenario', {
      method: 'POST',
      body: JSON.stringify({ scenario, server_target: serverTarget }),
    });
  },

  // Phase 2: OpenTelemetry & Distributed Traces
  getTraces: async (serviceName = '', status = '', minDuration = '') => {
    const params = new URLSearchParams();
    if (serviceName) params.append('service_name', serviceName);
    if (status) params.append('status_filter', status);
    if (minDuration) params.append('min_duration_ms', minDuration);
    const query = params.toString() ? `?${params.toString()}` : '';
    // Call /api/v2/traces
    const url = `/api/v2/traces${query}`;
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getTraceDetail: async (traceId) => {
    const url = `/api/v2/traces/${traceId}`;
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getServices: async () => {
    const url = '/api/v2/services';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getServiceDependencies: async () => {
    const url = '/api/v2/services/dependencies';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },

  // Phase 2: Security Hardening & Certificates
  getCertificates: async () => request('/security-hardening/certificates'),
  issueCertificate: async (collectorId, validityDays = 90) => {
    return request('/security-hardening/certificates/issue', {
      method: 'POST',
      body: JSON.stringify({ collector_id: collectorId, validity_days: validityDays })
    });
  },
  revokeCertificate: async (serialNumber) => {
    return request('/security-hardening/certificates/revoke', {
      method: 'POST',
      body: JSON.stringify({ serial_number: serialNumber })
    });
  },
  getSecurityAudit: async () => request('/security-hardening/audit'),
  runPrivacyTests: async () => request('/security-hardening/privacy-tests'),

  // Phase 2C: Machine Learning & Statistical Anomaly Detection
  getMLAnomalies: async (algorithm = '', severity = '') => {
    const params = new URLSearchParams();
    if (algorithm) params.append('algorithm', algorithm);
    if (severity) params.append('severity', severity);
    const query = params.toString() ? `?${params.toString()}` : '';
    const url = `/api/v2/anomalies${query}`;
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getMLAnomalyDetail: async (anomalyId) => {
    const url = `/api/v2/anomalies/${anomalyId}`;
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getMLModels: async () => {
    const url = '/api/v2/models';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getMLEvaluation: async () => {
    const url = '/api/v2/models/evaluation';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  retrainMLModel: async () => {
    const url = '/api/v2/models/train';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { method: 'POST', headers });
    return res.json();
  },

  // Phase 2D: Intelligent Root Cause Analysis (RCA)
  getRCAIncidents: async (status = '', severity = '') => {
    const params = new URLSearchParams();
    if (status) params.append('status_filter', status);
    if (severity) params.append('severity_filter', severity);
    const query = params.toString() ? `?${params.toString()}` : '';
    const url = `/api/v2/rca/incidents${query}`;
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getIncidentRCA: async (incidentId) => {
    const url = `/api/v2/rca/incidents/${incidentId}`;
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getBlastRadius: async (componentName) => {
    const url = `/api/v2/rca/blast-radius/${encodeURIComponent(componentName)}`;
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },

  // Phase 2E: Predictive Analytics, Capacity Forecasting & Integrations
  getForecast: async (serverId, metricName = 'disk_percent', horizon = '7d') => {
    const url = `/api/v2/predictive/forecast/${serverId}?metric_name=${metricName}&horizon=${horizon}`;
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getCapacityWarnings: async () => {
    const url = '/api/v2/predictive/capacity-warnings';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getSLOMetrics: async () => {
    const url = '/api/v2/predictive/slo';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  createSLO: async (sloData) => {
    const url = '/api/v2/predictive/slo';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), {
      method: 'POST',
      headers,
      body: JSON.stringify(sloData),
    });
    return res.json();
  },
  getIntegrations: async () => {
    const url = '/api/v2/integrations';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getRealHostTelemetry: async () => {
    const url = '/api/v2/integrations/real-host';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  getDockerStatus: async () => {
    const url = '/api/v2/integrations/docker-status';
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { headers });
    return res.json();
  },
  testIntegration: async (integrationType) => {
    const url = `/api/v2/integrations/test/${integrationType}`;
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('observault_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(resolveUrl(url), { method: 'POST', headers });
    return res.json();
  },

  // AI Intelligence Layer (Phase 3)
  explainIncident: async (incidentId) => {
    return request(`/ai/incidents/${incidentId}/explain`, { method: 'POST' });
  },
  getIncidentAIRCA: async (incidentId) => {
    return request(`/ai/incidents/${incidentId}/rca`, { method: 'POST' });
  },
  getPredictiveAIAnalysis: async (serverId, metricName = 'disk_percent', horizon = '7d') => {
    return request(`/ai/servers/${serverId}/predictive-analysis`, {
      method: 'POST',
      body: JSON.stringify({ metric_name: metricName, horizon }),
    });
  },
  sendCopilotChat: async (message, incidentId = null, serverId = null, conversationHistory = []) => {
    return request('/ai/copilot/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        incident_id: incidentId,
        server_id: serverId,
        conversation_history: conversationHistory,
      }),
    });
  },
  getRemediationPlan: async (incidentId) => {
    return request(`/ai/incidents/${incidentId}/remediation-plan`, { method: 'POST' });
  },
};
