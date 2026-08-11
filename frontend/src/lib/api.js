// Thin fetch wrapper for the WattWatch API.
// All calls are same-origin relative paths, credentials included, JSON in/out.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// Set by state.svelte.js so a 401 anywhere can flip the app back to the login screen.
let unauthorizedHandler = null;
export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

async function request(path, options = {}) {
  const res = await fetch(path, {
    credentials: 'same-origin',
    headers:
      options.body !== undefined
        ? { 'Content-Type': 'application/json', ...(options.headers || {}) }
        : options.headers,
    ...options
  });

  if (res.status === 401) {
    if (unauthorizedHandler) unauthorizedHandler();
    let detail = 'Not authenticated';
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // ignore
    }
    throw new ApiError(detail, 401);
  }

  if (res.status === 204 || res.status === 202) {
    // 202 bodies (reboot) still carry JSON; 204 never does.
    if (res.status === 202) {
      try {
        return await res.json();
      } catch {
        return null;
      }
    }
    return null;
  }

  let body = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!res.ok) {
    const detail = body?.detail ?? `Request failed (${res.status})`;
    throw new ApiError(detail, res.status);
  }

  return body;
}

function get(path) {
  return request(path, { method: 'GET' });
}

function post(path, body) {
  return request(path, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined
  });
}

export const api = {
  login: (username, password) => post('/api/auth/login', { username, password }),
  logout: () => post('/api/auth/logout'),
  me: () => get('/api/auth/me'),

  state: () => get('/api/state'),

  setPower: (on) => post('/api/device/power', { on }),
  setLed: (on) => post('/api/device/led', { on }),
  setAlias: (alias) => post('/api/device/alias', { alias }),
  reboot: () => post('/api/device/reboot'),

  energyDaily: (year, month) => {
    const params = new URLSearchParams();
    if (year != null) params.set('year', year);
    if (month != null) params.set('month', month);
    const qs = params.toString();
    return get(`/api/energy/daily${qs ? `?${qs}` : ''}`);
  },
  energyMonthly: (year) => {
    const params = new URLSearchParams();
    if (year != null) params.set('year', year);
    const qs = params.toString();
    return get(`/api/energy/monthly${qs ? `?${qs}` : ''}`);
  },
  energyReset: () => post('/api/energy/reset'),

  history: (hours) => get(`/api/history?hours=${encodeURIComponent(hours)}`),
  historySummary: (hours) => get(`/api/history/summary?hours=${encodeURIComponent(hours)}`),

  health: () => get('/api/health')
};
