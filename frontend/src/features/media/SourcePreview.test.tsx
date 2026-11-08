import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { SourcePreview } from './SourcePreview';
import { useMediaStore } from '../../store/mediaStore';

afterEach(() => useMediaStore.getState().clear());
function select() {
  useMediaStore.setState({ clips: [{
    id: 'a1', assetId: 'a1', name: 'source.mp4', path: '/local/a.mp4', size: 20,
    kind: 'video', role: 'source',
  }], selectedId: 'a1' });
}
it('plays registered media through the same-origin asset endpoint', () => {
  select(); render(<SourcePreview />);
  const player = screen.getByLabelText('source.mp4');
  expect(player).toHaveAttribute('src', '/api/v1/assets/a1/content');
  expect(player).toHaveAttribute('controls');
  expect(player).not.toHaveAttribute('autoplay');
});
it('shows a visible error for unsupported playback', () => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
  select(); render(<SourcePreview />);
  fireEvent.error(screen.getByLabelText('source.mp4'));
  expect(screen.getByRole('alert')).toBeInTheDocument();
});
