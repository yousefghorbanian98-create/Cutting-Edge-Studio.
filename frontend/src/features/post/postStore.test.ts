import { beforeEach, describe, expect, it } from 'vitest';
import {
  COMPARISON_LAYOUTS,
  POST_FEATURES,
  POST_PRESETS,
  canRender,
  captionLanguageTag,
  enabledFeatures,
  findPreset,
  summarize,
  usePostStore,
} from './postStore';

beforeEach(() => {
  usePostStore.getState().reset();
});

describe('post production store', () => {
  it('exposes the seven protocol features with unique ids', () => {
    expect(POST_FEATURES).toHaveLength(7);
    const ids = new Set(POST_FEATURES.map((feature) => feature.id));
    expect(ids.size).toBe(7);
    expect(POST_FEATURES.map((feature) => feature.labelKey).every((key) => key.startsWith('post.'))).toBe(true);
  });

  it('starts with the safe defaults (replay, captions, loudness, thumbnail)', () => {
    expect(enabledFeatures(usePostStore.getState().enabled)).toEqual(['replay', 'captions', 'loudness', 'thumbnail']);
  });

  it('toggles features and ignores unknown presets', () => {
    usePostStore.getState().toggle('broll');
    expect(usePostStore.getState().enabled.broll).toBe(true);
    usePostStore.getState().toggle('broll');
    expect(usePostStore.getState().enabled.broll).toBe(false);

    usePostStore.getState().setPreset('youtube');
    expect(usePostStore.getState().presetId).toBe('youtube');
    usePostStore.getState().setPreset('myspace');
    expect(usePostStore.getState().presetId).toBe('tiktok');
  });

  it('keeps preset geometry consistent', () => {
    expect(findPreset('tiktok')).toMatchObject({ width: 1080, height: 1920, maxSeconds: 180 });
    expect(findPreset('youtube')).toMatchObject({ width: 1920, height: 1080, maxSeconds: null });
    expect(POST_PRESETS.map((preset) => preset.id)).toContain('archive');
  });

  it('summarizes the current selection', () => {
    const summary = summarize(usePostStore.getState());
    expect(summary).toBe('tiktok · 1080x1920 · ass · preview · 4/7');
    usePostStore.getState().setPreset('shorts');
    usePostStore.getState().setCaptionFormat('srt');
    expect(summarize(usePostStore.getState())).toContain('shorts · 1080x1920 · srt');
  });

  it('blocks a final render when only templates is enabled', () => {
    const state = usePostStore.getState();
    for (const feature of POST_FEATURES) {
      if (state.enabled[feature.id]) state.toggle(feature.id);
    }
    state.toggle('templates');
    expect(canRender({ enabled: usePostStore.getState().enabled, quality: 'final' })).toBe(false);
    expect(canRender({ enabled: usePostStore.getState().enabled, quality: 'preview' })).toBe(true);
    state.toggle('replay');
    expect(canRender({ enabled: usePostStore.getState().enabled, quality: 'final' })).toBe(true);
  });

  it('maps layouts and caption languages', () => {
    expect(COMPARISON_LAYOUTS).toHaveLength(3);
    expect(captionLanguageTag('fa')).toBe('fa');
    expect(captionLanguageTag('de')).toBe('en');
    usePostStore.getState().setLayout('stacked');
    expect(usePostStore.getState().layout).toBe('stacked');
    usePostStore.getState().setQuality('final');
    expect(usePostStore.getState().quality).toBe('final');
  });
});
