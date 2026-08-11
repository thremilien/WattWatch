<script>
  import { deviceState } from '../state.svelte.js';
  import { humanizeUptime, fmtDate, fmtClockTime, DASH } from '../format.js';
  import SignalBars from './SignalBars.svelte';

  let device = $derived(deviceState.device);

  // Positive: the device's own clock is ahead of this browser's. Negative:
  // behind. Comparing epoch instants sidesteps any timezone label mismatch
  // between the two — see wattwatch/devices/kasa.py's Time module usage.
  let clockDriftSeconds = $derived.by(() => {
    if (!device?.device_time) return null;
    return (new Date(device.device_time).getTime() - Date.now()) / 1000;
  });
  let clockMismatch = $derived(clockDriftSeconds !== null && Math.abs(clockDriftSeconds) >= 300);
</script>

<section class="device-info card">
  <h2 class="section-title">Device</h2>

  {#if !device}
    <p class="empty">No device information yet.</p>
  {:else}
    <dl class="rows">
      <div class="row">
        <dt>Alias</dt>
        <dd>{device.alias ?? DASH}</dd>
      </div>
      <div class="row">
        <dt>Model</dt>
        <dd>{device.model ?? DASH}</dd>
      </div>
      <div class="row">
        <dt>MAC</dt>
        <dd>{device.mac ?? DASH}</dd>
      </div>
      <div class="row">
        <dt>Hardware</dt>
        <dd>{device.hw_version ?? DASH}</dd>
      </div>
      <div class="row">
        <dt>Firmware</dt>
        <dd class="truncate">{device.fw_version ?? DASH}</dd>
      </div>
      <div class="row">
        <dt>Signal</dt>
        <dd class="signal-cell">
          <SignalBars rssi={device.rssi} />
          <span class="rssi-value">{device.rssi ?? DASH}{device.rssi !== null && device.rssi !== undefined ? ' dBm' : ''}</span>
        </dd>
      </div>
      <div class="row">
        <dt>Uptime</dt>
        <dd>{humanizeUptime(device.uptime_seconds)}</dd>
      </div>
      <div class="row">
        <dt>Host</dt>
        <dd>{device.host ?? DASH}</dd>
      </div>
      <div class="row">
        <dt>Device clock</dt>
        <dd class="clock-cell">
          <span class:mismatch={clockMismatch}>
            {device.device_time
              ? `${fmtDate(device.device_time)} ${fmtClockTime(device.device_time)}`
              : DASH}
          </span>
          {#if clockMismatch}
            <span class="drift-note"
              >{clockDriftSeconds > 0 ? 'ahead' : 'behind'} by {humanizeUptime(
                Math.abs(clockDriftSeconds)
              )}</span
            >
          {/if}
        </dd>
      </div>
    </dl>
  {/if}
</section>

<style>
  .device-info {
    padding: 1.5rem;
  }

  .section-title {
    font-family: var(--font-condensed);
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }

  .empty {
    color: var(--ink-muted);
    font-size: 0.875rem;
  }

  .rows {
    display: flex;
    flex-direction: column;
    margin: 0;
  }

  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--hairline);
    font-size: 0.875rem;
  }

  .row:last-child {
    border-bottom: none;
  }

  dt {
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-muted);
    flex-shrink: 0;
  }

  dd {
    margin: 0;
    text-align: right;
    font-family: var(--font-mono);
    color: var(--ink);
    font-weight: 500;
    min-width: 0;
  }

  .truncate {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 180px;
  }

  .signal-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .rssi-value {
    color: var(--ink-muted);
    font-size: 0.75rem;
  }

  .clock-cell {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.15rem;
  }

  .mismatch {
    color: var(--signal);
  }

  .drift-note {
    color: var(--ink-muted);
    font-size: 0.75rem;
    font-weight: 400;
  }
</style>
