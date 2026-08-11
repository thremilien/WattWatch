<script>
  // Local history chart (from SQLite) with a range selector and a
  // summary stat strip (avg/min/max/energy).
  import { api, ApiError } from '../api.js';
  import { fmtWatts, fmtKwh, DASH } from '../format.js';
  import AreaChart from '../charts/AreaChart.svelte';

  const RANGES = [
    { label: '1h', hours: 1 },
    { label: '6h', hours: 6 },
    { label: '24h', hours: 24 },
    { label: '7d', hours: 24 * 7 },
    { label: '30d', hours: 24 * 30 }
  ];

  let selectedHours = $state(6);
  let points = $state([]);
  let summary = $state(null);
  let loading = $state(false);
  let loadError = $state(null);

  async function load(hours) {
    loading = true;
    loadError = null;
    try {
      const [historyRes, summaryRes] = await Promise.all([
        api.history(hours),
        api.historySummary(hours)
      ]);
      points = historyRes.points ?? [];
      summary = summaryRes;
    } catch (err) {
      loadError = err instanceof ApiError ? err.message : 'Could not load history.';
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    load(selectedHours);
  });
</script>

<section class="history card">
  <div class="header-row">
    <h2 class="section-title">History</h2>
    <div class="range-selector" role="group" aria-label="Time range">
      {#each RANGES as range (range.hours)}
        <button
          class="range-btn"
          class:active={selectedHours === range.hours}
          onclick={() => (selectedHours = range.hours)}
        >
          {range.label}
        </button>
      {/each}
    </div>
  </div>

  <div class="stat-strip">
    <div class="stat">
      <span class="label">Average</span>
      <span class="value tabular">{summary ? fmtWatts(summary.avg_power_w) : DASH} W</span>
    </div>
    <div class="stat">
      <span class="label">Min</span>
      <span class="value tabular">{summary ? fmtWatts(summary.min_power_w) : DASH} W</span>
    </div>
    <div class="stat">
      <span class="label">Max</span>
      <span class="value tabular">{summary ? fmtWatts(summary.max_power_w) : DASH} W</span>
    </div>
    <div class="stat">
      <span class="label">Energy</span>
      <span class="value tabular">{summary ? fmtKwh(summary.energy_kwh) : DASH} kWh</span>
    </div>
  </div>

  {#if loadError}
    <p class="error">{loadError}</p>
  {:else}
    <AreaChart {points} />
  {/if}
</section>

<style>
  .history {
    padding: 1.5rem;
    grid-column: 1 / -1;
  }

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
  }

  .section-title {
    font-family: var(--font-condensed);
    font-size: 1rem;
    font-weight: 600;
  }

  .range-selector {
    display: flex;
    gap: 0.25rem;
    background: var(--recess);
    border: 1px solid var(--hairline);
    border-radius: var(--radius-sm);
    padding: 3px;
  }

  .range-btn {
    background: none;
    border: none;
    color: var(--ink-muted);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 500;
    padding: 0.35em 0.7em;
    border-radius: 1px;
    cursor: pointer;
    transition: background-color 0.15s var(--ease), color 0.15s var(--ease);
  }

  .range-btn:hover {
    color: var(--ink);
  }

  .range-btn.active {
    background: var(--panel);
    color: var(--signal);
  }

  .stat-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
    margin-bottom: 1.25rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid var(--hairline);
  }

  .stat {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .stat .value {
    font-family: var(--font-mono);
    font-size: 1.125rem;
    font-weight: 500;
    color: var(--ink);
  }

  .error {
    color: var(--signal);
    font-size: 0.875rem;
    padding: 2rem 0;
    text-align: center;
  }

  @media (max-width: 560px) {
    .stat-strip {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
