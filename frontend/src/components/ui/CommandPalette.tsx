import { useEffect } from 'react';
import { Command } from 'cmdk';

export interface CommandAction {
  id: string;
  label: string;
  hint?: string;
  onRun: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actions: readonly CommandAction[];
  label: string;
  placeholder?: string;
}

/** cmdk palette, toggled with Ctrl/Cmd+K from the app shell. */
export function CommandPalette({ open, onOpenChange, actions, label, placeholder }: CommandPaletteProps) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onOpenChange, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-[15vh]" role="presentation">
      <Command
        label={label}
        className="w-[min(92vw,520px)] overflow-hidden rounded-[var(--radius-panel)] border border-white/10 bg-[var(--bg-secondary)] shadow-2xl"
      >
        <Command.Input
          autoFocus
          placeholder={placeholder ?? label}
          className="w-full border-b border-white/10 bg-transparent px-3 py-2.5 text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-secondary)]"
        />
        <Command.List className="max-h-72 overflow-auto p-1">
          <Command.Empty className="px-3 py-6 text-center text-xs text-[var(--text-secondary)]">—</Command.Empty>
          {actions.map((action) => (
            <Command.Item
              key={action.id}
              value={action.label}
              onSelect={() => {
                action.onRun();
                onOpenChange(false);
              }}
              className="flex cursor-pointer items-center justify-between rounded px-2 py-1.5 text-xs text-[var(--text-secondary)] data-[selected=true]:bg-[var(--surface-hover)] data-[selected=true]:text-[var(--text-primary)]"
            >
              <span>{action.label}</span>
              {action.hint ? <kbd className="font-mono text-[10px] opacity-60">{action.hint}</kbd> : null}
            </Command.Item>
          ))}
        </Command.List>
      </Command>
    </div>
  );
}
