<script>
  import { fly } from 'svelte/transition';
  import { toasts } from '../state.svelte.js';
</script>

<div class="stack" role="status" aria-live="polite">
  {#each toasts.items as toast (toast.id)}
    <div class="toast {toast.kind}" transition:fly={{ y: 12, duration: 200 }}>
      <span>{toast.message}</span>
      <button class="dismiss" onclick={() => toasts.dismiss(toast.id)} aria-label="Dismiss">
        &times;
      </button>
    </div>
  {/each}
</div>

<style>
  .stack {
    position: fixed;
    bottom: 1.25rem;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    z-index: 200;
    width: min(92vw, 420px);
  }

  .toast {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    background: var(--recess);
    border: 1px solid var(--hairline);
    border-radius: var(--radius-md);
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
    color: var(--ink);
  }

  .toast.error {
    border-color: color-mix(in srgb, var(--signal) 45%, transparent);
  }

  .toast.success {
    border-color: color-mix(in srgb, var(--ink) 30%, transparent);
  }

  .dismiss {
    background: none;
    border: none;
    color: var(--ink-muted);
    font-size: 1.1rem;
    line-height: 1;
    cursor: pointer;
    padding: 0;
  }

  .dismiss:hover {
    color: var(--ink);
  }
</style>
