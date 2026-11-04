import { Check } from 'lucide-react';
import { Badge, Button, Switch } from '../../components/ui';
import { cn } from '../../lib/cn';
import { translate } from '../../lib/i18n';
import { useAppStore } from '../../store/useAppStore';
import {
  COMPARISON_LAYOUTS,
  POST_FEATURES,
  POST_PRESETS,
  canRender,
  enabledFeatures,
  summarize,
  usePostStore,
  type ComparisonLayout,
} from './postStore';

const LAYOUT_KEY: Record<ComparisonLayout, string> = {
  side_by_side: 'post.layout.side',
  stacked: 'post.layout.stacked',
  picture_in_picture: 'post.layout.pip',
};

/** Post-production controls (P7): features, platform preset, captions and render quality. */
export function PostPanel() {
  const language = useAppStore((state) => state.language);
  const enabled = usePostStore((state) => state.enabled);
  const presetId = usePostStore((state) => state.presetId);
  const layout = usePostStore((state) => state.layout);
  const captionFormat = usePostStore((state) => state.captionFormat);
  const quality = usePostStore((state) => state.quality);
  const toggle = usePostStore((state) => state.toggle);
  const setPreset = usePostStore((state) => state.setPreset);
  const setLayout = usePostStore((state) => state.setLayout);
  const setCaptionFormat = usePostStore((state) => state.setCaptionFormat);
  const setQuality = usePostStore((state) => state.setQuality);

  const active = enabledFeatures(enabled);
  const summary = summarize({ enabled, presetId, captionFormat, quality });

  return (
    <section aria-labelledby="post-panel-title" className="flex h-full flex-col gap-3 overflow-y-auto pe-1">
      <header className="flex items-center justify-between">
        <h3 id="post-panel-title" className="text-xs font-semibold">
          {translate(language, 'post.title')}
        </h3>
        <Badge tone="accent">{translate(language, 'post.count').replace('{n}', String(active.length))}</Badge>
      </header>

      <ul className="flex flex-col gap-1.5">
        {POST_FEATURES.map((feature) => (
          <li
            key={feature.id}
            className={cn(
              'flex items-start justify-between gap-2 rounded-[var(--radius-control)] border border-[var(--border-subtle)] px-2 py-1.5',
              enabled[feature.id] ? 'bg-[var(--bg-elevated)]' : 'opacity-70',
            )}
          >
            <div className="min-w-0">
              <p className="truncate text-[11px] font-medium">{translate(language, feature.labelKey)}</p>
              <p className="truncate text-[10px] text-[var(--text-secondary)]">{translate(language, feature.hintKey)}</p>
            </div>
            <Switch
              checked={enabled[feature.id]}
              onCheckedChange={() => toggle(feature.id)}
              label={translate(language, feature.labelKey)}
            />
          </li>
        ))}
      </ul>

      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-medium text-[var(--text-secondary)]">{translate(language, 'post.preset')}</span>
        <div className="flex flex-wrap gap-1">
          {POST_PRESETS.map((preset) => (
            <Button
              key={preset.id}
              size="sm"
              variant={preset.id === presetId ? 'primary' : 'ghost'}
              aria-pressed={preset.id === presetId}
              onClick={() => setPreset(preset.id)}
            >
              {translate(language, preset.labelKey)}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-medium text-[var(--text-secondary)]">{translate(language, 'post.layout')}</span>
        <div className="flex flex-wrap gap-1">
          {COMPARISON_LAYOUTS.map((option) => (
            <Button
              key={option}
              size="sm"
              variant={option === layout ? 'primary' : 'ghost'}
              aria-pressed={option === layout}
              onClick={() => setLayout(option)}
            >
              {translate(language, LAYOUT_KEY[option])}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] text-[var(--text-secondary)]">{translate(language, 'post.captionFormat')}</span>
        <div className="flex gap-1">
          {(['ass', 'srt'] as const).map((format) => (
            <Button
              key={format}
              size="sm"
              variant={captionFormat === format ? 'primary' : 'ghost'}
              aria-pressed={captionFormat === format}
              onClick={() => setCaptionFormat(format)}
            >
              {format.toUpperCase()}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] text-[var(--text-secondary)]">{translate(language, 'post.quality')}</span>
        <div className="flex gap-1">
          {(['preview', 'final'] as const).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={quality === value ? 'primary' : 'ghost'}
              aria-pressed={quality === value}
              onClick={() => setQuality(value)}
            >
              {translate(language, value === 'preview' ? 'post.quality.preview' : 'post.quality.final')}
            </Button>
          ))}
        </div>
      </div>

      <div className="mt-auto flex flex-col gap-2 border-t border-[var(--border-subtle)] pt-2">
        <p className="text-[10px] text-[var(--text-secondary)]" data-testid="post-summary">
          {summary}
        </p>
        <Button size="sm" disabled={!canRender({ enabled, quality })}>
          <Check size={12} className="me-1" aria-hidden="true" />
          {translate(language, quality === 'preview' ? 'post.render.preview' : 'post.render.final')}
        </Button>
        {!canRender({ enabled, quality }) ? (
          <p className="text-[10px] text-[var(--warning)]">{translate(language, 'post.blocked')}</p>
        ) : null}
      </div>
    </section>
  );
}
