/** Keyboard-first skip link (WCAG 2.4.1). */
export function SkipLink({ label, targetId }: { label: string; targetId: string }) {
  return (
    <a
      href={`#${targetId}`}
      className="sr-only focus:not-sr-only focus:absolute focus:start-2 focus:top-2 focus:z-50 focus:rounded focus:bg-[var(--accent-primary)] focus:px-3 focus:py-1.5 focus:text-xs focus:text-black"
    >
      {label}
    </a>
  );
}
