<script>
  // Simple confirm dialog used for destructive/impactful actions
  // (power off, reboot, reset energy stats).
  import { fade, scale } from 'svelte/transition';

  let {
    open = false,
    title = 'Are you sure?',
    body = '',
    confirmLabel = 'Confirm',
    cancelLabel = 'Cancel',
    danger = true,
    pending = false,
    onconfirm,
    oncancel
  } = $props();

  function handleKeydown(e) {
    if (e.key === 'Escape') oncancel?.();
  }
</script>

<svelte:window onkeydown={open ? handleKeydown : null} />

{#if open}
  <div
    class="overlay"
    role="presentation"
    transition:fade={{ duration: 150 }}
    onclick={() => oncancel?.()}
  >
    <div
      class="dialog card"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      tabindex="-1"
      transition:scale={{ duration: 180, start: 0.96 }}
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
    >
      <h2 id="confirm-title">{title}</h2>
      {#if body}
        <p class="body">{body}</p>
      {/if}
      <div class="actions">
        <button class="btn" onclick={() => oncancel?.()} disabled={pending}>
          {cancelLabel}
        </button>
        <button
          class="btn {danger ? 'btn-danger' : 'btn-primary'}"
          onclick={() => onconfirm?.()}
          disabled={pending}
        >
          {pending ? 'Working…' : confirmLabel}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgb(28 26 23 / 45%);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
    z-index: 100;
  }

  .dialog {
    width: 100%;
    max-width: 380px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    background: var(--panel);
  }

  h2 {
    font-family: var(--font-condensed);
    font-size: 1.15rem;
    font-weight: 600;
  }

  .body {
    color: var(--ink-muted);
    font-size: 0.9rem;
    line-height: 1.5;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
</style>
