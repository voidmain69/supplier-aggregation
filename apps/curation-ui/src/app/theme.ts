/**
 * Light/dark theme (curation-ui-plan §9.1). The choice is a UI preference, not a secret, so it
 * may live in localStorage; it seeds from the OS setting on first load. Applying a class on
 * <html> drives the `.dark` token overrides in styles.css.
 */

import { create } from 'zustand';

export type Theme = 'light' | 'dark';

const KEY = 'curation-ui.theme';

function initial(): Theme {
  const saved = localStorage.getItem(KEY);
  if (saved === 'light' || saved === 'dark') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function apply(theme: Theme): void {
  const root = document.documentElement;
  root.classList.remove('light', 'dark');
  root.classList.add(theme);
}

interface ThemeState {
  theme: Theme;
  toggle: () => void;
}

export const useTheme = create<ThemeState>((set, get) => ({
  theme: initial(),
  toggle: () => {
    const next: Theme = get().theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem(KEY, next);
    apply(next);
    set({ theme: next });
  },
}));

/** Call once at boot to apply the persisted/system theme before first paint. */
export function initTheme(): void {
  apply(useTheme.getState().theme);
}
