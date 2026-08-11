<script>
  // The signature element: a hand-rolled SVG auto-ranging moving-coil
  // wattmeter, styled after a bench instrument face. Replaces the old
  // sparkline-behind-digits hero.
  //
  // Auto-ranging: picks the smallest full-scale range that comfortably
  // contains the current reading, the way a bench multimeter does, with
  // hysteresis so a reading hovering near a boundary doesn't flip the
  // scale back and forth.
  //
  // Needle motion: spring-damped critically-ish-damped integrator driven
  // by requestAnimationFrame, so the needle swings toward the new value
  // and settles with a little overshoot, like a real moving coil.
  import { untrack } from 'svelte';
  import { prefersReducedMotion } from 'svelte/motion';
  import { deviceState } from '../state.svelte.js';
  import { fmtWatts, fmtVolts, fmtAmps, DASH } from '../format.js';

  let live = $derived(deviceState.live);
  let reachable = $derived(deviceState.reachable);
  let powerReading = $derived(
    reachable && live?.power_w !== null && live?.power_w !== undefined ? live.power_w : null
  );

  // --- Auto-ranging with hysteresis ---------------------------------
  const RANGES = [50, 100, 250, 500, 1000, 2000, 3680];
  const HYSTERESIS = 0.1; // 10%

  function smallestRangeFor(value) {
    for (const r of RANGES) {
      if (value <= r) return r;
    }
    return RANGES[RANGES.length - 1];
  }

  let activeRange = $state(RANGES[0]);

  // This can't be a pure $derived because the hysteresis decision depends
  // on the range's own previous value (impure by definition) — it's a
  // small state machine, which is exactly what $effect is for.
  $effect(() => {
    const value = powerReading;
    if (value === null) return; // keep last range when unreachable; needle falls to 0
    untrack(() => {
      const current = activeRange;
      // Step up as soon as the reading exceeds the current range's ceiling
      // (no hysteresis needed going up — the needle would peg otherwise).
      if (value > current) {
        activeRange = smallestRangeFor(value);
        return;
      }
      // Step down only once the reading is comfortably inside a smaller
      // range's ceiling — 10% below it — so a value hovering right at a
      // boundary doesn't flip the scale back and forth.
      const idx = RANGES.indexOf(current);
      if (idx > 0) {
        const below = RANGES[idx - 1];
        if (value <= below * (1 - HYSTERESIS)) {
          activeRange = smallestRangeFor(value);
        }
      }
    });
  });

  let fullScale = $derived(activeRange);
  let isMaxRange = $derived(activeRange === RANGES[RANGES.length - 1]);

  // --- Arc geometry ----------------------------------------------------
  const CX = 150;
  const CY = 162;
  const R = 128;
  const SWEEP_DEG = 220;
  const START_DEG = 270 - SWEEP_DEG / 2; // 160
  const END_DEG = 270 + SWEEP_DEG / 2; // 380

  function polar(cx, cy, r, deg) {
    const rad = (deg * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function angleForFraction(frac) {
    return START_DEG + frac * SWEEP_DEG;
  }

  function arcPath(cx, cy, r, deg1, deg2) {
    const p1 = polar(cx, cy, r, deg1);
    const p2 = polar(cx, cy, r, deg2);
    const large = deg2 - deg1 > 180 ? 1 : 0;
    return `M ${p1.x.toFixed(2)} ${p1.y.toFixed(2)} A ${r} ${r} 0 ${large} 1 ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
  }

  const faceArc = arcPath(CX, CY, R, START_DEG, END_DEG);

  // Major ticks: choose a step that yields 5-6 major divisions.
  function majorStepFor(scale) {
    const steps = { 50: 10, 100: 20, 250: 50, 500: 100, 1000: 200, 2000: 500, 3680: 500 };
    return steps[scale] ?? scale / 5;
  }

  let majorTicks = $derived.by(() => {
    const step = majorStepFor(fullScale);
    const ticks = [];
    for (let v = 0; v <= fullScale + 1e-6; v += step) {
      ticks.push(Math.round(v));
    }
    return ticks;
  });

  let minorTicks = $derived.by(() => {
    const step = majorStepFor(fullScale) / 5;
    const ticks = [];
    for (let v = 0; v <= fullScale + 1e-6; v += step) {
      const rounded = Math.round(v * 100) / 100;
      if (!majorTicks.some((m) => Math.abs(m - rounded) < step / 2)) {
        ticks.push(rounded);
      }
    }
    return ticks;
  });

  // Redline: only meaningful on the top (3680 W / 16 A) range, marking
  // the last ~9% of the scale (3360-3680 W corresponds to ~14.6-16 A).
  const REDLINE_START_FRACTION = 0.913; // ~3360/3680

  // --- Needle physics: spring-damped RAF integrator ---------------------
  // Modeled as a damped harmonic oscillator: angle accelerates toward the
  // target proportional to displacement (spring) and is opposed by a
  // velocity-proportional damping force. Slight underdamping gives the
  // small overshoot-and-settle a real moving-coil meter exhibits.
  const STIFFNESS = 90; // spring constant (rad/s^2 per rad of error)
  const DAMPING = 11.5; // damping coefficient — underdamped for a touch of overshoot

  let needleFraction = $state(0); // 0..1+ position along the sweep
  let needleVelocity = 0;
  let targetFraction = $state(0);
  let rafId = null;
  let lastT = null;

  let reduced = $derived(prefersReducedMotion.current);

  function stepAnimation(t) {
    if (lastT === null) lastT = t;
    let dt = (t - lastT) / 1000;
    lastT = t;
    dt = Math.min(dt, 0.05); // clamp huge gaps (tab switches)

    const error = targetFraction - needleFraction;
    const accel = STIFFNESS * error - DAMPING * needleVelocity;
    needleVelocity += accel * dt;
    needleFraction += needleVelocity * dt;

    const settled = Math.abs(error) < 0.0006 && Math.abs(needleVelocity) < 0.001;
    if (settled) {
      needleFraction = targetFraction;
      needleVelocity = 0;
      rafId = null;
      lastT = null;
      return;
    }
    rafId = requestAnimationFrame(stepAnimation);
  }

  function ensureAnimating() {
    if (rafId === null) {
      lastT = null;
      rafId = requestAnimationFrame(stepAnimation);
    }
  }

  // Recompute the target whenever the reading or the active range changes,
  // then (re)start the RAF loop so the needle animates toward it. This is
  // an imperative rAF-driven animation loop (like the canvas example in
  // the Svelte docs), not a derivation, so it belongs in $effect.
  $effect(() => {
    const value = powerReading;
    const scale = fullScale;
    untrack(() => {
      targetFraction = value === null ? 0 : Math.max(0, Math.min(1.06, value / scale));
      if (reduced) {
        needleFraction = targetFraction;
        needleVelocity = 0;
      } else {
        ensureAnimating();
      }
    });
  });

  $effect(() => {
    return () => {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
        lastT = null;
      }
    };
  });

  let needleAngle = $derived(angleForFraction(Math.max(0, Math.min(1.08, needleFraction))));
  let needleTip = $derived(polar(CX, CY, R - 14, needleAngle));
  let needleTail = $derived(polar(CX, CY, 22, needleAngle + 180));

  let desaturated = $derived(!reachable);

  let displayWatts = $derived(powerReading === null ? DASH : fmtWatts(powerReading));
  let displayVolts = $derived(live?.voltage_v ?? null);
  let displayAmps = $derived(live?.current_a ?? null);
</script>

<section class="meter card" class:desaturated aria-label="Live power meter">
  <svg
    class="face"
    viewBox="0 0 300 210"
    role="img"
    aria-label={powerReading === null ? 'Power unavailable' : `${displayWatts} watts`}
  >
    <path class="face-arc" d={faceArc} />

    {#if isMaxRange}
      {@const redStart = angleForFraction(REDLINE_START_FRACTION)}
      {@const redPath = arcPath(CX, CY, R, redStart, END_DEG)}
      <path class="redline" d={redPath} />
    {/if}

    {#each minorTicks as v (v)}
      {@const a = angleForFraction(v / fullScale)}
      {@const p1 = polar(CX, CY, R, a)}
      {@const p2 = polar(CX, CY, R - 7, a)}
      <line class="tick minor" x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} />
    {/each}

    {#each majorTicks as v (v)}
      {@const a = angleForFraction(v / fullScale)}
      {@const p1 = polar(CX, CY, R, a)}
      {@const p2 = polar(CX, CY, R - 12, a)}
      {@const labelPos = polar(CX, CY, R - 26, a)}
      <line class="tick major" x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} />
      <text class="tick-label" x={labelPos.x} y={labelPos.y} text-anchor="middle" dominant-baseline="middle">
        {v}
      </text>
    {/each}

    {#if isMaxRange}
      <text class="max-marking" x={CX} y={CY - 4} text-anchor="middle">16A MAX</text>
    {/if}

    <line
      class="needle"
      x1={needleTail.x}
      y1={needleTail.y}
      x2={needleTip.x}
      y2={needleTip.y}
    />
    <circle class="pivot" cx={CX} cy={CY} r="6" />
  </svg>

  <div class="range-label">RANGE {fullScale} W</div>

  <div class="readout">
    <div class="watts">
      <span class="value">{displayWatts}</span>
      <span class="unit">W</span>
    </div>
    <div class="secondary">
      <span class="volts">{displayVolts === null ? DASH : fmtVolts(displayVolts)} V</span>
      <span class="amps">{displayAmps === null ? DASH : fmtAmps(displayAmps)} A</span>
    </div>
  </div>

  {#if !reachable}
    <p class="unreachable-note">Needle at zero — device unreachable.</p>
  {/if}
</section>

<style>
  .meter {
    padding: 1.75rem 1.5rem 1.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
  }

  .face {
    width: 100%;
    max-width: 420px;
    height: auto;
    display: block;
  }

  .face-arc {
    fill: none;
    stroke: var(--ink);
    stroke-opacity: 0.18;
    stroke-width: 2;
  }

  .redline {
    fill: none;
    stroke: var(--signal);
    stroke-opacity: 0.55;
    stroke-width: 5;
  }

  .tick {
    stroke: var(--ink);
  }

  .tick.major {
    stroke-width: 1.5;
    stroke-opacity: 0.75;
  }

  .tick.minor {
    stroke-width: 1;
    stroke-opacity: 0.4;
  }

  .tick-label {
    font-family: var(--font-mono);
    font-size: 10px;
    fill: var(--ink);
    fill-opacity: 0.8;
  }

  .max-marking {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.06em;
    fill: var(--signal);
  }

  .needle {
    stroke: var(--signal);
    stroke-width: 2;
    stroke-linecap: round;
  }

  .pivot {
    fill: var(--ink);
  }

  .desaturated .face-arc,
  .desaturated .tick,
  .desaturated .tick-label {
    stroke-opacity: 0.12;
    fill-opacity: 0.35;
  }

  .desaturated .needle {
    stroke: var(--ink-muted);
  }

  .range-label {
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.08em;
    color: var(--ink-muted);
    margin-top: -0.5rem;
  }

  .readout {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.35rem;
    margin-top: 0.5rem;
  }

  .watts {
    display: flex;
    align-items: baseline;
    gap: 0.35rem;
    font-family: var(--font-condensed);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .watts .value {
    font-size: clamp(56px, 9vw, 96px);
    line-height: 1;
    color: var(--ink);
    letter-spacing: -0.01em;
  }

  .watts .unit {
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--ink-muted);
  }

  .secondary {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-family: var(--font-mono);
    font-size: 0.9375rem;
    font-variant-numeric: tabular-nums;
  }

  .volts {
    color: var(--data-blue);
  }

  .amps {
    color: var(--ink);
  }

  .unreachable-note {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--ink-muted);
    margin-top: 0.5rem;
  }

  @media (max-width: 560px) {
    .meter {
      padding: 1.25rem 1rem 1.25rem;
    }
  }
</style>
