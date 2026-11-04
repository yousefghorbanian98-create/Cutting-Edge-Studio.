import { AnimatePresence, motion } from 'framer-motion';
import { ShieldCheck } from 'lucide-react';
import { Badge, Button, ProgressBar, Stepper, type Step } from '../../components/ui';
import { translate } from '../../lib/i18n';
import { useAppStore } from '../../store/useAppStore';
import { useWorkspaceStore } from '../workspace/workspaceStore';
import { InspectionPanel } from './InspectionPanel';
import { useMediaStore } from '../media/mediaStore';
import { useWizardStore, WIZARD_STEPS, canAdvance } from './wizardStore';

const STEP_LABEL_KEYS = ['wizard.step.1', 'wizard.step.2', 'wizard.step.3', 'wizard.step.4', 'wizard.step.5'];

/** Style Match wizard (LOCK-01: the default flow of the app). */
export function StyleMatchWizard() {
  const language = useAppStore((state) => state.language);
  const clips = useMediaStore((state) => state.clips);
  const projectId=useMediaStore(state=>state.projectId);
  const importing=useMediaStore(state=>state.importing);
  const navigating=useWorkspaceStore(state=>state.navigating);
  const stepIndex = useWizardStore((state) => state.stepIndex);
  const next = useWizardStore((state) => state.next);
  const back = useWizardStore((state) => state.back);
  const goTo = useWizardStore((state) => state.goTo);
  const selectedReference = useWizardStore((state) => state.selectReference);
  const referencePath = useWizardStore((state) => state.selectedReference);

  const steps: Step[] = WIZARD_STEPS.map((id, index) => ({
    id,
    label: translate(language, STEP_LABEL_KEYS[index] ?? ''),
  }));
  const requirement = {
    referenceSelected: referencePath !== null && clips.some(clip => clip.role === 'reference' && clip.path === referencePath && clip.available !== false),
    clipCount: clips.filter(clip=>clip.role==='source').length,
  };
  const reference = clips.find(clip => clip.role === 'reference');
  const blocked = !canAdvance(stepIndex, requirement);
  const progress = Math.round((stepIndex / (WIZARD_STEPS.length - 1)) * 100);
  const isLast = stepIndex === WIZARD_STEPS.length - 1;

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-[var(--text-primary)]">{translate(language, 'wizard.title')}</h3>
        <Badge tone="success">
          <ShieldCheck size={11} className="me-1" aria-hidden="true" />
          {translate(language, 'wizard.independence')}
        </Badge>
      </div>

      <Stepper completedIndices={[]} steps={steps} currentIndex={stepIndex} onSelect={goTo} />

      <ProgressBar value={progress} label={translate(language, 'wizard.progress')} />

      <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={stepIndex}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.18 }}
        className="min-h-0 flex-1 overflow-auto rounded-[var(--radius-control)] border border-white/5 bg-[var(--bg-secondary)] p-3 text-xs text-[var(--text-secondary)]"
      >
        {blocked ? (
          <p role="status" className="text-[var(--warning)]">
            {stepIndex === 0
              ? translate(language, 'wizard.needs.reference')
              : translate(language, 'wizard.needs.clips')}
          </p>
        ) : (
          <p>{steps[stepIndex]?.label}</p>
        )}

        {stepIndex === 2 ? <InspectionPanel key={projectId ?? 'empty'} projectId={projectId}
          referenceId={clips.find(c=>c.role==='reference' && c.path===referencePath)?.assetId ?? null}
          sourceIds={clips.filter(c=>c.role==='source' && c.assetId).map(c=>c.assetId!)}
          blocked={importing || navigating || clips.some(c=>(c.role==='source' || c.path===referencePath) && c.available===false)} />:null}
        {stepIndex === 0 ? (
          <div className="mt-3 space-y-1">
            <p className="text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
              {translate(language, 'wizard.reference.selected')}
            </p>
            <p className="text-[11px] text-[var(--text-primary)]">
              {requirement.referenceSelected ? referencePath : translate(language, 'wizard.no.reference')}
            </p>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => selectedReference(reference?.path ?? null)}
              disabled={!reference}
            >
              {translate(language, 'wizard.step.1')}
            </Button>
          </div>
        ) : null}
      </motion.div>
      </AnimatePresence>

      {isLast ? <p role="status" className="text-xs text-[var(--warning)]">{translate(language, 'wizard.unavailable')}</p> : null}
      <div className="flex items-center justify-between gap-2">
        <Button variant="ghost" size="sm" onClick={back} disabled={stepIndex === 0}>
          {translate(language, 'wizard.back')}
        </Button>
        <Button
          size="sm"
          onClick={() => next(requirement)}
          disabled={blocked || isLast}
          loading={false}
          data-testid="wizard-next"
        >
          {isLast ? translate(language, 'wizard.start') : translate(language, 'wizard.next')}
        </Button>
      </div>
    </div>
  );
}
