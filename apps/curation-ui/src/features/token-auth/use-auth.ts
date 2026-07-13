import { useSyncExternalStore } from 'react';

import { tokenStore } from '@/shared/api/token';

/** Reactive view of the current session token. Drives route guards and the sign-out control. */
export function useAuth() {
  const token = useSyncExternalStore(
    (callback) => tokenStore.subscribe(callback),
    () => tokenStore.get(),
    () => null,
  );
  return {
    token,
    isAuthenticated: token !== null,
    signOut: () => {
      tokenStore.clear();
    },
  };
}
