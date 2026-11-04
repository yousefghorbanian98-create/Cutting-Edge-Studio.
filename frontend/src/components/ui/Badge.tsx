import type { ReactNode } from 'react';
import { cn } from '../../lib/cn';

export type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'error';

const TONES: Record<BadgeTone, string> = {
  neutral: 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]',
  accent: 'bg-[var(--accent-primary)]/15 text-[var(--accent-primary)]',
  success: 'bg-[var(--success)]/15 text-[var(--success)]',
  warning: 'bg-[var(--warning)]/15 text-[var(--warning)]',
  error: 'bg-[var(--error)]/15 text-[var(--error)]',
};

export function Badge({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium', TONES[tone], className)}
    >
      {children}
    </span>
  );
}
