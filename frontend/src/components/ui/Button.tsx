import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { cn } from '../../lib/cn';
import { Spinner } from './Spinner';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  /** Visual error/success states map onto aria-invalid + data attributes. */
  tone?: 'neutral' | 'error' | 'success';
}

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-[var(--accent-primary)] text-black hover:bg-[var(--accent-hover)] active:brightness-90',
  secondary:
    'bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]',
  ghost: 'bg-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]',
  danger: 'bg-[var(--error)] text-white hover:brightness-110',
};

const SIZES: Record<ButtonSize, string> = {
  sm: 'h-7 px-2.5 text-xs',
  md: 'h-9 px-3.5 text-sm',
  lg: 'h-11 px-5 text-base',
};

/** Accessible button with the 10 component states expressed in data attributes. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = 'primary', size = 'md', loading = false, tone = 'neutral', disabled, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={props.type ?? 'button'}
      disabled={disabled ?? loading}
      aria-busy={loading || undefined}
      aria-invalid={tone === 'error' || undefined}
      data-tone={tone}
      data-loading={loading || undefined}
      className={cn(
        'inline-flex select-none items-center justify-center gap-2 rounded-[var(--radius-control)]',
        'font-medium transition-colors duration-[var(--duration-fast)]',
        'disabled:cursor-not-allowed disabled:opacity-45',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent-primary)]',
        VARIANTS[variant],
        SIZES[size],
        tone === 'error' && 'ring-1 ring-[var(--error)]',
        tone === 'success' && 'ring-1 ring-[var(--success)]',
        className,
      )}
      {...props}
    >
      {loading ? <Spinner size={size === 'lg' ? 16 : 12} decorative /> : null}
      {children}
    </button>
  );
});
