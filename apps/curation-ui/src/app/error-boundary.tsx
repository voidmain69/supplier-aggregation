import { Component, type ErrorInfo, type ReactNode } from 'react';

import { t } from '@/shared/config/i18n';

/**
 * Top-level crash guard. On error it renders a recoverable fallback and forwards to the error
 * monitor (curation-ui-plan §7). Sentry/GlitchTip wiring hooks in at `report` when configured.
 */
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ui_crash', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-8 text-center">
          <p className="text-lg font-semibold text-danger">{t.common.errorTitle}</p>
          <p className="max-w-md text-sm text-muted">{this.state.error.message}</p>
          <button
            type="button"
            onClick={() => {
              window.location.reload();
            }}
            className="rounded-md bg-accent px-4 py-2 text-sm text-accent-fg"
          >
            {t.common.retry}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
