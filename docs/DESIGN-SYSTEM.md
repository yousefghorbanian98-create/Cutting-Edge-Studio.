# Design System — Cutting Edge v2 (P1)

Stack: **Radix UI primitives (MIT)** + Tailwind 3 + CSS variables. No component library is
built from scratch (LOCK-00): primitives come from Radix, styling from a single token layer.

## Tokens (`frontend/src/index.css`)

| Group | Rule |
|---|---|
| Spacing | 4px base, `space-0` … `space-24` |
| Typography | 1.25 Major Third, 11px → 43px (`2xs` … `4xl`) |
| Radii | pro 8/6 · glass 20/12 · minimal 6/4 (panel/control) |
| Motion | fade 250ms (pro), spring 350ms (glass), 200ms crossfade (minimal) |
| Fonts | Vazirmatn (fa) + Inter (en) + JetBrains Mono, all **bundled OFL-1.1** via `@fontsource/*` |

Themes are switched with a single attribute: `document.documentElement.dataset.theme`.
Every theme consumes the same variable names, so components never branch on theme.

## The ten component states

`default · hover · active · focus · disabled · loading · error · success · empty · selected`

Implemented through data attributes + ARIA, never colour alone:

| State | Mechanism |
|---|---|
| focus | `:focus-visible` outline in `--accent-primary`, 2px + 2px offset |
| disabled | `disabled` attr + `opacity-45` + `cursor-not-allowed` |
| loading | `aria-busy` + decorative spinner (no extra AT noise) |
| error | `aria-invalid` + `ring-[--error]` (Input: `invalid` prop) |
| success | `data-success` + `ring-[--success]` |
| empty | `EmptyState` component with actionable hint |
| selected | `aria-current` / `data-state=checked` / `data-[selected=true]` (Radix) |

## Component inventory (`frontend/src/components/ui/`)

| Component | Primitive | Notes |
|---|---|---|
| Button | native `<button>` | variants primary/secondary/ghost/danger, sizes sm/md/lg |
| Badge | native `<span>` | tones neutral/accent/success/warning/error |
| Input | native `<input>` | invalid/success states |
| Spinner | CSS keyframes | `decorative` mode for busy parents |
| ProgressBar | `@radix-ui/react-progress` | always labelled, clamped, aria-valuenow |
| Modal | `@radix-ui/react-dialog` | focus trap + ESC from the primitive |
| Tooltip | `@radix-ui/react-tooltip` | 250 ms delay |
| Select | `@radix-ui/react-select` | keyboard navigable |
| Tabs | `@radix-ui/react-tabs` | roving focus |
| Switch | `@radix-ui/react-switch` | label + description |
| Slider | `@radix-ui/react-slider` | labelled thumb |
| Skeleton | CSS pulse | `aria-hidden` (state owned by parent) |
| EmptyState | native | title/hint/icon/action |
| Stepper | native `<ol>` | `aria-current="step"`, 48px bar |
| Toaster | sonner | themed by CSS variables |
| CommandPalette | cmdk | `Ctrl/Cmd+K` |
| SkipLink | native `<a>` | WCAG 2.4.1 |

## Accessibility gates
`frontend/src/a11y.test.tsx` runs **axe-core** over the shell in three configurations
(Persian/RTL, English/LTR, palette open) and fails on any violation. Colour contrast is
disabled in jsdom (no computed styles) and is verified on the real build in CI (P8).
