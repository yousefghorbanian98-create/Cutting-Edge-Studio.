import type { ReactNode } from 'react';
import { cn } from '../../lib/cn';

interface EmptyStateProps {
  title: string;
  hint?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ title, hint, icon, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex h-full flex-col items-center justify-center gap-2 rounded-[var(--radius-control)]',
        'border border-dashed border-white/10 p-6 text-center',
        className,
      )}
    >
      {icon ? <span aria-hidden="true" className="text-[var(--text-secondary)]">{icon}</span> : null}
      <p className="text-xs font-medium text-[var(--text-primary)]">{title}</p>
      {hint ? <p className="max-w-[32ch] text-[11px] text-[var(--text-secondary)]">{hint}</p> : null}
      {action}
    </div>
  );
}
