import type { ReactNode } from 'react';
import * as TabsPrimitive from '@radix-ui/react-tabs';

export interface TabItem {
  value: string;
  label: string;
  content: ReactNode;
}

export function Tabs({ items, defaultValue, label }: { items: readonly TabItem[]; defaultValue?: string; label: string }) {
  return (
    <TabsPrimitive.Root defaultValue={defaultValue ?? items[0]?.value} className="flex h-full flex-col">
      <TabsPrimitive.List aria-label={label} className="flex shrink-0 gap-1 border-b border-white/5 pb-1">
        {items.map((item) => (
          <TabsPrimitive.Trigger
            key={item.value}
            value={item.value}
            className="rounded px-2 py-1 text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] data-[state=active]:bg-[var(--surface-hover)] data-[state=active]:text-[var(--text-primary)]"
          >
            {item.label}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
      {items.map((item) => (
        <TabsPrimitive.Content key={item.value} value={item.value} className="min-h-0 flex-1 overflow-auto pt-2">
          {item.content}
        </TabsPrimitive.Content>
      ))}
    </TabsPrimitive.Root>
  );
}
