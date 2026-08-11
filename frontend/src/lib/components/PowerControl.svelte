<script>
  // Prominent on/off toggle. Turning off requires confirmation;
  // turning on is immediate.
  import { api, ApiError } from '../api.js';
  import { deviceState, toasts } from '../state.svelte.js';
  import { DASH } from '../format.js';
  import ConfirmModal from './ConfirmModal.svelte';

  let pending = $state(false);
  let confirmOpen = $state(false);

  let device = $derived(deviceState.device);
  let isOn = $derived(device?.is_on ?? null);
  let disabled = $derived(pending || !deviceState.reachable || !device);

  async function setPower(on) {
    pending = true;
    try {
      const updated = await api.setPower(on);
      deviceState.applyDeviceOnly(updated);
      toasts.push(on ? 'Turned on.' : 'Turned off.', 'success', 2500);
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 502
          ? "Can't reach the plug right now. Try again shortly."
          : err instanceof ApiError
            ? err.message
            : 'Something went wrong. Try again.';
      toasts.push(msg, 'error');
    } finally {
      pending = false;
      confirmOpen = false;
    }
  }

  function handleToggle() {
    if (disabled) return;
    if (isOn) {
      confirmOpen = true;
    } else {
      setPower(true);
    }
  }
</script>

<section class="power card">
  <div class="info">
    <span class="label">Power</span>
    <span class="state tabular" class:on={isOn === true}>
      <span class="lamp" class:lit={isOn === true} aria-hidden="true"></span>
      {isOn === null ? DASH : isOn ? 'On' : 'Off'}
    </span>
  </div>

  <button
    class="switch"
    class:on={isOn === true}
    role="switch"
    aria-checked={isOn === true}
    aria-label="Toggle power"
    onclick={handleToggle}
    disabled={disabled}
  >
    <span class="switch-track"></span>
  </button>
</section>

<ConfirmModal
  open={confirmOpen}
  title="Turn off {device?.alias ?? 'this device'}?"
  body="The connected device will lose power immediately."
  confirmLabel="Turn off"
  cancelLabel="Cancel"
  danger={true}
  pending={pending}
  onconfirm={() => setPower(false)}
  oncancel={() => (confirmOpen = false)}
/>

<style>
  .power {
    padding: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .info {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .state {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: var(--font-condensed);
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--ink-muted);
    letter-spacing: -0.01em;
  }

  .state.on {
    color: var(--ink);
  }

  .lamp {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--ink-muted);
    opacity: 0.4;
    flex-shrink: 0;
  }

  .lamp.lit {
    background: var(--signal);
    opacity: 1;
  }

  /* Panel switch: a flat rectangular rocker, not an iOS-style pill. */
  .switch {
    position: relative;
    width: 64px;
    height: 34px;
    border-radius: var(--radius-sm);
    background: var(--recess);
    border: 1px solid var(--hairline);
    cursor: pointer;
    padding: 3px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
  }

  .switch:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .switch-track {
    position: relative;
    width: 26px;
    height: 100%;
    border-radius: 1px;
    background: var(--ink);
    transition: transform 0.15s var(--ease);
  }

  .switch.on .switch-track {
    background: var(--signal);
    transform: translateX(28px);
  }
</style>
