import { create } from 'zustand';

export type ToastTone = 'success' | 'danger' | 'neutral';

export interface Toast {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastState {
  toasts: Toast[];
  push: (message: string, tone?: ToastTone) => void;
  dismiss: (id: number) => void;
}

let seq = 0;

export const useToasts = create<ToastState>((set) => ({
  toasts: [],
  push: (message, tone = 'neutral') => {
    const id = ++seq;
    set((s) => ({ toasts: [...s.toasts, { id, message, tone }] }));
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((toast) => toast.id !== id) }));
    }, 4000);
  },
  dismiss: (id) => {
    set((s) => ({ toasts: s.toasts.filter((toast) => toast.id !== id) }));
  },
}));

/** Imperative helper for non-component code (mutation callbacks). */
export const toast = {
  success: (m: string) => {
    useToasts.getState().push(m, 'success');
  },
  error: (m: string) => {
    useToasts.getState().push(m, 'danger');
  },
  info: (m: string) => {
    useToasts.getState().push(m, 'neutral');
  },
};
