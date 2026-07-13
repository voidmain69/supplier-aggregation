/**
 * Bearer-token holder for the MVP (pre-OIDC).
 *
 * Lives in `shared` because the HTTP core needs it and `shared` may not import `features`. The
 * token is kept only in `sessionStorage` (curation-ui-plan §6.1): it dies with the tab and is
 * never written to `localStorage`, a cookie, the URL, or any log. When OIDC lands, this becomes
 * a silent-refresh access-token holder and nothing else changes.
 */

const KEY = 'curation-ui.token';

const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

export const tokenStore = {
  get(): string | null {
    return sessionStorage.getItem(KEY);
  },
  set(token: string): void {
    sessionStorage.setItem(KEY, token);
    emit();
  },
  clear(): void {
    sessionStorage.removeItem(KEY);
    emit();
  },
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
};
