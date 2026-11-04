import { create } from 'zustand';

export const WIZARD_STEPS = ['reference', 'dna', 'analysis', 'compatibility', 'edl'] as const;
export type WizardStepId = (typeof WIZARD_STEPS)[number];

export interface WizardRequirements {
  referenceSelected: boolean;
  clipCount: number;
}

interface WizardState {
  stepIndex: number;
  selectedReference: string | null;
  completed: boolean;
  selectReference: (path: string | null) => void;
  next: (requirements: WizardRequirements) => boolean;
  back: () => void;
  goTo: (index: number) => void;
  reset: () => void;
  progress: () => number;
}

/** Blocking rules per step — the gate that stops the wizard running blind. */
export function canAdvance(stepIndex: number, requirements: WizardRequirements): boolean {
  if (stepIndex === 0) return requirements.referenceSelected;
  if (stepIndex === 1) return requirements.clipCount > 0;
  return true;
}

export const useWizardStore = create<WizardState>((set, get) => ({
  stepIndex: 0,
  selectedReference: null,
  completed: false,
  selectReference: (path) => set({ selectedReference: path }),
  next: (requirements) => {
    const { stepIndex } = get();
    if (!canAdvance(stepIndex, requirements)) return false;
    const isLast = stepIndex >= WIZARD_STEPS.length - 1;
    set({ stepIndex: isLast ? stepIndex : stepIndex + 1, completed: isLast });
    return true;
  },
  back: () => set((state) => ({ stepIndex: Math.max(0, state.stepIndex - 1) })),
  goTo: (index) =>
    set({ stepIndex: Math.min(Math.max(index, 0), WIZARD_STEPS.length - 1) }),
  reset: () => set({ stepIndex: 0, selectedReference: null, completed: false }),
  progress: () => Math.round((get().stepIndex / (WIZARD_STEPS.length - 1)) * 100),
}));
