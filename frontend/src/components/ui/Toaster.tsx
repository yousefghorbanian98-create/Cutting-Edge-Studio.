import { Toaster as SonnerToaster } from 'sonner';

/** Sonner toaster, themed by the CSS variables (no external network, no fonts). */
export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-left"
      theme="dark"
      closeButton
      toastOptions={{
        classNames: {
          toast: 'rounded-[var(--radius-control)] border border-white/10 bg-[var(--bg-secondary)] text-[var(--text-primary)]',
        },
      }}
    />
  );
}
