import type { ReactNode } from 'react';

import { cn } from './cn';

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section className={cn('rounded-md border border-border bg-surface', className)}>
      {children}
    </section>
  );
}

export function CardHeader({ children }: { children: ReactNode }) {
  return (
    <header className="border-b border-border px-4 py-2 text-xs font-semibold tracking-wide text-muted uppercase">
      {children}
    </header>
  );
}

export function CardBody({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('p-4', className)}>{children}</div>;
}
