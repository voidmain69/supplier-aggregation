/**
 * Runtime configuration, read once from Vite env vars.
 *
 * Only `VITE_*` values are exposed to the browser — never put a secret here (curation-ui-plan
 * §6.7). The API base URL points at the api-gateway, the single ingress the UI is allowed to
 * call; the UI never talks to a service directly.
 */

export interface AppConfig {
  /** api-gateway base URL, e.g. `http://localhost:8080`. */
  apiBaseUrl: string;
  /** Optional Sentry/GlitchTip DSN for error monitoring; empty disables reporting. */
  sentryDsn: string;
  /** Deploy environment label surfaced in error reports. */
  env: string;
}

function required(name: string, value: string | undefined, fallback: string): string {
  const v = value ?? fallback;
  if (!v) throw new Error(`Missing required env var ${name}`);
  return v.replace(/\/$/, '');
}

export const config: AppConfig = {
  apiBaseUrl: required(
    'VITE_API_BASE_URL',
    import.meta.env.VITE_API_BASE_URL,
    'http://localhost:8080',
  ),
  sentryDsn: import.meta.env.VITE_SENTRY_DSN ?? '',
  env: import.meta.env.MODE,
};
