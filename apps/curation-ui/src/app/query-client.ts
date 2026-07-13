import { QueryClient } from '@tanstack/react-query';

import { ApiError } from '@/shared/api/http';

/**
 * Shared Query client. Don't retry auth/validation/conflict errors — retrying a 401/403/409/422
 * just wastes the per-principal rate budget; retry only transient failures, twice.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status < 500 && error.status !== 429) return false;
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
});
