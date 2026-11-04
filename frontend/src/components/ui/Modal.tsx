import type { ReactNode } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '../../lib/cn';

interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children?: ReactNode;
  footer?: ReactNode;
  className?: string;
}

/** Radix dialog: focus trap, ESC handling and aria wiring come from the primitive. */
export function Modal({ open, onOpenChange, title, description, children, footer, className }: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content
          className={cn(
            'fixed left-1/2 top-1/2 z-50 w-[min(92vw,520px)] -translate-x-1/2 -translate-y-1/2',
            'rounded-[var(--radius-panel)] border border-white/10 bg-[var(--bg-secondary)] p-5 shadow-2xl',
            className,
          )}
        >
          <div className="mb-3 flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-sm font-semibold text-[var(--text-primary)]">{title}</Dialog.Title>
              {description ? (
                <Dialog.Description className="mt-1 text-xs text-[var(--text-secondary)]">
                  {description}
                </Dialog.Description>
              ) : null}
            </div>
            <Dialog.Close
              aria-label="close"
              className="rounded p-1 text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
            >
              <X size={16} aria-hidden="true" />
            </Dialog.Close>
          </div>
          {children}
          {footer ? <div className="mt-5 flex justify-end gap-2">{footer}</div> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
