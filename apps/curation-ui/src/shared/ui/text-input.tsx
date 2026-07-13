import type { InputHTMLAttributes } from 'react';

import { cn } from './cn';

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

/** Labelled text input for the small curation forms. */
export function TextInput({ label, className, id, ...rest }: TextInputProps) {
  const inputId = id ?? `in-${label}`;
  return (
    <label htmlFor={inputId} className="flex flex-col gap-1 text-sm">
      <span className="text-muted">{label}</span>
      <input
        id={inputId}
        className={cn(
          'h-9 rounded-md border border-border bg-surface px-3 text-sm text-text outline-none focus:border-accent',
          className,
        )}
        {...rest}
      />
    </label>
  );
}
