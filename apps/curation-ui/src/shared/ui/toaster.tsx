import { cn } from './cn';
import { useToasts, type ToastTone } from './toast';

const TONES: Record<ToastTone, string> = {
  success: 'border-success text-success',
  danger: 'border-danger text-danger',
  neutral: 'border-border text-text',
};

export function Toaster() {
  const toasts = useToasts((s) => s.toasts);
  const dismiss = useToasts((s) => s.dismiss);
  return (
    <div
      className="pointer-events-none fixed right-4 bottom-4 z-50 flex flex-col gap-2"
      aria-live="polite"
    >
      {toasts.map((toastItem) => (
        <button
          key={toastItem.id}
          type="button"
          onClick={() => {
            dismiss(toastItem.id);
          }}
          className={cn(
            'pointer-events-auto max-w-sm rounded-md border-l-4 bg-surface px-4 py-2 text-left text-sm shadow-lg',
            TONES[toastItem.tone],
          )}
        >
          {toastItem.message}
        </button>
      ))}
    </div>
  );
}
