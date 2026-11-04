import { useCallback, useMemo, useRef } from 'react';
import { Timeline, type TimelineState } from '@xzdarcy/react-timeline-editor';
import type { TimelineEffect, TimelineRow } from '@xzdarcy/timeline-engine';
import { useHotkeys } from 'react-hotkeys-hook';
import { Magnet, Minus, Pause, Play, Plus, Scissors, Trash2, Undo2, Redo2, Bookmark } from 'lucide-react';
import { Badge, Button, Tooltip } from '../../components/ui';
import { translate } from '../../lib/i18n';
import { useAppStore } from '../../store/useAppStore';
import { EFFECT_IDS, fromEditorData, toEditorData } from './timelineAdapter';
import { clamp, rulerTicks, snapTime, timecode } from './timelineMath';
import { snapTargets, useTimelineStore } from './timelineStore';

/**
 * Effects are plain descriptors: the code/audio classes are rendered by
 * `getActionRender`, so no custom drawing logic from scratch is needed.
 */
const EFFECTS: Record<string, TimelineEffect> = {
  [EFFECT_IDS.video]: { id: EFFECT_IDS.video, name: 'video' },
  [EFFECT_IDS.audio]: { id: EFFECT_IDS.audio, name: 'audio' },
};

/** Timeline: ruler + playhead + bars, powered by @xzdarcy/react-timeline-editor. */
export function TimelinePanel() {
  const language = useAppStore((state) => state.language);
  const timelineRef = useRef<TimelineState | null>(null);

  const {
    tracks,
    clips,
    bookmarks,
    pxPerSecond,
    playhead,
    playing,
    snapEnabled,
    selectedIds,
    duration,
  } = useTimelineStore();

  const setZoom = useTimelineStore((state) => state.setZoom);
  const zoomIn = useTimelineStore((state) => state.zoomIn);
  const zoomOut = useTimelineStore((state) => state.zoomOut);
  const toggleSnap = useTimelineStore((state) => state.toggleSnap);
  const togglePlaying = useTimelineStore((state) => state.togglePlaying);
  const setPlayhead = useTimelineStore((state) => state.setPlayhead);
  const selectClip = useTimelineStore((state) => state.selectClip);
  const moveClip = useTimelineStore((state) => state.moveClip);
  const splitAtPlayhead = useTimelineStore((state) => state.splitAtPlayhead);
  const removeSelected = useTimelineStore((state) => state.removeSelected);
  const addBookmark = useTimelineStore((state) => state.addBookmark);
  const undo = useTimelineStore((state) => state.undo);
  const redo = useTimelineStore((state) => state.redo);

  const editorData = useMemo(() => toEditorData(tracks, clips), [tracks, clips]);
  const ticks = useMemo(() => rulerTicks(duration, pxPerSecond, 70), [duration, pxPerSecond]);

  const handleChange = useCallback(
    (next: TimelineRow[]) => {
      for (const change of fromEditorData(next)) {
        const clip = clips.find((item) => item.id === change.id);
        if (!clip) continue;
        if (Math.abs(change.start - clip.start) > 1e-3) {
          const { value } = snapTime(change.start, {
            pxPerSecond,
            grid: 0.5,
            targets: snapTargets(clips, bookmarks, clip.id),
            enabled: snapEnabled,
          });
          moveClip(clip.id, value);
        }
      }
      return false;
    },
    [bookmarks, clips, moveClip, pxPerSecond, snapEnabled],
  );

  useHotkeys('space', (event) => {
    event.preventDefault();
    togglePlaying();
  }, [togglePlaying]);
  useHotkeys('m', () => addBookmark());
  useHotkeys('s', () => splitAtPlayhead());
  useHotkeys('delete, backspace', () => removeSelected());
  useHotkeys('mod+z', () => undo());
  useHotkeys('mod+shift+z', () => redo());
  useHotkeys('equal, plus', () => zoomIn());
  useHotkeys('minus', () => zoomOut());
  useHotkeys('left', () => setPlayhead(playhead - 1 / 30));
  useHotkeys('right', () => setPlayhead(playhead + 1 / 30));

  const seek = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const offset = event.clientX - rect.left;
    setPlayhead(clamp(offset / pxPerSecond, 0, duration));
    timelineRef.current?.setTime?.(offset / pxPerSecond);
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-1">
      <div className="flex items-center gap-1.5">
        <Tooltip content="Space">
          <Button size="sm" variant="secondary" onClick={togglePlaying} aria-label="play-pause">
            {playing ? <Pause size={12} aria-hidden="true" /> : <Play size={12} aria-hidden="true" />}
          </Button>
        </Tooltip>
        <Tooltip content="M">
          <Button size="sm" variant="ghost" onClick={() => addBookmark()} aria-label="add-bookmark">
            <Bookmark size={12} aria-hidden="true" />
          </Button>
        </Tooltip>
        <Tooltip content="S">
          <Button size="sm" variant="ghost" onClick={() => splitAtPlayhead()} aria-label="split">
            <Scissors size={12} aria-hidden="true" />
          </Button>
        </Tooltip>
        <Tooltip content="Delete">
          <Button size="sm" variant="ghost" onClick={() => removeSelected()} aria-label="delete-selected" disabled={selectedIds.length === 0}>
            <Trash2 size={12} aria-hidden="true" />
          </Button>
        </Tooltip>
        <Tooltip content="Ctrl+Z">
          <Button size="sm" variant="ghost" onClick={() => undo()} aria-label="undo">
            <Undo2 size={12} aria-hidden="true" />
          </Button>
        </Tooltip>
        <Tooltip content="Ctrl+Shift+Z">
          <Button size="sm" variant="ghost" onClick={() => redo()} aria-label="redo">
            <Redo2 size={12} aria-hidden="true" />
          </Button>
        </Tooltip>
        <span className="mx-1 h-4 w-px bg-white/10" aria-hidden="true" />
        <Button
          size="sm"
          variant={snapEnabled ? 'secondary' : 'ghost'}
          onClick={toggleSnap}
          aria-label="toggle-snap"
          aria-pressed={snapEnabled}
        >
          <Magnet size={12} aria-hidden="true" />
        </Button>
        <Button size="sm" variant="ghost" onClick={zoomOut} aria-label="zoom-out">
          <Minus size={12} aria-hidden="true" />
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setZoom(pxPerSecond)} aria-label="zoom-reset">
          <Plus size={12} aria-hidden="true" />
        </Button>
        <Button size="sm" variant="ghost" onClick={zoomIn} aria-label="zoom-in">
          <span className="text-[10px]">×1.25</span>
        </Button>
        <span className="ms-auto font-mono text-[11px] text-[var(--text-secondary)]" data-testid="timecode">
          {timecode(playhead)} / {timecode(duration)}
        </span>
        <Badge tone="neutral">{clips.length}</Badge>
      </div>

      <div
        role="slider"
        aria-label="playhead"
        aria-valuemin={0}
        aria-valuemax={duration}
        aria-valuenow={Number(playhead.toFixed(2))}
        tabIndex={0}
        onClick={seek}
        className="relative h-6 shrink-0 cursor-pointer overflow-hidden rounded-[var(--radius-control)] border border-white/5 bg-[var(--bg-secondary)]"
      >
        {ticks.map((tick) => (
          <span
            key={tick.time}
            aria-hidden="true"
            className={`absolute top-0 h-full border-s ${tick.major ? 'border-white/25' : 'border-white/10'}`}
            style={{ left: tick.time * pxPerSecond }}
          >
            {tick.major ? (
              <span className="absolute top-0.5 ps-1 font-mono text-[9px] text-[var(--text-secondary)]">
                {timecode(tick.time).slice(3, 8)}
              </span>
            ) : null}
          </span>
        ))}
        {bookmarks.map((bookmark) => (
          <span
            key={bookmark.id}
            aria-label={`bookmark ${bookmark.label}`}
            className="absolute top-0 h-full w-0.5 bg-[var(--warning)]"
            style={{ left: bookmark.time * pxPerSecond }}
          />
        ))}
        <span
          aria-hidden="true"
          data-testid="playhead-marker"
          className="absolute top-0 h-full w-px bg-[var(--accent-primary)]"
          style={{ left: playhead * pxPerSecond }}
        />
      </div>

      <div className="min-h-0 flex-1 overflow-hidden rounded-[var(--radius-control)] border border-white/5">
        <Timeline
          ref={timelineRef}
          editorData={editorData}
          effects={EFFECTS}
          scale={1}
          scaleWidth={pxPerSecond}
          scaleSplitCount={4}
          rowHeight={32}
          gridSnap={snapEnabled}
          dragLine
          hideCursor
          style={{ width: '100%', height: '100%' }}
          onChange={handleChange}
          onClickAction={(event, { action }) => {
            event.stopPropagation();
            selectClip(String(action.id), event.shiftKey);
          }}
          onClickRow={(_event, { time }) => setPlayhead(time)}
          getActionRender={(action) => {
            const data = (action as unknown as { data?: { name?: string } }).data;
            return (
              <div className="flex h-full items-center truncate px-1.5 text-[10px] text-[var(--text-primary)]">
                {data?.name ?? translate(language, 'panel.media')}
              </div>
            );
          }}
        />
      </div>
    </div>
  );
}
