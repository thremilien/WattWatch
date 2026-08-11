<script>
  // On-device energy counters: daily (per day of a month) and monthly
  // (per month of a year), each with prev/next navigation.
  import { api, ApiError } from '../api.js';
  import { deviceState, priceState } from '../state.svelte.js';
  import { fmtKwh, fmtEuro, MONTH_NAMES, DASH } from '../format.js';
  import BarChart from '../charts/BarChart.svelte';

  const now = new Date();

  // Straight-line projection to end-of-period from how much of the period
  // has elapsed. Floored so the very first minute of a day/month doesn't
  // extrapolate to an absurd spike.
  function projectDaily(kwhSoFar) {
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const fraction = Math.max((Date.now() - startOfDay.getTime()) / 86_400_000, 0.01);
    return kwhSoFar / fraction;
  }

  function projectMonthly(kwhSoFar) {
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
    const fraction = Math.max((Date.now() - startOfMonth.getTime()) / (daysInMonth * 86_400_000), 0.01);
    return kwhSoFar / fraction;
  }

  let dailyYear = $state(now.getFullYear());
  let dailyMonth = $state(now.getMonth() + 1); // 1-12
  let dailyEntries = $state([]);
  let dailyLoading = $state(false);
  let dailyError = $state(null);

  let monthlyYear = $state(now.getFullYear());
  let monthlyEntries = $state([]);
  let monthlyLoading = $state(false);
  let monthlyError = $state(null);

  async function loadDaily() {
    dailyLoading = true;
    dailyError = null;
    try {
      const res = await api.energyDaily(dailyYear, dailyMonth);
      const isCurrentMonth = dailyYear === now.getFullYear() && dailyMonth === now.getMonth() + 1;
      const today = now.getDate();
      dailyEntries = (res.entries ?? []).map((e) => {
        const isToday = isCurrentMonth && e.day === today;
        return {
          label: String(e.day),
          value: e.kwh,
          current: isToday,
          projected: isToday ? projectDaily(e.kwh) : null
        };
      });
    } catch (err) {
      dailyError = err instanceof ApiError ? err.message : 'Could not load daily stats.';
    } finally {
      dailyLoading = false;
    }
  }

  async function loadMonthly() {
    monthlyLoading = true;
    monthlyError = null;
    try {
      const res = await api.energyMonthly(monthlyYear);
      const isCurrentYear = monthlyYear === now.getFullYear();
      const thisMonth = now.getMonth() + 1;
      monthlyEntries = (res.entries ?? []).map((e) => {
        const isThisMonth = isCurrentYear && e.month === thisMonth;
        return {
          label: MONTH_NAMES[e.month - 1]?.slice(0, 3) ?? String(e.month),
          value: e.kwh,
          current: isThisMonth,
          projected: isThisMonth ? projectMonthly(e.kwh) : null
        };
      });
    } catch (err) {
      monthlyError = err instanceof ApiError ? err.message : 'Could not load monthly stats.';
    } finally {
      monthlyLoading = false;
    }
  }

  $effect(() => {
    loadDaily();
  });

  $effect(() => {
    loadMonthly();
  });

  function shiftMonth(delta) {
    let m = dailyMonth + delta;
    let y = dailyYear;
    if (m < 1) {
      m = 12;
      y -= 1;
    } else if (m > 12) {
      m = 1;
      y += 1;
    }
    dailyMonth = m;
    dailyYear = y;
  }

  function shiftYear(delta) {
    monthlyYear += delta;
  }

  let live = $derived(deviceState.live);

  let priceInput = $state(priceState.perKwh !== null ? String(priceState.perKwh) : '');

  function commitPrice() {
    const trimmed = priceInput.trim();
    if (trimmed === '') {
      priceState.set(null);
      return;
    }
    const parsed = Number(trimmed);
    if (Number.isFinite(parsed) && parsed >= 0) {
      priceState.set(parsed);
    } else {
      // Reject silently back to the last valid value — no error UI for a
      // single optional local preference field.
      priceInput = priceState.perKwh !== null ? String(priceState.perKwh) : '';
    }
  }

  let cost = $derived.by(() => {
    const price = priceState.perKwh;
    if (price === null || !live) return { today: null, month: null, total: null };
    return {
      today: live.today_kwh != null ? live.today_kwh * price : null,
      month: live.month_kwh != null ? live.month_kwh * price : null,
      total: live.total_kwh != null ? live.total_kwh * price : null
    };
  });
</script>

