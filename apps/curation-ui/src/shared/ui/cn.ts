import clsx, { type ClassValue } from 'clsx';

/** Conditional className join. Kept trivial; add tailwind-merge only if class conflicts appear. */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}
