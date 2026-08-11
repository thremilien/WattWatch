<script>
  // Full-viewport login screen. Shown whenever the app is not authenticated.
  import { auth } from '../state.svelte.js';
  import { ApiError } from '../api.js';

  let username = $state('');
  let password = $state('');
  let pending = $state(false);
  let error = $state(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (pending) return;
    error = null;
    pending = true;
    try {
      await auth.login(username, password);
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Something went wrong. Try again.';
    } finally {
      pending = false;
    }
  }
</script>

<div class="login-screen">
  <form class="login-card card" onsubmit={handleSubmit}>
    <div class="brand">
      <span class="mark" aria-hidden="true"></span>
      <h1>WattWatch</h1>
    </div>
    <p class="subtitle">Sign in to view and control your plug.</p>

    <label class="field">
      <span class="label">Username</span>
      <input
        type="text"
        name="username"
        autocomplete="username"
        bind:value={username}
        disabled={pending}
        required
      />
    </label>

    <label class="field">
      <span class="label">Password</span>
      <input
        type="password"
        name="password"
        autocomplete="current-password"
        bind:value={password}
        disabled={pending}
        required
      />
    </label>

    {#if error}
      <p class="error" role="alert">{error}</p>
    {/if}

    <button type="submit" class="btn btn-primary submit" disabled={pending}>
      {pending ? 'Signing in…' : 'Sign in'}
    </button>
  </form>
</div>

<style>
  .login-screen {
    min-height: 100vh;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
  }

  .login-card {
    width: 100%;
    max-width: 360px;
    padding: 2.25rem 2rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    background: var(--recess);
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .mark {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--signal);
    flex-shrink: 0;
  }

  h1 {
    font-family: var(--font-condensed);
    font-size: 1.375rem;
    font-weight: 600;
    letter-spacing: -0.01em;
  }

  .subtitle {
    color: var(--ink-muted);
    font-size: 0.875rem;
    margin-bottom: 0.5rem;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .field .label {
    margin-bottom: 0;
  }

  input {
    background: var(--panel);
    border: 1px solid var(--hairline);
    border-radius: var(--radius-sm);
    padding: 0.65rem 0.75rem;
    color: var(--ink);
    font-family: var(--font-mono);
    font-size: 0.9375rem;
  }

  input:focus-visible {
    outline: 2px solid var(--signal);
    outline-offset: 1px;
  }

  .error {
    color: var(--signal);
    font-family: var(--font-mono);
    font-size: 0.8125rem;
    background: color-mix(in srgb, var(--signal) 8%, var(--panel));
    border: 1px solid color-mix(in srgb, var(--signal) 30%, transparent);
    border-radius: var(--radius-sm);
    padding: 0.5rem 0.65rem;
  }

  .submit {
    margin-top: 0.5rem;
    padding: 0.75rem 1rem;
    font-size: 0.9375rem;
  }
</style>
