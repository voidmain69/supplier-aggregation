import { useMutation } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useState, type SyntheticEvent } from 'react';

import { getCurationQueue } from '@/shared/api/endpoints';
import { tokenStore } from '@/shared/api/token';
import { t } from '@/shared/config/i18n';
import { Button } from '@/shared/ui/button';
import { Card, CardBody } from '@/shared/ui/card';

/**
 * MVP sign-in: the operator pastes a bearer token (issued out-of-band). We validate it by making
 * the smallest scoped call — one queue item — so a token without `matching:curate` is rejected
 * here rather than on the first real screen. Replaced by an OIDC redirect flow later (§3.1).
 */
export function LoginPage() {
  const navigate = useNavigate();
  const [token, setToken] = useState('');

  const login = useMutation({
    mutationFn: async (candidate: string) => {
      tokenStore.set(candidate);
      try {
        await getCurationQueue({ limit: 1 });
      } catch (error) {
        tokenStore.clear();
        throw error;
      }
    },
    onSuccess: () => void navigate({ to: '/queue' }),
  });

  function onSubmit(event: SyntheticEvent) {
    event.preventDefault();
    if (token.trim()) login.mutate(token.trim());
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg p-4">
      <Card className="w-full max-w-sm">
        <CardBody className="flex flex-col gap-4">
          <div>
            <h1 className="text-lg font-semibold text-text">{t.login.title}</h1>
            <p className="mt-1 text-sm text-muted">{t.login.tokenHint}</p>
          </div>
          <form onSubmit={onSubmit} className="flex flex-col gap-3">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-muted">{t.login.tokenLabel}</span>
              <input
                type="password"
                autoComplete="off"
                value={token}
                onChange={(e) => {
                  setToken(e.target.value);
                }}
                className="h-10 rounded-md border border-border bg-surface px-3 font-mono text-sm text-text outline-none focus:border-accent"
              />
            </label>
            {login.isError ? <p className="text-sm text-danger">{t.login.invalid}</p> : null}
            <Button type="submit" variant="primary" disabled={login.isPending || !token.trim()}>
              {login.isPending ? t.login.checking : t.login.submit}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
