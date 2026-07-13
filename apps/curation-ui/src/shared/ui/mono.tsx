import { t } from '@/shared/config/i18n';

import { cn } from './cn';

/** Monospace identifier (GTIN, articul, ULID) with click-to-copy. Falls back to an em dash. */
export function Mono({ value, className }: { value: string | null; className?: string }) {
  if (!value) return <span className="text-muted">{t.common.none}</span>;
  return (
    <button
      type="button"
      title={value}
      onClick={() => {
        void navigator.clipboard.writeText(value);
      }}
      className={cn('cursor-pointer font-mono text-xs hover:underline', className)}
    >
      {value}
    </button>
  );
}
