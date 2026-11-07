import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// jsdom lacks these browser APIs; Radix popovers/sliders observe element size.
class ResizeObserverStub {
  observe(): void {
    return undefined;
  }
  unobserve(): void {
    return undefined;
  }
  disconnect(): void {
    return undefined;
  }
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
globalThis.DOMRect ??= class {
  constructor(
    public x = 0,
    public y = 0,
    public width = 0,
    public height = 0,
  ) {}
  static fromRect(): DOMRect {
    return new DOMRect() as DOMRect;
  }
  get top(): number {
    return this.y;
  }
  get left(): number {
    return this.x;
  }
  get bottom(): number {
    return this.y + this.height;
  }
  get right(): number {
    return this.x + this.width;
  }
  toJSON(): Record<string, number> {
    return { x: this.x, y: this.y, width: this.width, height: this.height };
  }
} as unknown as typeof DOMRect;
globalThis.PointerEvent ??= MouseEvent as unknown as typeof PointerEvent;
Element.prototype.scrollIntoView = () => undefined;
Element.prototype.hasPointerCapture = () => false;
Element.prototype.releasePointerCapture = () => undefined;

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  document.documentElement.lang = 'fa';
  document.documentElement.dir = 'rtl';
});