<section class="stats-grid">
  <div class="totals card">
    <h2 class="section-title">Totals</h2>
    <div class="totals-row">
      <div class="stat">
        <span class="label">Today</span>
        <span class="value tabular">{live ? fmtKwh(live.today_kwh) : DASH} kWh</span>
      </div>
      <div class="stat">
        <span class="label">This month</span>
        <span class="value tabular">{live ? fmtKwh(live.month_kwh) : DASH} kWh</span>
      </div>
      <div class="stat">
        <span class="label">All time</span>
        <span class="value tabular">{live ? fmtKwh(live.total_kwh) : DASH} kWh</span>
      </div>
    </div>
  </div>

  <div class="totals card">
    <div class="header-row">
      <h2 class="section-title">Cost</h2>
      <label class="price-field">
        <span class="label">€ / kWh</span>
        <input
          type="text"
          inputmode="decimal"
          placeholder="0.00"
          bind:value={priceInput}
          onchange={commitPrice}
        />
      </label>
    </div>
    <div class="totals-row">
      <div class="stat">
        <span class="label">Today</span>
        <span class="value tabular">{cost.today !== null ? fmtEuro(cost.today) : DASH} €</span>
      </div>
      <div class="stat">
        <span class="label">This month</span>
        <span class="value tabular">{cost.month !== null ? fmtEuro(cost.month) : DASH} €</span>
      </div>
      <div class="stat">
        <span class="label">All time</span>
        <span class="value tabular">{cost.total !== null ? fmtEuro(cost.total) : DASH} €</span>
      </div>
    </div>
  </div>

  <div class="chart-card card">
    <div class="header-row">
      <h2 class="section-title">Daily usage</h2>
      <div class="nav">
        <button class="nav-btn" onclick={() => shiftMonth(-1)} aria-label="Previous month">‹</button>
        <span class="nav-label">{MONTH_NAMES[dailyMonth - 1]} {dailyYear}</span>
        <button class="nav-btn" onclick={() => shiftMonth(1)} aria-label="Next month">›</button>
      </div>
    </div>
    {#if dailyError}
      <p class="error">{dailyError}</p>
    {:else}
      <BarChart entries={dailyEntries} unit="kWh" />
    {/if}
  </div>

  <div class="chart-card card">
    <div class="header-row">
      <h2 class="section-title">Monthly usage</h2>
      <div class="nav">
        <button class="nav-btn" onclick={() => shiftYear(-1)} aria-label="Previous year">‹</button>
        <span class="nav-label">{monthlyYear}</span>
        <button class="nav-btn" onclick={() => shiftYear(1)} aria-label="Next year">›</button>
      </div>
    </div>
    {#if monthlyError}
      <p class="error">{monthlyError}</p>
    {:else}
      <BarChart entries={monthlyEntries} unit="kWh" />
    {/if}
  </div>
</section>

<style>
  .stats-grid {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .totals {
    grid-column: 1 / -1;
    padding: 1.5rem;
  }

  .totals-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }

  .chart-card {
    padding: 1.5rem;
    min-width: 0;
  }

  .section-title {
    font-family: var(--font-condensed);
    font-size: 1rem;
    font-weight: 600;
  }

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }

  .nav {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .price-field {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .price-field .label {
    white-space: nowrap;
  }

  .price-field input {
    background: var(--recess);
    border: 1px solid var(--hairline);
    border-radius: var(--radius-sm);
    padding: 0.35em 0.5em;
    color: var(--ink);
    font-family: var(--font-mono);
    font-size: 0.8125rem;
    width: 70px;
    text-align: right;
  }

  .nav-btn {
    background: var(--recess);
    border: 1px solid var(--hairline);
    color: var(--ink);
    width: 24px;
    height: 24px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-size: 0.9rem;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .nav-btn:hover {
    background: #cac7bd;
  }

  .nav-label {
    font-family: var(--font-mono);
    font-size: 0.8125rem;
    color: var(--ink-muted);
    min-width: 90px;
    text-align: center;
  }

  .stat {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .stat .value {
    font-family: var(--font-mono);
    font-size: 1.25rem;
    font-weight: 500;
    color: var(--ink);
  }

  .error {
    color: var(--signal);
    font-size: 0.875rem;
    text-align: center;
    padding: 2rem 0;
  }

  @media (max-width: 800px) {
    .stats-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 480px) {
    .totals-row {
      grid-template-columns: 1fr;
      gap: 0.75rem;
    }
  }
</style>
