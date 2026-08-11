// Shared reactive state for WattWatch, built with Svelte 5 runes.
// Plain .svelte.js module exporting singleton instances — no stores needed.

import { api, ApiError, onUnauthorized } from './api.js';

const POLL_INTERVAL_MS = 2000;

class ToastStore {
  items = $state([]);
  #nextId = 1;

  push(message, kind = 'error', timeoutMs = 5000) {
    const id = this.#nextId++;
    this.items.push({ id, message, kind });
    if (timeoutMs > 0) {
      setTimeout(() => this.dismiss(id), timeoutMs);
    }
    return id;
  }

  dismiss(id) {
    const idx = this.items.findIndex((t) => t.id === id);
    if (idx !== -1) this.items.splice(idx, 1);
  }
}

export const toasts = new ToastStore();

class AuthState {
  username = $state(null);
  checked = $state(false);

  get isAuthenticated() {
    return this.username !== null;
  }

  async check() {
    try {
      const me = await api.me();
      this.username = me.username;
    } catch {
      this.username = null;
    } finally {
      this.checked = true;
    }
  }

  async login(username, password) {
    const res = await api.login(username, password);
    this.username = res.username;
    return res;
  }

  async logout() {
    try {
      await api.logout();
    } catch {
      // best-effort; clear local state regardless
    }
    this.username = null;
  }

  clear() {
    this.username = null;
  }
}

export const auth = new AuthState();

onUnauthorized(() => {
  auth.clear();
});

class DeviceState {
  reachable = $state(true);
  error = $state(null);
  stale = $state(false);
  device = $state(null);
  live = $state(null);
  lastUpdated = $state(null);
  lastFetchFailed = $state(false);
  loadedOnce = $state(false);

  // Rolling buffer of recent live power readings for the hero sparkline.
  sparkline = $state([]);
  #sparklineMax = 150;

  #pollTimer = null;
  #inFlight = false;
  #visibilityHandler = null;

  applySnapshot(snapshot) {
    this.reachable = snapshot.reachable;
    this.error = snapshot.error ?? null;
    this.stale = snapshot.stale ?? false;
    this.device = snapshot.device ?? null;
    this.live = snapshot.live ?? null;
    this.lastUpdated = new Date();
    this.lastFetchFailed = false;
    this.loadedOnce = true;

    if (this.live?.power_w !== null && this.live?.power_w !== undefined) {
      this.sparkline.push({
        t: this.live.timestamp ?? new Date().toISOString(),
        w: this.live.power_w
      });
      if (this.sparkline.length > this.#sparklineMax) {
        this.sparkline.splice(0, this.sparkline.length - this.#sparklineMax);
      }
    }
  }

  applyDeviceOnly(device) {
    // Used after mutating endpoints that return only the device object.
    this.device = device;
    this.lastUpdated = new Date();
  }

  async fetchOnce() {
    if (this.#inFlight) return;
    this.#inFlight = true;
    try {
      const snapshot = await api.state();
      this.applySnapshot(snapshot);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        // Auth handler already cleared session state; stop this poll cycle quietly.
        return;
      }
      this.lastFetchFailed = true;
    } finally {
      this.#inFlight = false;
    }
  }

  startPolling() {
    this.stopPolling();
    this.fetchOnce();
    this.#pollTimer = setInterval(() => {
      if (!document.hidden) this.fetchOnce();
    }, POLL_INTERVAL_MS);

    this.#visibilityHandler = () => {
      if (!document.hidden) this.fetchOnce();
    };
    document.addEventListener('visibilitychange', this.#visibilityHandler);
  }

  stopPolling() {
    if (this.#pollTimer) {
      clearInterval(this.#pollTimer);
      this.#pollTimer = null;
    }
    if (this.#visibilityHandler) {
      document.removeEventListener('visibilitychange', this.#visibilityHandler);
      this.#visibilityHandler = null;
    }
  }

  reset() {
    this.stopPolling();
    this.reachable = true;
    this.error = null;
    this.stale = false;
    this.device = null;
    this.live = null;
    this.lastUpdated = null;
    this.lastFetchFailed = false;
    this.loadedOnce = false;
    this.sparkline = [];
  }
}

export const deviceState = new DeviceState();
