import { Check } from 'lucide-react';
import { cn } from '../../lib/cn';

export interface Step {
  id: string;
  label: string;
}

interface StepperProps {
  steps: readonly Step[];
  currentIndex: number;
  onSelect?: (index: number) => void;
  className?: string;
}

/** 48px wizard step indicator (§10 layout for the Style Match wizard). */
export function Stepper({ steps, currentIndex, onSelect, className }: StepperProps) {
  return (
    <ol className={cn('flex h-12 items-center gap-2 overflow-x-auto px-1', className)} aria-label="wizard steps">
      {steps.map((step, index) => {
        const done = index < currentIndex;
        const active = index === currentIndex;
        return (
          <li key={step.id} className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onSelect?.(index)}
              aria-current={active ? 'step' : undefined}
              aria-label={`${index + 1}. ${step.label}`}
              disabled={onSelect === undefined}
              className={cn(
                'flex items-center gap-2 rounded-[var(--radius-control)] px-2.5 py-1.5 text-xs transition-colors',
                active && 'bg-[var(--accent-primary)]/15 text-[var(--accent-primary)]',
                done && 'text-[var(--success)]',
                !active && !done && 'text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]',
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  'grid h-5 w-5 place-items-center rounded-full border text-[10px]',
                  active && 'border-[var(--accent-primary)]',
                  done && 'border-[var(--success)] bg-[var(--success)]/15',
                  !active && !done && 'border-white/20',
                )}
              >
                {done ? <Check size={11} /> : index + 1}
              </span>
              <span className="whitespace-nowrap">{step.label}</span>
            </button>
            {index < steps.length - 1 ? (
              <span aria-hidden="true" className="h-px w-4 bg-white/10" />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
