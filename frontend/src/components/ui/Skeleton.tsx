import { cn } from '../../lib/cn';

/** Loading placeholder; `aria-hidden` because the spinner/role=status carries the state. */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn('animate-pulse rounded bg-white/5', className)} />;
}
