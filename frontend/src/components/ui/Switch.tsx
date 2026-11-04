import * as SwitchPrimitive from '@radix-ui/react-switch';

interface SwitchProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}

export function Switch({ checked, onCheckedChange, label, description, disabled }: SwitchProps) {
  const id = `switch-${label.replace(/\s+/g, '-').toLowerCase()}`;
  return (
    <div className="flex items-center justify-between gap-3 py-1">
      <label htmlFor={id} className="text-xs text-[var(--text-primary)]">
        {label}
        {description ? <span className="block text-[11px] text-[var(--text-secondary)]">{description}</span> : null}
      </label>
      <SwitchPrimitive.Root
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        className="relative h-5 w-9 shrink-0 rounded-full bg-[var(--bg-tertiary)] transition-colors data-[state=checked]:bg-[var(--accent-primary)] disabled:opacity-40"
      >
        <SwitchPrimitive.Thumb className="block h-4 w-4 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-[18px]" />
      </SwitchPrimitive.Root>
    </div>
  );
}
