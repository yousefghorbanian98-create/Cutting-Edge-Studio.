import { useRef, useState } from 'react';
import { DndContext, type DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { ArrowRight, Film, Music, Trash2, Upload } from 'lucide-react';
import { Badge, Button, EmptyState, Tooltip } from '../../components/ui';
import { translate } from '../../lib/i18n';
import { formatBytes } from '../../lib/files';
import { useAppStore } from '../../store/useAppStore';
import { useTimelineStore } from '../timeline/timelineStore';
import { type MediaClip, useMediaStore } from './mediaStore';

function SortableClip({
  clip,
  language,
  onRemove,
  onSend,
  onSelect,
}: {
  clip: MediaClip;
  language: 'fa' | 'en';
  onRemove: (id: string) => void;
  onSend: (clip: MediaClip) => void;
  onSelect: (id: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: clip.id });
  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`flex items-center gap-2 rounded-[var(--radius-control)] border border-white/5 bg-[var(--bg-secondary)] px-2 py-1.5 ${
        isDragging ? 'opacity-60' : ''
      }`}
      data-testid={`clip-${clip.id}`}
    >
      <button
        type="button"
        aria-label={`drag ${clip.name}`}
        className="cursor-grab text-[var(--text-secondary)]"
        {...attributes}
        {...listeners}
      >
        {clip.kind === 'video' ? <Film size={13} aria-hidden="true" /> : <Music size={13} aria-hidden="true" />}
      </button>
      <div className="min-w-0 flex-1">
        <button type="button" onClick={() => onSelect(clip.id)} className="block max-w-full truncate text-[11px] text-[var(--text-primary)]">{clip.name}</button>
        <p className="text-[10px] text-[var(--text-secondary)]">
          {formatBytes(clip.size)}{clip.duration !== undefined ? ` · ${clip.duration.toFixed(2)}s · ${clip.width}×${clip.height}` : ''}
          {clip.available === false ? ` · ${translate(language, 'media.unavailable')}` : ''}
          {clip.role === 'reference' ? ` · ${translate(language, 'media.reference')}` : ''}
        </p>
      </div>
      <Tooltip content={translate(language, 'media.send')}>
        <button
          type="button"
          onClick={() => onSend(clip)}
          aria-label={`${translate(language, 'media.send')} ${clip.name}`}
          className="rounded p-1 text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--accent-primary)]"
        >
          <ArrowRight size={12} aria-hidden="true" className="rtl:rotate-180" />
        </button>
      </Tooltip>
      <Tooltip content={translate(language, 'media.remove')}>
        <button
          type="button"
          onClick={() => onRemove(clip.id)}
          aria-label={`${translate(language, 'media.remove')} ${clip.name}`}
          className="rounded p-1 text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--error)]"
        >
          <Trash2 size={12} aria-hidden="true" />
        </button>
      </Tooltip>
    </li>
  );
}

/** Media panel: native drag-drop import + dnd-kit reordering (LOCK-00: no hand-rolled DnD). */
export function MediaPanel() {
  const language = useAppStore((state) => state.language);
  const clips = useMediaStore((state) => state.clips);
  const importToBackend = useMediaStore((state) => state.importFiles);
  const deleteImported = useMediaStore((state) => state.deleteImported);
  const selectClip = useMediaStore((state) => state.selectClip);
  const importing = useMediaStore((state) => state.importing);
  const reorder = useMediaStore((state) => state.reorder);
  const addClipToTimeline = useTimelineStore((state) => state.addClip);
  const [errors, setErrors] = useState<string[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const referenceInputRef = useRef<HTMLInputElement>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const importFiles = async (files: FileList | File[], role: 'source' | 'reference' = 'source') => {
    try {
      const outcome = await importToBackend(Array.from(files), role);
      setErrors(outcome.rejected.map(item => {
        const key = `media.error.${item.reason}`;
        const message = translate(language, key);
        return `${item.name}: ${message === key ? item.reason : message}`;
      }));
    } catch (error) {
      console.error('media.import.failed', error);
      setErrors([String(error)]);
    }
  };

  const removeClip = async (id: string) => {
    const clip = useMediaStore.getState().clips.find(item => item.id === id);
    if (clip && useTimelineStore.getState().clips.some(item => item.mediaId === clip.path)) {
      setErrors([translate(language, 'media.error.inUse')]);
      return;
    }
    try { await deleteImported(id); setErrors([]); }
    catch (error) {
      console.error('media.delete.failed', error);
      setErrors([String(error)]);
    }
  };

  const onDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      reorder(String(active.id), String(over.id));
    }
  };

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        void importFiles(event.dataTransfer.files);
      }}
      className="flex h-full flex-col gap-2"
      data-dragging={dragging || undefined}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] text-[var(--text-secondary)]">
          {clips.length} {translate(language, 'media.count')}
        </span>
        <Button size="sm" variant="secondary" disabled={importing} onClick={() => inputRef.current?.click()}>
          <Upload size={12} aria-hidden="true" />
          {translate(language, 'media.import')}
        </Button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="video/*,audio/*"
          aria-label={translate(language, 'media.import')}
          className="hidden"
          onChange={(event) => {
            if (event.target.files) void importFiles(event.target.files);
            event.target.value = '';
          }}
        />
      </div>

      <div className="flex flex-col gap-1">
        <Button size="sm" variant="secondary" disabled={importing} onClick={() => referenceInputRef.current?.click()}>
          {translate(language, 'media.import.reference')}
        </Button>
        <input ref={referenceInputRef} type="file" accept="video/*" className="hidden"
          aria-label={translate(language, 'media.import.reference')}
          onChange={event => {
            if (event.target.files) void importFiles(event.target.files, 'reference');
            event.target.value = '';
          }} />
        {importing ? <p role="status">{translate(language, 'media.importing')}</p> : null}
      </div>

      {errors.length > 0 ? (
        <ul role="alert" className="space-y-1 text-[10px] text-[var(--error)]">
          {errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      ) : null}

      {clips.length === 0 ? (
        <EmptyState
          title={translate(language, 'media.empty')}
          hint={translate(language, 'media.empty.hint')}
          icon={<Film size={22} />}
        />
      ) : (
        <DndContext sensors={sensors} onDragEnd={onDragEnd}>
          <SortableContext items={clips.map((clip) => clip.id)} strategy={verticalListSortingStrategy}>
            <ul className="space-y-1">
              {clips.map((clip) => (
                <SortableClip
                  key={clip.id}
                  clip={clip}
                  language={language}
                  onRemove={id => void removeClip(id)}
                  onSelect={selectClip}
                  onSend={(item) => {
                    selectClip(item.id);
                    addClipToTimeline({ mediaId: item.path, name: item.name, kind: item.kind, duration: item.duration });
                  }}
                />
              ))}
            </ul>
          </SortableContext>
        </DndContext>
      )}
      {clips.some((clip) => clip.role === 'reference') ? (
        <Badge tone="accent">{translate(language, 'media.reference')}</Badge>
      ) : null}
    </div>
  );
}
