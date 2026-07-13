/**
 * Keyboard-first review (curation-ui-plan §9.2): bind single-key actions, ignoring keystrokes
 * typed into inputs so typing in a search box never triggers a decision.
 */

import { useEffect } from 'react';

export type HotkeyMap = Record<string, (event: KeyboardEvent) => void>;

function isEditable(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable;
}

export function useHotkeys(map: HotkeyMap, enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    function onKeyDown(event: KeyboardEvent): void {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (isEditable(event.target)) return;
      const handler = map[event.key];
      if (handler) {
        event.preventDefault();
        handler(event);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [map, enabled]);
}
