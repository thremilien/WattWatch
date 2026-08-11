<script>
  import { auth, deviceState, toasts } from '../state.svelte.js';

  let loggingOut = $state(false);

  async function handleLogout() {
    if (loggingOut) return;
    loggingOut = true;
    try {
      await auth.logout();
    } catch {
      toasts.push('Could not reach the server to log out, but your session was cleared locally.', 'error');
    } finally {
      loggingOut = false;
    }
  }

  let connectionLabel = $derived.by(() => {
    if (!deviceState.loadedOnce) return 'Connecting…';
    if (deviceState.lastFetchFailed) return 'Connection lost';
    if (!deviceState.reachable) return 'Device unreachable';
    return 'Connected';
  });

  let connectionOk = $derived(deviceState.loadedOnce && deviceState.reachable && !deviceState.lastFetchFailed);
</script>

<header class="header">
  <div class="left">
    <span class="mark" aria-hidden="true"></span>
    <span class="app-name">WattWatch</span>
  </div>

  <div class="right">
    <span class="status" class:ok={connectionOk}>
      <span class="dot"></span>
      {connectionLabel}
    </span>
    <button class="btn logout" onclick={handleLogout} disabled={loggingOut}>
      {loggingOut ? 'Signing out…' : 'Log out'}
    </button>
  </div>
</header>

<style>
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--hairline);
    position: sticky;
    top: 0;
    background: var(--panel);
    z-index: 50;
  }

  .left {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .mark {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--signal);
  }

  .app-name {
    font-family: var(--font-condensed);
    font-weight: 600;
    font-size: 1.0625rem;
    letter-spacing: -0.01em;
  }

  .right {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .status {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    letter-spacing: 0.04em;
    color: var(--ink-muted);
  }

  .status .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ink);
    opacity: 0.6;
  }

  .status:not(.ok) .dot {
    background: var(--signal);
    opacity: 1;
  }

  .logout {
    font-size: 0.8125rem;
    padding: 0.45em 0.9em;
  }

  @media (max-width: 520px) {
    .header {
      padding: 0.875rem 1rem;
    }
    .status span:not(.dot) {
      display: none;
    }
  }
</style>
