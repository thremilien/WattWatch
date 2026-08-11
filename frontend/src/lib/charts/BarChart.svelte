<script>
  // Simple bar chart for daily/monthly on-device energy stats.
  // Expects entries: [{ label, value }].
  import { fmtKwh } from '../format.js';

  let { entries = [], unit = 'kWh', height = 200 } = $props();

  const width = 600;
  const padTop = 12;
  const padBottom = 22;
  const barGap = 4;

  let plotHeight = $derived(height - padTop - padBottom);

  let maxValue = $derived.by(() => {
    if (!entries.length) return 1;
    const max = Math.max(...entries.map((e) => e.value ?? 0));
    return max > 0 ? max : 1;
  });

  let barWidth = $derived(entries.length ? width / entries.length - barGap : 0);

  let hoverIndex = $state(null);
</script>

<div class="chart-wrap">
  {#if !entries.length}
    <div class="empty" style="height: {height}px">No data for this period yet.</div>
  {:else}
    <svg
      class="chart"
      viewBox="0 0 {width} {height}"
      preserveAspectRatio="none"
      role="img"
      aria-label="Energy usage by period"
    >
      {#each entries as entry, i (entry.label)}
        {@const barHeight = ((entry.value ?? 0) / maxValue) * plotHeight}
        {@const x = i * (width / entries.length) + barGap / 2}
        {@const y = padTop + plotHeight - barHeight}
        <rect
          {x}
          {y}
          width={barWidth}
          height={Math.max(barHeight, entry.value ? 2 : 0)}
          fill={entry.current ? 'var(--signal)' : 'var(--ink)'}
          fill-opacity={entry.current ? '1' : hoverIndex === i ? '0.85' : '0.7'}
          onmouseenter={() => (hoverIndex = i)}
          onmouseleave={() => (hoverIndex = null)}
          role="presentation"
        >
          <title>{entry.label}: {fmtKwh(entry.value)} {unit}</title>
        </rect>
        {#if entries.length <= 12 || i % Math.ceil(entries.length / 12) === 0}
          <text
            x={x + barWidth / 2}
            y={height - 6}
            text-anchor="middle"
            class="axis-label"
          >
            {entry.label}
          </text>
        {/if}
      {/each}
    </svg>

    {#if hoverIndex !== null}
      <div class="readout">
        <span class="readout-label">{entries[hoverIndex].label}</span>
        <span class="readout-value tabular">{fmtKwh(entries[hoverIndex].value)} {unit}</span>
      </div>
    {/if}
  {/if}
</div>

<style>
  .chart-wrap {
    width: 100%;
  }

  .chart {
    display: block;
    width: 100%;
  }

  .chart rect {
    transition: fill-opacity 0.1s;
    cursor: pointer;
  }

  .axis-label {
    fill: var(--ink-muted);
    font-size: 10px;
    font-family: var(--font-mono);
  }

  .empty {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--ink-muted);
    font-size: 0.875rem;
  }

  .readout {
    display: flex;
    justify-content: space-between;
    padding-top: 0.5rem;
    border-top: 1px solid var(--hairline);
    margin-top: 0.5rem;
    font-size: 0.8125rem;
  }

  .readout-label {
    color: var(--ink-muted);
    font-family: var(--font-mono);
  }

  .readout-value {
    color: var(--signal);
    font-weight: 500;
    font-family: var(--font-mono);
  }
</style>
