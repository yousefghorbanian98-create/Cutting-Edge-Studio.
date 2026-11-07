import * as SliderPrimitive from '@radix-ui/react-slider';

interface SliderProps {
  value: number;
  onValueChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label: string;
  format?: (value: number) => string;
}

export function Slider({ value, onValueChange, min = 0, max = 100, step = 1, label, format }: SliderProps) {
  return (
    <div className="py-1">
      <div className="mb-1 flex justify-between text-[11px] text-[var(--text-secondary)]">
        <span>{label}</span>
        <span className="font-mono">{format ? format(value) : value}</span>
      </div>
      <SliderPrimitive.Root
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={([next]) => onValueChange(next ?? min)}
        aria-label={label}
        className="relative flex h-4 w-full touch-none items-center"
      >
        <SliderPrimitive.Track className="relative h-1 w-full grow rounded-full bg-[var(--bg-tertiary)]">
          <SliderPrimitive.Range className="absolute h-full rounded-full bg-[var(--accent-primary)]" />
        </SliderPrimitive.Track>
        <SliderPrimitive.Thumb aria-label={label} className="block h-3 w-3 rounded-full bg-white shadow focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent-primary)]" />
      </SliderPrimitive.Root>
    </div>
  );
}
