import { cn } from '../../lib/cn';

interface SpinnerProps {
  size?: number;
  label?: string;
  className?: string;
  /** Decorative spinners are hidden from AT because a parent already carries the state. */
  decorative?: boolean;
}

/** CSS-only spinner (no canvas, no external animation library). */
export function Spinner({ size = 14, label = 'loading', className, decorative = false }: SpinnerProps) {
  return (
    <span
      role={decorative ? undefined : 'status'}
      aria-label={decorative ? undefined : label}
      aria-hidden={decorative || undefined}
      className={cn('inline-block animate-spin rounded-full border-2 border-current border-t-transparent', className)}
      style={{ width: size, height: size }}
    />
  );
}
