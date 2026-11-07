import { describe, expect, it } from 'vitest';
import { AVAILABLE_LANGUAGES, keysOf, translate } from './i18n';

describe('translation completeness (bilingual requirement)', () => {
  it('has identical key sets in both languages', () => {
    const fa = keysOf('fa').sort();
    const en = keysOf('en').sort();
    expect(fa).toEqual(en);
  });

  it('never ships an empty string', () => {
    for (const language of AVAILABLE_LANGUAGES) {
      for (const key of keysOf(language)) {
        expect(translate(language, key).trim().length).toBeGreaterThan(0);
      }
    }
  });

  it('covers every UI surface added in P1', () => {
    for (const key of [
      'wizard.next',
      'wizard.back',
      'media.import',
      'media.error.extension',
      'palette.label',
      'a11y.skip',
      'menu.theme',
    ]) {
      expect(keysOf('fa')).toContain(key);
      expect(keysOf('en')).toContain(key);
    }
  });
});
