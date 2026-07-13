import { Link, Outlet } from '@tanstack/react-router';

import { useAuth } from '@/features/token-auth/use-auth';
import { t } from '@/shared/config/i18n';
import { cn } from '@/shared/ui/cn';
import { Toaster } from '@/shared/ui/toaster';

import { useTheme } from './theme';

function NavLink({ to, children }: { to: '/queue' | '/canonical'; children: string }) {
  return (
    <Link
      to={to}
      className="rounded-md px-3 py-1.5 text-sm text-muted hover:bg-surface-2"
      activeProps={{
        className: cn('rounded-md px-3 py-1.5 text-sm font-medium text-text bg-surface-2'),
      }}
    >
      {children}
    </Link>
  );
}

export function RootLayout() {
  const { isAuthenticated, signOut } = useAuth();
  const { theme, toggle } = useTheme();

  return (
    <div className="min-h-screen">
      {isAuthenticated ? (
        <header className="sticky top-0 z-40 flex items-center gap-2 border-b border-border bg-surface px-4 py-2">
          <span className="mr-2 font-semibold text-text">{t.appName}</span>
          <nav className="flex gap-1">
            <NavLink to="/queue">{t.nav.queue}</NavLink>
            <NavLink to="/canonical">{t.nav.canonical}</NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={toggle}
              aria-label="Toggle theme"
              className="rounded-md px-2 py-1.5 text-sm text-muted hover:bg-surface-2"
            >
              {theme === 'dark' ? '☀' : '☾'}
            </button>
            <button
              type="button"
              onClick={signOut}
              className="rounded-md px-3 py-1.5 text-sm text-muted hover:bg-surface-2"
            >
              {t.nav.signOut}
            </button>
          </div>
        </header>
      ) : null}
      <main>
        <Outlet />
      </main>
      <Toaster />
    </div>
  );
}
