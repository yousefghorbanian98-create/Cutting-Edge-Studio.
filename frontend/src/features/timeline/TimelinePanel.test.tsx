import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTimelineStore } from './timelineStore';

// The editor renders a virtualized canvas-ish surface; in jsdom we assert our own
// wiring (data mapping, toolbar, hotkeys) and stub the third-party surface.
vi.mock('@xzdarcy/react-timeline-editor', () => ({
  Timeline: ({ editorData, onClickRow, onClickAction }: {
    editorData: { id: string; actions: { id: string; start: number; end: number }[] }[];
    onClickRow?: (event: unknown, param: { row: unknown; time: number }) => void;
    onClickAction?: (event: { stopPropagation: () => void; shiftKey: boolean }, param: { action: { id: string }; row: unknown; time: number }) => void;
  }) => (
    <div data-testid="editor-surface">
      {editorData.map((row) => (
        <div key={row.id} data-testid={`row-${row.id}`}>
          {row.actions.map((action) => (
            <button
              key={action.id}
              type="button"
              data-testid={`action-${action.id}`}
              onClick={(event) =>
                onClickAction?.({ stopPropagation: () => undefined, shiftKey: event.shiftKey }, {
                  action,
                  row,
                  time: action.start,
                })
              }
            >
              {`${action.start}-${action.end}`}
            </button>
          ))}
        </div>
      ))}
      <button type="button" data-testid="row-click" onClick={() => onClickRow?.({}, { row: {}, time: 3 })}>
        seek
      </button>
    </div>
  ),
}));

const { TimelinePanel } = await import('./TimelinePanel');

beforeEach(() => {
  useTimelineStore.getState().reset();
});

afterEach(() => {
  useTimelineStore.getState().reset();
});

describe('TimelinePanel', () => {
  it('renders one row per track and maps clips to actions', () => {
    useTimelineStore.getState().addClip({ mediaId: '/m/a.mp4', name: 'a.mp4', kind: 'video', at: 2 });
    render(<TimelinePanel />);
    expect(screen.getByTestId('row-v1')).toBeInTheDocument();
    expect(screen.getByTestId('row-v2')).toBeInTheDocument();
    expect(screen.getByTestId('row-a1')).toBeInTheDocument();
    expect(screen.getByText('2-7')).toBeInTheDocument();
  });

  it('shows the playhead timecode and keeps it in sync with the store', async () => {
    useTimelineStore.getState().setPlayhead(65);
    render(<TimelinePanel />);
    expect(screen.getByTestId('timecode')).toHaveTextContent('00:01:05:00');
  });

  it('seeks when a row is clicked', async () => {
    render(<TimelinePanel />);
    await userEvent.click(screen.getByTestId('row-click'));
    expect(useTimelineStore.getState().playhead).toBe(3);
  });

  it('selects an action through the editor callback', async () => {
    const clip = useTimelineStore.getState().addClip({ mediaId: '/m/a.mp4', name: 'a.mp4', kind: 'video', at: 0 });
    render(<TimelinePanel />);
    await userEvent.click(screen.getByTestId(`action-${clip?.id}`));
    expect(useTimelineStore.getState().selectedIds).toEqual([clip?.id]);
  });

  it('adds a bookmark, splits and deletes from the toolbar', async () => {
    const clip = useTimelineStore.getState().addClip({ mediaId: '/m/a.mp4', name: 'a.mp4', kind: 'video', at: 0 });
    useTimelineStore.getState().setPlayhead(2);
    render(<TimelinePanel />);

    await userEvent.click(screen.getByRole('button', { name: 'add-bookmark' }));
    expect(useTimelineStore.getState().bookmarks).toHaveLength(1);

    await userEvent.click(screen.getByRole('button', { name: 'split' }));
    expect(useTimelineStore.getState().clips).toHaveLength(2);

    useTimelineStore.getState().selectClip(String(clip?.id));
    await userEvent.click(screen.getByRole('button', { name: 'delete-selected' }));
    expect(useTimelineStore.getState().clips).toHaveLength(1);
  });

  it('toggles snapping and zooms through the toolbar', async () => {
    render(<TimelinePanel />);
    const snap = screen.getByRole('button', { name: 'toggle-snap' });
    expect(snap).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(snap);
    expect(useTimelineStore.getState().snapEnabled).toBe(false);

    const before = useTimelineStore.getState().pxPerSecond;
    await userEvent.click(screen.getByRole('button', { name: 'zoom-in' }));
    expect(useTimelineStore.getState().pxPerSecond).toBeGreaterThan(before);
  });

  it('responds to the M hotkey with a bookmark', async () => {
    useTimelineStore.getState().setPlayhead(7);
    render(<TimelinePanel />);
    await userEvent.keyboard('m');
    expect(useTimelineStore.getState().bookmarks[0]?.time).toBe(7);
  });

  it('exposes the playhead as an accessible slider', () => {
    useTimelineStore.getState().setPlayhead(12);
    render(<TimelinePanel />);
    const slider = screen.getByRole('slider', { name: 'playhead' });
    expect(slider).toHaveAttribute('aria-valuenow', '12');
  });
});
