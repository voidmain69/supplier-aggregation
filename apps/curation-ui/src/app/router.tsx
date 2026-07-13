import { createRootRoute, createRoute, createRouter, redirect } from '@tanstack/react-router';

import { tokenStore } from '@/shared/api/token';
import { CanonicalDetailPage } from '@/pages/canonical/canonical-detail-page';
import { CanonicalListPage } from '@/pages/canonical/canonical-list-page';
import { LoginPage } from '@/pages/login/login-page';
import { QueuePage } from '@/pages/queue/queue-page';
import { ReviewPage } from '@/pages/review/review-page';

import { RootLayout } from './root-layout';

/** Route guard: no session token → send to login (curation-ui-plan §3.1). */
function requireAuth(): void {
  // `throw redirect(...)` is TanStack Router's documented control-flow idiom, not an error throw.
  // eslint-disable-next-line @typescript-eslint/only-throw-error
  if (tokenStore.get() === null) throw redirect({ to: '/login' });
}

const rootRoute = createRootRoute({ component: RootLayout });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  beforeLoad: () => {
    // eslint-disable-next-line @typescript-eslint/only-throw-error
    throw redirect({ to: '/queue' });
  },
});

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
});

const queueRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/queue',
  beforeLoad: requireAuth,
  component: QueuePage,
});

const reviewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/queue/$supplierProductId',
  beforeLoad: requireAuth,
  // The candidate canonical id travels in the URL so a refreshed review still resolves it.
  validateSearch: (search: Record<string, unknown>): { candidate?: string } => ({
    candidate: typeof search.candidate === 'string' ? search.candidate : undefined,
  }),
  component: ReviewPage,
});

const canonicalListRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/canonical',
  beforeLoad: requireAuth,
  component: CanonicalListPage,
});

const canonicalDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/canonical/$canonicalId',
  beforeLoad: requireAuth,
  component: CanonicalDetailPage,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  queueRoute,
  reviewRoute,
  canonicalListRoute,
  canonicalDetailRoute,
]);

export const router = createRouter({ routeTree, defaultPreload: 'intent' });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
