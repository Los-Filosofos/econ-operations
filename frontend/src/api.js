// HTTP Client for ECON Operations API

const API_BASE = '/api/v1';

async function request(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!res.ok) {
    let errDetail = `${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) errDetail = errJson.detail;
    } catch (_) {}
    throw new Error(errDetail);
  }

  return res.json();
}

export const api = {
  // Hub
  getHub: (mode = 'fixture') => request(`${API_BASE}/hub?mode=${mode}`),

  // Graph
  getGraph: (mode = 'fixture') => request(`${API_BASE}/graph?mode=${mode}`),

  // Indicators / SLAs
  getIndicators: (mode = 'fixture') => request(`${API_BASE}/indicators?mode=${mode}`),

  // Integration trace
  getIntegration: (requestId, mode = 'fixture') =>
    request(`${API_BASE}/integration/${encodeURIComponent(requestId)}?mode=${mode}`),

  // Suggestions for request
  getSuggestions: (requestId, mode = 'fixture') =>
    request(`${API_BASE}/requests/${encodeURIComponent(requestId)}/suggestions?mode=${mode}`),

  // Operations
  getOperations: (mode = 'fixture') => request(`${API_BASE}/operations?mode=${mode}`),
  getCatalogs: () => request(`${API_BASE}/operations/catalogs`),
  savePlan: (body) =>
    request(`${API_BASE}/operations/plans`, { method: 'POST', body: JSON.stringify(body) }),
  queueMovement: (id, body = {}) =>
    request(`${API_BASE}/operations/${encodeURIComponent(id)}/queue`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  syncOperations: (body = {}) =>
    request(`${API_BASE}/operations/sync`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  registerReceipt: (id, body) =>
    request(`${API_BASE}/operations/${encodeURIComponent(id)}/receipt`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // Status & Health
  getStatus: () => request(`${API_BASE}/status`),
  getHealth: () => request('/health'),
};
