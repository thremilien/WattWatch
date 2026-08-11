<script>
  import { api, ApiError } from '../api.js';
  import { deviceState, toasts } from '../state.svelte.js';
  import ConfirmModal from './ConfirmModal.svelte';

  let device = $derived(deviceState.device);
  let disabled = $derived(!deviceState.reachable || !device);

  // Rename
  let editingAlias = $state(false);
  let aliasDraft = $state('');
  let aliasPending = $state(false);

  function startEditAlias() {
    aliasDraft = device?.alias ?? '';
    editingAlias = true;
  }

  function cancelEditAlias() {
    editingAlias = false;
  }

  function autofocus(node) {
    node.focus();
  }

  async function saveAlias() {
    const trimmed = aliasDraft.trim();
    if (!trimmed) {
      toasts.push('Name cannot be empty.', 'error');
      return;
    }
    if (trimmed.length > 31) {
      toasts.push('Name must be 31 characters or fewer.', 'error');
      return;
    }
    aliasPending = true;
    try {
      const updated = await api.setAlias(trimmed);
      deviceState.applyDeviceOnly(updated);
      editingAlias = false;
      toasts.push('Name updated.', 'success', 2500);
    } catch (err) {
      toasts.push(describeError(err), 'error');
    } finally {
      aliasPending = false;
    }
  }

  // LED
  let ledPending = $state(false);

  async function toggleLed() {
    if (!device) return;
    ledPending = true;
    try {
      const updated = await api.setLed(!device.led_on);
      deviceState.applyDeviceOnly(updated);
    } catch (err) {
      toasts.push(describeError(err), 'error');
    } finally {
      ledPending = false;
    }
  }

  // Reboot
  let rebootConfirmOpen = $state(false);
  let rebootPending = $state(false);

  async function reboot() {
    rebootPending = true;
    try {
      await api.reboot();
      toasts.push('Rebooting — the device will be back in about 10 seconds.', 'success', 4000);
      rebootConfirmOpen = false;
    } catch (err) {
      toasts.push(describeError(err), 'error');
    } finally {
      rebootPending = false;
    }
  }

  // Sync device clock
  let syncTimePending = $state(false);

  async function syncTime() {
    syncTimePending = true;
    try {
      const updated = await api.syncTime();
      deviceState.applyDeviceOnly(updated);
      toasts.push('Device clock synced.', 'success', 2500);
    } catch (err) {
      toasts.push(describeError(err), 'error');
    } finally {
      syncTimePending = false;
    }
  }

  // Reset energy stats
  let resetConfirmOpen = $state(false);
  let resetPending = $state(false);

  async function resetEnergy() {
    resetPending = true;
    try {
      await api.energyReset();
      toasts.push('Energy statistics cleared.', 'success', 2500);
      resetConfirmOpen = false;
    } catch (err) {
      toasts.push(describeError(err), 'error');
    } finally {
      resetPending = false;
    }
  }

  function describeError(err) {
    if (err instanceof ApiError && err.status === 502) {
      return "Can't reach the plug right now. Try again shortly.";
    }
    return err instanceof ApiError ? err.message : 'Something went wrong. Try again.';
  }
</script>

<section class="settings card">
  <h2 class="section-title">Settings</h2>

  <div class="row">
    <span class="row-label">Name</span>
    {#if editingAlias}
      <form class="alias-form" onsubmit={(e) => { e.preventDefault(); saveAlias(); }}>
        <input
          type="text"
          bind:value={aliasDraft}
          maxlength="31"
          disabled={aliasPending}
          {@attach autofocus}
        />
        <button type="submit" class="btn btn-primary sm" disabled={aliasPending}>
          {aliasPending ? 'Saving…' : 'Save'}
        </button>
        <button type="button" class="btn sm" onclick={cancelEditAlias} disabled={aliasPending}>
          Cancel
        </button>
      </form>
    {:else}
      <div class="row-control">
        <span class="row-value">{device?.alias ?? '—'}</span>
        <button class="btn sm" onclick={startEditAlias} disabled={disabled}>Rename</button>
      </div>
    {/if}
  </div>

  <div class="row">
    <span class="row-label">Status LED</span>
    <div class="row-control">
      <button
        class="mini-toggle"
        class:on={device?.led_on === true}
        role="switch"
        aria-checked={device?.led_on === true}
        aria-label="Toggle status LED"
        onclick={toggleLed}
        disabled={disabled || ledPending}
      >
        <span class="mini-knob"></span>
      </button>
    </div>
  </div>

  <div class="row">
    <span class="row-label">Reboot device</span>
    <button class="btn sm" onclick={() => (rebootConfirmOpen = true)} disabled={disabled}>
      Reboot
    </button>
  </div>

  <div class="row">
    <span class="row-label">Sync device clock</span>
    <button class="btn sm" onclick={syncTime} disabled={disabled || syncTimePending}>
      {syncTimePending ? 'Syncing…' : 'Sync'}
    </button>
  </div>

  <div class="row">
    <span class="row-label">Reset energy stats</span>
    <button class="btn btn-danger sm" onclick={() => (resetConfirmOpen = true)} disabled={disabled}>
      Reset
    </button>
  </div>
</section>

<ConfirmModal
  open={rebootConfirmOpen}
  title="Reboot {device?.alias ?? 'this device'}?"
  body="The plug will restart and drop off the network for about 10 seconds. Anything plugged into it stays powered as it is now."
  confirmLabel="Reboot"
  cancelLabel="Cancel"
  danger={true}
  pending={rebootPending}
  onconfirm={reboot}
  oncancel={() => (rebootConfirmOpen = false)}
/>

<ConfirmModal
  open={resetConfirmOpen}
  title="Reset energy statistics?"
  body="This permanently clears the plug's on-device daily and monthly energy totals. Local history readings are not affected."
  confirmLabel="Reset"
  cancelLabel="Cancel"
  danger={true}
  pending={resetPending}
  onconfirm={resetEnergy}
  oncancel={() => (resetConfirmOpen = false)}
/>

<style>
  .settings {
    padding: 1.5rem;
  }

  .section-title {
    font-family: var(--font-condensed);
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }

  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.65rem 0;
    border-bottom: 1px solid var(--hairline);
  }

  .row:last-child {
    border-bottom: none;
  }

  .row-label {
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-muted);
  }

  .row-control {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .row-value {
    font-family: var(--font-mono);
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--ink);
  }

  .btn.sm {
    padding: 0.4em 0.85em;
    font-size: 0.8125rem;
  }

  .alias-form {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .alias-form input {
    background: var(--recess);
    border: 1px solid var(--hairline);
    border-radius: var(--radius-sm);
    padding: 0.4em 0.6em;
    color: var(--ink);
    font-family: var(--font-mono);
    font-size: 0.875rem;
    width: 140px;
  }

  /* Panel switch, matching the main power switch language. */
  .mini-toggle {
    position: relative;
    width: 44px;
    height: 24px;
    border-radius: var(--radius-sm);
    background: var(--recess);
    border: 1px solid var(--hairline);
    cursor: pointer;
    padding: 2px;
    display: flex;
    align-items: center;
  }

  .mini-toggle:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .mini-knob {
    position: relative;
    width: 18px;
    height: 100%;
    border-radius: 1px;
    background: var(--ink-muted);
    transition: transform 0.15s var(--ease);
  }

  .mini-toggle.on .mini-knob {
    background: var(--signal);
    transform: translateX(18px);
  }
</style>
