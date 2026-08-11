<script>
  // Simple bar chart for daily/monthly on-device energy stats.
  // Expects entries: [{ label, value, current, projected, cost, projectedCost }].
  // `projected`/`projectedCost` are forecasted end-of-period totals, set only
  // on the still-in-progress entry (today / this month), and rendered as a
  // hatched zone above the actual bar so a partial period reads at its true
  // expected height. `cost`/`projectedCost` are optional (only present once a
  // €/kWh price is set) and shown alongside kWh on hover, not as a second chart.
  import { fmtKwh, fmtEuro, DASH } from '../format.js';

  let { entries = [], unit = 'kWh', height = 200 } = $props();

  const width = 600;
  const padTop = 12;
  const padBottom = 22;
  const barGap = 4;
  // Unique per instance: two BarCharts (daily + monthly) share one DOM, and
  // SVG pattern ids are global regardless of which <svg> defines them.
  const hatchId = `barchart-hatch-${Math.random().toString(36).slice(2)}`;

  let plotHeight = $derived(height - padTop - padBottom);

  let maxValue = $derived.by(() => {
    if (!entries.length) return 1;
    const max = Math.max(...entries.map((e) => Math.max(e.value ?? 0, e.projected ?? 0)));
    return max > 0 ? max : 1;
  });

  let barWidth = $derived(entries.length ? width / entries.length - barGap : 0);
  let colWidth = $derived(entries.length ? width / entries.length : 0);

  let hoverIndex = $state(null);
  let hovered = $derived(hoverIndex !== null ? entries[hoverIndex] : null);
  let hoveredHasProjection = $derived(
    hovered ? (hovered.projected ?? 0) > (hovered.value ?? 0) : false
  );
  // Reserve the cost row whenever any entry carries cost data, not just the
  // hovered one, so a price being set/unset is the only thing that resizes
  // the readout — hovering never does.
  let hasCostData = $derived(entries.some((e) => e.cost != null));
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
      <defs>
        <pattern
          id={hatchId}
          width="5"
          height="5"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="5" stroke="var(--signal)" stroke-width="1.5" />
        </pattern>
      </defs>
      {#each entries as entry, i (entry.label)}
        {@const barHeight = ((entry.value ?? 0) / maxValue) * plotHeight}
        {@const hasProjection = (entry.projected ?? 0) > (entry.value ?? 0)}
        {@const projectedHeight = hasProjection ? (entry.projected / maxValue) * plotHeight : 0}
        {@const colX = i * (width / entries.length)}
        {@const x = colX + barGap / 2}
        {@const y = padTop + plotHeight - barHeight}
        {@const projectedY = padTop + plotHeight - projectedHeight}
        <g
          onmouseenter={() => (hoverIndex = i)}
          onmouseleave={() => (hoverIndex = null)}
          role="presentation"
        >
          <!-- Invisible full-height hit area: a tiny bar (e.g. near-zero
               today's reading) would otherwise be nearly impossible to
               hover precisely. -->
          <rect x={colX} y={padTop} width={colWidth} height={plotHeight} fill="transparent" />
          {#if hasProjection}
            <rect
              x={x}
              y={projectedY}
              width={barWidth}
              height={projectedHeight - barHeight}
              fill="url(#{hatchId})"
              fill-opacity={hoverIndex === i ? '0.55' : '0.4'}
            />
            <line
              x1={x}
              x2={x + barWidth}
              y1={projectedY}
              y2={projectedY}
              stroke="var(--signal)"
              stroke-width="1"
              stroke-dasharray="2 2"
            />
          {/if}
          <rect
            {x}
            {y}
            width={barWidth}
            height={Math.max(barHeight, entry.value ? 2 : 0)}
            fill={entry.current ? 'var(--signal)' : 'var(--ink)'}
            fill-opacity={entry.current ? '1' : hoverIndex === i ? '0.85' : '0.7'}
          >
            <title
              >{entry.label}: {fmtKwh(entry.value)} {unit}{hasProjection
                ? ` (projected ${fmtKwh(entry.projected)} ${unit})`
                : ''}{entry.cost != null
                ? ` · ${fmtEuro(entry.cost)} €${
                    hasProjection && entry.projectedCost != null
                      ? ` (projected ${fmtEuro(entry.projectedCost)} €)`
                      : ''
                  }`
                : ''}</title
            >
          </rect>
        </g>
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

    <!-- Always rendered, at fixed height, so hovering never resizes the
         card — a resize under the cursor was flipping mouseenter/mouseleave
         in a loop and made small bars flicker. -->
    <div class="readout">
      <span class="readout-label">{hovered ? hovered.label : DASH}</span>
      <div class="readout-values">
        <span class="readout-value tabular" class:idle={!hovered}>
          {hovered ? fmtKwh(hovered.value) : DASH} {unit}
          {#if hovered && hoveredHasProjection}
            <span class="readout-projected">→ ~{fmtKwh(hovered.projected)} {unit} projected</span>
          {/if}
        </span>
        {#if hasCostData}
          <span class="readout-value readout-cost tabular">
            {hovered && hovered.cost != null ? fmtEuro(hovered.cost) : DASH} €
            {#if hovered && hoveredHasProjection && hovered.projectedCost != null}
              <span class="readout-projected">→ ~{fmtEuro(hovered.projectedCost)} € projected</span>
            {/if}
          </span>
        {/if}
      </div>
    </div>
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
    align-items: flex-start;
    padding-top: 0.5rem;
    border-top: 1px solid var(--hairline);
    margin-top: 0.5rem;
    font-size: 0.8125rem;
  }

  .readout-label {
    color: var(--ink-muted);
    font-family: var(--font-mono);
  }

  .readout-values {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.25rem;
  }

  .readout-value {
    color: var(--signal);
    font-weight: 500;
    font-family: var(--font-mono);
  }

  .readout-value.idle {
    color: var(--ink-muted);
    font-weight: 400;
  }

  .readout-cost {
    color: var(--ink-muted);
    font-size: 0.75rem;
  }

  .readout-projected {
    color: var(--ink-muted);
    font-weight: 400;
    margin-left: 0.5em;
  }
</style>
