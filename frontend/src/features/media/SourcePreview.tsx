import { useState } from 'react';
import { assetContentUrl } from '../../lib/api';
import { translate } from '../../lib/i18n';
import { useAppStore } from '../../store/useAppStore';
import { type MediaClip, useMediaStore } from './mediaStore';

/** Native browser playback only; never implies that the edit has been rendered. */
function Player({ clip }: { clip: MediaClip }) {
  const language = useAppStore(state => state.language);
  const [failed, setFailed] = useState(false);
  const props = {
    src: assetContentUrl(clip.assetId!),
    controls: true,
    preload: 'metadata',
    onError: () => {
      console.error('media.playback.failed', clip.assetId);
      setFailed(true);
    },
    'aria-label': clip.name,
  };
  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <p className="text-xs text-[var(--text-secondary)]">{translate(language, 'preview.source')} · {clip.name}</p>
      {clip.kind === 'video'
        ? <video {...props} className="min-h-0 w-full flex-1 bg-black object-contain" />
        : <audio {...props} className="w-full" />}
      {failed ? <p role="alert" className="text-xs text-[var(--error)]">{translate(language, 'preview.failed')}</p> : null}
    </div>
  );
}

export function SourcePreview() {
  const language = useAppStore(state => state.language);
  const clip = useMediaStore(state => state.clips.find(item => item.id === state.selectedId));
  if (!clip?.assetId) {
    return <div className="flex h-full items-center justify-center bg-black/40 text-xs text-[var(--text-secondary)]">{translate(language, 'preview.empty')}</div>;
  }
  return <Player key={clip.assetId} clip={clip} />;
}
