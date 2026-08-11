<script>
  // Root component: shows the login screen when unauthenticated, otherwise
  // the dashboard. Owns the auth check and starts/stops device polling.
  import { auth, deviceState } from './lib/state.svelte.js';
  import LoginScreen from './lib/components/LoginScreen.svelte';
  import Header from './lib/components/Header.svelte';
  import Meter from './lib/components/Meter.svelte';
  import PowerControl from './lib/components/PowerControl.svelte';
  import DeviceInfo from './lib/components/DeviceInfo.svelte';
  import SettingsCard from './lib/components/SettingsCard.svelte';
  import HistorySection from './lib/components/HistorySection.svelte';
  import DeviceStats from './lib/components/DeviceStats.svelte';
  import ToastStack from './lib/components/ToastStack.svelte';

  $effect(() => {
    auth.check();
  });

  $effect(() => {
    if (auth.isAuthenticated) {
      deviceState.startPolling();
      return () => deviceState.stopPolling();
    } else {
      deviceState.reset();
    }
  });
</script>

{#if !auth.checked}
  <div class="boot" aria-hidden="true"></div>
{:else if !auth.isAuthenticated}
  <LoginScreen />
{:else}
  <Header />
  <main class="dashboard">
    <Meter />
    <div class="grid">
      <PowerControl />
      <DeviceInfo />
      <SettingsCard />
      <HistorySection />
      <DeviceStats />
    </div>
  </main>
{/if}

<ToastStack />

<style>
  .boot {
    min-height: 100vh;
  }

  .dashboard {
    flex: 1;
    width: 100%;
    max-width: var(--max-width);
    margin: 0 auto;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .grid :global(.power) {
    grid-column: 1 / -1;
  }

  @media (max-width: 720px) {
    .grid {
      grid-template-columns: 1fr;
    }
    .dashboard {
      padding: 1rem;
    }
  }
</style>
