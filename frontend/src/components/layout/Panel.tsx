import type { ReactNode } from 'react';
import { cn } from '../../lib/cn';

interface PanelProps {
  title: string;
  children: ReactNode;
  className?: string;
  actions?: ReactNode;
  as?: 'section' | 'aside';
}

/** Bordered workspace panel with a fixed-height header (see layout spec §10). */
export function Panel({ title, children, className, actions, as = 'section' }: PanelProps) {
  const Tag = as;
  return (
    <Tag
      aria-label={title}
      className={cn(
        'flex min-h-0 flex-col overflow-hidden border border-white/5 bg-surface',
        'rounded-panel',
        className,
      )}
      style={{ borderRadius: 'var(--radius-panel)' }}
    >
      <header className="flex h-9 shrink-0 items-center justify-between border-b border-white/5 px-3">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-text-secondary">{title}</h2>
        {actions}
      </header>
      <div className="min-h-0 flex-1 overflow-auto p-3">{children}</div>
    </Tag>
  );
}
