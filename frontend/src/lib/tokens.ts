/**
 * Design tokens shared by TS logic and tests (CSS variables live in index.css).
 * Typography follows a 1.25 Major Third scale starting at 11px (§10).
 */

export const SPACING_BASE_PX = 4;

/** space-0 … space-24 (4px base). */
export const spacing = Object.fromEntries(
  Array.from({ length: 25 }, (_, index) => [`space-${index}`, index * SPACING_BASE_PX]),
) as Record<string, number>;

export const TYPE_SCALE = 1.25;

export const fontSizesPx = Object.fromEntries(
  ['2xs', 'xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl', '4xl'].map((name, index) => [
    name,
    Math.round(11 * TYPE_SCALE ** index),
  ]),
) as Record<string, number>;

/** Radius per theme (§10). */
export const radii = {
  pro: { panel: 8, control: 6 },
  glass: { panel: 20, control: 12 },
  minimal: { panel: 6, control: 4 },
} as const;

/** The ten component states every interactive element must be able to express. */
export const COMPONENT_STATES = [
  'default',
  'hover',
  'active',
  'focus',
  'disabled',
  'loading',
  'error',
  'success',
  'empty',
  'selected',
] as const;

export type ComponentState = (typeof COMPONENT_STATES)[number];
