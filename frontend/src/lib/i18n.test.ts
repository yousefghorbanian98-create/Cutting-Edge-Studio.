import { describe, expect, it } from 'vitest';
import { AVAILABLE_LANGUAGES, directionOf, translate } from './i18n';

describe('i18n', () => {
  it('ships both required languages', () => {
    expect(AVAILABLE_LANGUAGES).toEqual(['fa', 'en']);
  });

  it('maps direction per language', () => {
    expect(directionOf('fa')).toBe('rtl');
    expect(directionOf('en')).toBe('ltr');
  });

  it('translates in both languages', () => {
    expect(translate('fa', 'panel.media')).toBe('رسانه');
    expect(translate('en', 'panel.media')).toBe('Media');
  });

  it('falls back to the key instead of throwing', () => {
    expect(translate('en', 'missing.key')).toBe('missing.key');
  });
});
