import { create } from 'zustand';
import { api } from '../lib/api';

export type PostFeatureId = 'replay' | 'comparison' | 'captions' | 'broll' | 'loudness' | 'thumbnail' | 'templates';

export interface PostFeature {
  id: PostFeatureId;
  /** i18n key for the visible label. */
  labelKey: string;
  /** i18n key for the one-line explanation. */
  hintKey: string;
  /** Off by default when the feature changes the reference DNA. */
  defaultOn: boolean;
}

/** The seven post-production features promised by the protocol (P7), in UI order. */
export const POST_FEATURES: PostFeature[] = [
  { id: 'replay', labelKey: 'post.replay', hintKey: 'post.replay.hint', defaultOn: true },
  { id: 'comparison', labelKey: 'post.comparison', hintKey: 'post.comparison.hint', defaultOn: false },
  { id: 'captions', labelKey: 'post.captions', hintKey: 'post.captions.hint', defaultOn: true },
  { id: 'broll', labelKey: 'post.broll', hintKey: 'post.broll.hint', defaultOn: false },
  { id: 'loudness', labelKey: 'post.loudness', hintKey: 'post.loudness.hint', defaultOn: true },
  { id: 'thumbnail', labelKey: 'post.thumbnail', hintKey: 'post.thumbnail.hint', defaultOn: true },
  { id: 'templates', labelKey: 'post.templates', hintKey: 'post.templates.hint', defaultOn: false },
];

export interface PresetOption {
  id: string;
  labelKey: string;
  width: number;
  height: number;
  maxSeconds: number | null;
}

/** Offline fallback mirroring backend PRESETS, used until `hydratePresets` resolves.
 *
 * The backend owns this table (`services/post/presets.py`); these values exist only so
 * the panel renders before the sidecar answers and when it is unreachable. A contract
 * test (`backend/tests/test_post_contract.py`) fails the build if the two ever diverge.
 */
export const POST_PRESETS: PresetOption[] = [
  { id: 'tiktok', labelKey: 'post.preset.tiktok', width: 1080, height: 1920, maxSeconds: 180 },
  { id: 'shorts', labelKey: 'post.preset.shorts', width: 1080, height: 1920, maxSeconds: 60 },
  { id: 'youtube', labelKey: 'post.preset.youtube', width: 1920, height: 1080, maxSeconds: null },
  { id: 'instagram_feed', labelKey: 'post.preset.feed', width: 1080, height: 1350, maxSeconds: 60 },
  { id: 'archive', labelKey: 'post.preset.archive', width: 3840, height: 2160, maxSeconds: null },
];

export const COMPARISON_LAYOUTS = ['side_by_side', 'stacked', 'picture_in_picture'] as const;
export type ComparisonLayout = (typeof COMPARISON_LAYOUTS)[number];
export type CaptionFormat = 'srt' | 'ass';
export type RenderQuality = 'preview' | 'final';

const PRESET_LABEL_KEY: Record<string, string> = {
  tiktok: 'post.preset.tiktok',
  shorts: 'post.preset.shorts',
  youtube: 'post.preset.youtube',
  instagram_feed: 'post.preset.feed',
  archive: 'post.preset.archive',
};

interface PostState {
  enabled: Record<PostFeatureId, boolean>;
  /** Backend-owned preset table; seeded from POST_PRESETS until hydration lands. */
  presets: PresetOption[];
  layouts: ComparisonLayout[];
  presetId: string;
  layout: ComparisonLayout;
  captionFormat: CaptionFormat;
  quality: RenderQuality;
  toggle: (id: PostFeatureId) => void;
  setPreset: (id: string) => void;
  setLayout: (layout: ComparisonLayout) => void;
  setCaptionFormat: (format: CaptionFormat) => void;
  setQuality: (quality: RenderQuality) => void;
  /** Replace the local fallback with the backend's authoritative preset table. */
  hydrateFromBackend: (signal?: AbortSignal) => Promise<void>;
  reset: () => void;
}

function defaults(): Record<PostFeatureId, boolean> {
  return POST_FEATURES.reduce(
    (accumulator, feature) => ({ ...accumulator, [feature.id]: feature.defaultOn }),
    {} as Record<PostFeatureId, boolean>,
  );
}

export function findPreset(id: string, presets: PresetOption[] = POST_PRESETS): PresetOption {
  return presets.find((preset) => preset.id === id) ?? presets[0] ?? POST_PRESETS[0]!;
}

export function enabledFeatures(enabled: Record<PostFeatureId, boolean>): PostFeatureId[] {
  return POST_FEATURES.filter((feature) => enabled[feature.id]).map((feature) => feature.id);
}

/** One-line summary rendered under the panel ("tiktok · 1080x1920 · ass · 4/7"). */
export function summarize(settings: {
  enabled: Record<PostFeatureId, boolean>;
  presetId: string;
  captionFormat: CaptionFormat;
  quality: RenderQuality;
  presets?: PresetOption[];
}): string {
  const preset = findPreset(settings.presetId, settings.presets ?? POST_PRESETS);
  const count = enabledFeatures(settings.enabled).length;
  return `${preset.id} · ${preset.width}x${preset.height} · ${settings.captionFormat} · ${settings.quality} · ${count}/${POST_FEATURES.length}`;
}

/** Caption language choice drives the RTL override used in ASS output. */
export function captionLanguageTag(language: string): string {
  return language === 'fa' ? 'fa' : 'en';
}

/** Blocks final render when nothing that changes the picture is selected. */
export function canRender(settings: { enabled: Record<PostFeatureId, boolean>; quality: RenderQuality }): boolean {
  const features = enabledFeatures(settings.enabled);
  if (settings.quality === 'preview') return features.length > 0;
  return features.some((id) => id !== 'templates');
}

export const usePostStore = create<PostState>((set, get) => ({
  enabled: defaults(),
  presets: POST_PRESETS,
  layouts: [...COMPARISON_LAYOUTS],
  presetId: 'tiktok',
  layout: 'side_by_side',
  captionFormat: 'ass',
  quality: 'preview',
  toggle: (id) =>
    set({
      enabled: {
        ...get().enabled,
        [id]: !get().enabled[id],
      },
    }),
  setPreset: (presetId) => set({ presetId: findPreset(presetId, get().presets).id }),
  setLayout: (layout) => set({ layout }),
  setCaptionFormat: (captionFormat) => set({ captionFormat }),
  setQuality: (quality) => set({ quality }),
  hydrateFromBackend: async (signal) => {
    try {
      const [presets, layouts] = await Promise.all([api.postPresets(signal), api.postLayouts(signal)]);
      if (presets.length === 0) return;
      set({
        presets: presets.map((preset) => ({
          id: preset.name,
          labelKey: PRESET_LABEL_KEY[preset.name] ?? preset.label,
          width: preset.width,
          height: preset.height,
          maxSeconds: preset.max_seconds,
        })),
        layouts: layouts.filter((name): name is ComparisonLayout =>
          (COMPARISON_LAYOUTS as readonly string[]).includes(name),
        ),
      });
    } catch {
      // Offline-first: keep the bundled fallback rather than emptying the panel.
    }
  },
  reset: () => set({ enabled: defaults(), presetId: 'tiktok', layout: 'side_by_side', captionFormat: 'ass', quality: 'preview' }),
}));
