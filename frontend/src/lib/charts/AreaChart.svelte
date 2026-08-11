<script>
  // Full history line chart with hover tooltip. Hand-rolled SVG,
  // no charting library. Expects points: [{ ts, power_w }].
  // Flat hairline trace on a recessed well — no gradient fill.
  import { fmtWatts, fmtClockTime, fmtDate } from '../format.js';

  let { points = [], height = 260 } = $props();

  const width = 1000;
  const padTop = 16;
  const padBottom = 28;
  const padLeft = 4;
  const padRight = 4;

  let plotWidth = $derived(width - padLeft - padRight);
  let plotHeight = $derived(height - padTop - padBottom);

  let scale = $derived.by(() => {
    if (!points.length) return null;
    const values = points.map((p) => p.power_w).filter((v) => v !== null && v !== undefined);
    if (!values.length) return null;
    const max = Math.max(...values);
    const min = Math.min(0, Math.min(...values));
    const range = max - min || 1;
    return { max: max + range * 0.08, min };
  });

  let coords = $derived.by(() => {
    if (!scale || points.length < 2) return [];
    const n = points.length;
    const span = scale.max - scale.min || 1;
    return points.map((p, i) => {
      const x = padLeft + (i / (n - 1)) * plotWidth;
      const v = p.power_w ?? scale.min;
      const y = padTop + plotHeight - ((v - scale.min) / span) * plotHeight;
      return { x, y, point: p };
    });
  });

  let linePath = $derived(
    coords.length ? coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ') : ''
  );

  // Axis ticks: first, middle, last timestamp
  let ticks = $derived.by(() => {
    if (coords.length < 2) return [];
    const first = coords[0];
    const last = coords[coords.length - 1];
    const mid = coords[Math.floor(coords.length / 2)];
    return [first, mid, last];
  });

  let hoverIndex = $state(null);
  let svgEl = $state(null);

  function handleMove(e) {
    if (!coords.length || !svgEl) return;
    const rect = svgEl.getBoundingClientRect();
    const relX = ((e.clientX - rect.left) / rect.width) * width;
    let closest = 0;
    let bestDist = Infinity;
    for (let i = 0; i < coords.length; i++) {
      const d = Math.abs(coords[i].x - relX);
      if (d < bestDist) {
        bestDist = d;
        closest = i;
      }
    }
    hoverIndex = closest;
  }

  function handleLeave() {
    hoverIndex = null;
  }

  let hovered = $derived(hoverIndex !== null ? coords[hoverIndex] : null);
</script>

<div class="chart-wrap">
  {#if !points.length}
    <div class="empty">No readings yet. The first sample lands within 60 seconds.</div>
  {:else}
    <svg
      bind:this={svgEl}
      class="chart"
      viewBox="0 0 {width} {height}"
      preserveAspectRatio="none"
      onmousemove={handleMove}
      onmouseleave={handleLeave}
      role="img"
      aria-label="Power over time"
    >
      {#if linePath}
        <path d={linePath} fill="none" stroke="var(--signal)" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />
      {/if}

      {#if hovered}
        <line
          x1={hovered.x}
          x2={hovered.x}
          y1={padTop}
          y2={padTop + plotHeight}
          stroke="var(--ink)"
          stroke-opacity="0.3"
          stroke-width="1"
          stroke-dasharray="3,3"
        />
        <circle cx={hovered.x} cy={hovered.y} r="3.5" fill="var(--signal)" stroke="var(--recess)" stroke-width="2" />
      {/if}

      {#each ticks as tick, i (i)}
        <text
          x={i === 0 ? tick.x + 2 : i === ticks.length - 1 ? tick.x - 2 : tick.x}
          y={height - 8}
          text-anchor={i === 0 ? 'start' : i === ticks.length - 1 ? 'end' : 'middle'}
          class="axis-label"
        >
          {fmtClockTime(tick.point.ts)}
        </text>
      {/each}
    </svg>

    {#if hovered}
      <div
        class="tooltip"
        style="left: {(hovered.x / width) * 100}%; top: {(hovered.y / height) * 100}%"
      >
        <div class="tooltip-value">{fmtWatts(hovered.point.power_w)} W</div>
        <div class="tooltip-time">{fmtDate(hovered.point.ts)} · {fmtClockTime(hovered.point.ts)}</div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .chart-wrap {
    position: relative;
    width: 100%;
  }

  .chart {
    display: block;
    width: 100%;
    height: 260px;
    background: var(--recess);
    border-radius: var(--radius-md);
    cursor: crosshair;
  }

  .axis-label {
    fill: var(--ink-muted);
    font-size: 11px;
    font-family: var(--font-mono);
    letter-spacing: 0.04em;
  }

  .empty {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 260px;
    background: var(--recess);
    border-radius: var(--radius-md);
    color: var(--ink-muted);
    font-size: 0.875rem;
    text-align: center;
    padding: 0 2rem;
  }

  .tooltip {
    position: absolute;
    transform: translate(-50%, -120%);
    background: var(--panel);
    border: 1px solid var(--hairline);
    border-radius: var(--radius-sm);
    padding: 0.4rem 0.65rem;
    font-size: 0.8rem;
    pointer-events: none;
    white-space: nowrap;
  }

  .tooltip-value {
    font-weight: 500;
    font-family: var(--font-mono);
    color: var(--signal);
    font-variant-numeric: tabular-nums;
  }

  .tooltip-time {
    color: var(--ink-muted);
    font-family: var(--font-mono);
    font-size: 0.7rem;
  }
</style>
