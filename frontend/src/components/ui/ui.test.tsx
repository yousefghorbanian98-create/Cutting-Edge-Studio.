import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { Button } from './Button';
import { CommandPalette } from './CommandPalette';
import { Modal } from './Modal';
import { ProgressBar } from './ProgressBar';
import { Slider } from './Slider';
import { Stepper } from './Stepper';
import { Switch } from './Switch';

describe('Button', () => {
  it('exposes loading state and blocks clicks while busy', async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Save
      </Button>,
    );
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
    // The spinner is decorative: aria-busy on the button already carries the state.
    expect(screen.queryByRole('status')).toBeNull();
    await userEvent.click(button, { pointerEventsCheck: 0 });
    expect(onClick).not.toHaveBeenCalled();
  });

  it('maps tone to aria-invalid for error states', () => {
    render(<Button tone="error">Retry</Button>);
    expect(screen.getByRole('button', { name: 'Retry' })).toHaveAttribute('aria-invalid', 'true');
  });

  it('calls onClick when idle', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Run</Button>);
    await userEvent.click(screen.getByRole('button', { name: 'Run' }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe('ProgressBar', () => {
  it('reports aria value and clamps out-of-range input', () => {
    render(<ProgressBar value={250} max={100} label="Analysis" hint="stage 3 of 11" />);
    const bar = screen.getByRole('progressbar', { name: 'Analysis' });
    expect(bar).toHaveAttribute('aria-valuenow', '100');
    expect(screen.getByText('stage 3 of 11')).toBeInTheDocument();
  });

  it('never divides by zero', () => {
    render(<ProgressBar value={5} max={0} label="Empty" />);
    expect(screen.getByRole('progressbar', { name: 'Empty' })).toHaveAttribute('aria-valuenow', '0');
  });
});

describe('Modal', () => {
  it('renders an accessible dialog and closes from the X button', async () => {
    function Harness() {
      const [open, setOpen] = useState(true);
      return (
        <Modal open={open} onOpenChange={setOpen} title="Confirm export" description="Renders 1080p NVENC">
          <p>body</p>
        </Modal>
      );
    }
    render(<Harness />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Confirm export')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'close' }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});

describe('Stepper', () => {
  it('marks the active step and reports clicks', async () => {
    const onSelect = vi.fn();
    render(
      <Stepper
        steps={[
          { id: 'a', label: 'One' },
          { id: 'b', label: 'Two' },
        ]}
        currentIndex={1}
        onSelect={onSelect}
      />,
    );
    expect(screen.getByRole('button', { name: '2. Two' })).toHaveAttribute('aria-current', 'step');
    expect(screen.getByRole('button', { name: '1. One' })).not.toHaveAttribute('aria-current');
    await userEvent.click(screen.getByRole('button', { name: '1. One' }));
    expect(onSelect).toHaveBeenCalledWith(0);
  });
});

describe('Switch and Slider', () => {
  it('toggles through the primitive', async () => {
    function Harness() {
      const [checked, setChecked] = useState(false);
      return <Switch checked={checked} onCheckedChange={setChecked} label="Enable GPU" />;
    }
    render(<Harness />);
    const toggle = screen.getByRole('switch', { name: 'Enable GPU' });
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-checked', 'true');
  });

  it('labels the slider thumb', () => {
    render(<Slider value={30} onValueChange={() => undefined} label="Intensity" />);
    expect(screen.getByRole('slider', { name: 'Intensity' })).toBeInTheDocument();
  });
});

describe('CommandPalette', () => {
  it('renders actions when open and runs the selected one', async () => {
    const run = vi.fn();
    render(
      <CommandPalette
        open
        onOpenChange={() => undefined}
        label="Commands"
        placeholder="Search"
        actions={[{ id: 'x', label: 'Toggle theme', hint: 'pro', onRun: run }]}
      />,
    );
    expect(screen.getByPlaceholderText('Search')).toBeInTheDocument();
    await userEvent.click(screen.getByText('Toggle theme'));
    expect(run).toHaveBeenCalledTimes(1);
  });

  it('renders nothing when closed', () => {
    render(
      <CommandPalette open={false} onOpenChange={() => undefined} label="Commands" actions={[]} />,
    );
    expect(screen.queryByLabelText('Commands')).toBeNull();
  });
});
