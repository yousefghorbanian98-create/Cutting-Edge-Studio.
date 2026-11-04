import * as Progress from '@radix-ui/react-progress';
import { cn } from '../../lib/cn';

interface ProgressBarProps {
  value: number;
  max?: number;
  label: string;
  hint?: string;
  tone?: 'accent' | 'success' | 'error';
  className?: string;
}

/** Determinate progress with an explicit, screen-reader-visible label (P0 req: clear progress UI). */
export function ProgressBar({ value, max = 100, label, hint, tone = 'accent', className }: ProgressBarProps) {
  const clamped = Math.min(Math.max(value, 0), max);
  const percent = max === 0 ? 0 : Math.round((clamped / max) * 100);
  const color =
    tone === 'success' ? 'var(--success)' : tone === 'error' ? 'var(--error)' : 'var(--accent-primary)';

  return (
    <div className={cn('w-full', className)}>
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <span className="text-xs text-[var(--text-secondary)]">{label}</span>
        <span className="font-mono text-[11px] text-[var(--text-secondary)]" aria-hidden="true">
          {percent}%
        </span>
      </div>
      <Progress.Root
        value={clamped}
        max={max}
        aria-label={label}
        className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--bg-tertiary)]"
      >
        <Progress.Indicator
          className="h-full rounded-full transition-[width] duration-300 ease-out"
          style={{ width: `${percent}%`, background: color }}
        />
      </Progress.Root>
      {hint ? <p className="mt-1 text-[11px] text-[var(--text-secondary)]">{hint}</p> : null}
    </div>
  );
}
