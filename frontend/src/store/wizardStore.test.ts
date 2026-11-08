import { beforeEach, describe, expect, it } from 'vitest';
import { WIZARD_STEPS, canAdvance, useWizardStore } from '../store/wizardStore';

const ok = { referenceSelected: true, clipCount: 3 };

beforeEach(() => {
  useWizardStore.getState().reset();
});

describe('style match wizard store', () => {
  it('defines the 5 visible stages of the flow', () => {
    expect(WIZARD_STEPS).toHaveLength(5);
    expect(WIZARD_STEPS[0]).toBe('reference');
    expect(WIZARD_STEPS[4]).toBe('edl');
  });

  it('blocks step 1 without a reference', () => {
    expect(canAdvance(0, { referenceSelected: false, clipCount: 5 })).toBe(false);
    expect(useWizardStore.getState().next({ referenceSelected: false, clipCount: 5 })).toBe(false);
    expect(useWizardStore.getState().stepIndex).toBe(0);
  });

  it('blocks step 2 without source clips', () => {
    expect(canAdvance(1, { referenceSelected: true, clipCount: 0 })).toBe(false);
  });

  it('advances, reports progress and marks completion at the last step', () => {
    expect(useWizardStore.getState().next(ok)).toBe(true);
    expect(useWizardStore.getState().stepIndex).toBe(1);
    expect(useWizardStore.getState().progress()).toBe(25);
    for (let index = 0; index < 3; index += 1) {
      useWizardStore.getState().next(ok);
    }
    expect(useWizardStore.getState().stepIndex).toBe(4);
    expect(useWizardStore.getState().progress()).toBe(100);
    useWizardStore.getState().next(ok);
    expect(useWizardStore.getState().completed).toBe(true);
  });

  it('clamps back and goTo', () => {
    useWizardStore.getState().back();
    expect(useWizardStore.getState().stepIndex).toBe(0);
    useWizardStore.getState().goTo(99);
    expect(useWizardStore.getState().stepIndex).toBe(4);
  });

  it('keeps the selected reference', () => {
    useWizardStore.getState().selectReference('/media/ref.mp4');
    expect(useWizardStore.getState().selectedReference).toBe('/media/ref.mp4');
  });
});
