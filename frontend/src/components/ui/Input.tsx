import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '../../lib/cn';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
  success?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, invalid, success, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      data-success={success || undefined}
      className={cn(
        'h-9 w-full rounded-[var(--radius-control)] border bg-[var(--bg-secondary)] px-3 text-sm',
        'text-[var(--text-primary)] placeholder:text-[var(--text-secondary)]',
        'border-white/10 hover:border-white/20',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--accent-primary)]',
        'disabled:cursor-not-allowed disabled:opacity-50',
        invalid && 'border-[var(--error)]',
        success && 'border-[var(--success)]',
        className,
      )}
      {...props}
    />
  );
});
