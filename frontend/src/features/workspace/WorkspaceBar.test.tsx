import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError } from '../../lib/api';
import { useAppStore } from '../../store/useAppStore';
import { useMediaStore } from '../../store/mediaStore';
import { useTimelineStore } from '../../store/timelineStore';
import { usePostStore } from '../../store/postStore';
import { useWizardStore } from '../../store/wizardStore';
import { WorkspaceBar } from './WorkspaceBar';
import { useWorkspaceStore } from '../../store/workspaceStore';

beforeEach(() => {
  vi.useFakeTimers();
  localStorage.clear();
  useAppStore.getState().setLanguage('en');
  useTimelineStore.getState().reset();
  usePostStore.getState().reset();
  useWizardStore.getState().reset();
  useMediaStore.getState().clear();
  useMediaStore.setState({ projectId: 'project-1', projectName: 'Match' });
  useWorkspaceStore.setState({
    initialized: true,
    navigating: false,
    dirty: false,
    generation: 0,
    status: 'idle',
    error: null,
    warning: null,
    conflict: false,
    revision: 'a'.repeat(64),
    revisionProject: 'project-1',
    projects: [],
  });
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
});
afterEach(() => vi.useRealTimers());

it('debounces automatic SQLite saves and marks success only after the response', async () => {
  const save = vi
    .spyOn(api, 'saveWorkspace')
    .mockImplementation(async (_id, _revision, name, snapshot) => ({ name, snapshot, revision: 'b'.repeat(64) }));
  render(<WorkspaceBar />);
  fireEvent.change(screen.getByLabelText('Project name'), { target: { value: 'مسابقهٔ نهایی' } });
  expect(screen.getByTestId('workspace-status')).toHaveTextContent('Unsaved changes');
  await act(() => vi.advanceTimersByTimeAsync(799));
  expect(save).not.toHaveBeenCalled();
  await act(() => vi.advanceTimersByTimeAsync(1));
  expect(save).toHaveBeenCalledOnce();
  expect(save.mock.calls[0]?.[2]).toBe('مسابقهٔ نهایی');
  expect(screen.getByTestId('workspace-status')).toHaveTextContent('Saved locally');
});

it('keeps unsaved changes visible on failure, does not loop retries and supports Save retry', async () => {
  const save = vi.spyOn(api, 'saveWorkspace').mockRejectedValue(new Error('disk offline'));
  render(<WorkspaceBar />);
  fireEvent.change(screen.getByLabelText('Project name'), { target: { value: 'Unsaved' } });
  await act(() => vi.advanceTimersByTimeAsync(800));
  expect(screen.getByRole('alert')).toHaveTextContent('disk offline');
  expect(useWorkspaceStore.getState().dirty).toBe(true);
  await act(() => vi.advanceTimersByTimeAsync(5000));
  expect(save).toHaveBeenCalledOnce();
  save.mockImplementation(async (_id, _revision, name, snapshot) => ({ name, snapshot, revision: 'b'.repeat(64) }));
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Save project' }));
  });
  expect(save).toHaveBeenCalledTimes(2);
  expect(screen.getByTestId('workspace-status')).toHaveTextContent('Saved locally');
});

it('warns before closing an unsaved document and removes the warning after save', () => {
  render(<WorkspaceBar />);
  fireEvent.change(screen.getByLabelText('Project name'), { target: { value: 'Unsaved' } });
  const dirtyClose = new Event('beforeunload', { cancelable: true });
  window.dispatchEvent(dirtyClose);
  expect(dirtyClose.defaultPrevented).toBe(true);
  act(() => useWorkspaceStore.setState({ dirty: false }));
  const cleanClose = new Event('beforeunload', { cancelable: true });
  window.dispatchEvent(cleanClose);
  expect(cleanClose.defaultPrevented).toBe(false);
});

it('blocks conflicting autosaves and requires confirmation before discarding local edits', async () => {
  vi.spyOn(api, 'saveWorkspace').mockRejectedValue(new ApiError('Changed elsewhere', 409));
  const read = vi
    .spyOn(api, 'getWorkspace')
    .mockResolvedValue({ name: 'Other tab', revision: 'c'.repeat(64), snapshot: null });
  vi.spyOn(api, 'listAssets').mockResolvedValue([]);
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
  render(<WorkspaceBar />);
  fireEvent.change(screen.getByLabelText('Project name'), { target: { value: 'Local edits' } });
  await act(() => vi.advanceTimersByTimeAsync(800));
  expect(screen.getByRole('button', { name: 'Save project' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Reopen saved' }));
  expect(confirm).toHaveBeenCalledOnce();
  expect(read).not.toHaveBeenCalled();
  expect(useMediaStore.getState().projectName).toBe('Local edits');
  confirm.mockReturnValue(true);
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Reopen saved' }));
  });
  expect(useMediaStore.getState().projectName).toBe('Other tab');
  expect(useWorkspaceStore.getState().dirty).toBe(false);
});

it('does not call an empty workspace saved, and exposes missing-media warnings', () => {
  useMediaStore.setState({ projectId: null });
  const { unmount } = render(<WorkspaceBar />);
  expect(screen.getByTestId('workspace-status')).toHaveTextContent('No project open');
  unmount();
  useMediaStore.setState({
    projectId: 'project-1',
    clips: [
      {
        id: 'missing',
        path: '/missing.mp4',
        name: 'missing.mp4',
        size: 1,
        kind: 'video',
        role: 'source',
        available: false,
      },
    ],
  });
  render(<WorkspaceBar />);
  expect(screen.getByRole('alert')).toHaveTextContent('Some media files are unavailable');
});
