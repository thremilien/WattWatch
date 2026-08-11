<script>
  // Renders RSSI (dBm) as a 4-bar signal strength indicator, plus the raw
  // value as a tooltip/aria-label. Typical Wi-Fi RSSI range: -30 (great) to
  // -90 (unusable).
  let { rssi = null } = $props();

  const THRESHOLDS = [-80, -70, -60]; // bar 1, 2, 3 cutoffs; bar 4 is anything better

  let level = $derived.by(() => {
    if (rssi === null || rssi === undefined) return -1;
    if (rssi < THRESHOLDS[0]) return 1;
    if (rssi < THRESHOLDS[1]) return 2;
    if (rssi < THRESHOLDS[2]) return 3;
    return 4;
  });

  let label = $derived(
    rssi === null || rssi === undefined ? 'Signal unknown' : `Signal ${rssi} dBm`
  );
</script>

<span class="signal" role="img" aria-label={label} title={label}>
  {#each [1, 2, 3, 4] as bar (bar)}
    <span class="bar" class:filled={bar <= level} style="--h: {bar * 25}%"></span>
  {/each}
</span>

<style>
  .signal {
    display: inline-flex;
    align-items: flex-end;
    gap: 2px;
    height: 14px;
  }

  .bar {
    width: 3px;
    height: var(--h);
    background: var(--ink);
    opacity: 0.25;
  }

  .bar.filled {
    background: var(--signal);
    opacity: 1;
  }
</style>
