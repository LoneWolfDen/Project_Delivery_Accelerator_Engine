// Accessibility helpers (UI-02): polite live-region announcements and view focus.
import { h } from './dom.js';

let region = null;

// Create the aria-live region once; main.js appends it to the page.
export function liveRegion() {
  region ??= h('div', { id: 'live-region', class: 'visually-hidden', attrs: { 'aria-live': 'polite', role: 'status' } });
  return region;
}

// Announce text to screen readers. Clearing first makes a repeated message announce again.
export function announce(text) {
  const r = liveRegion();
  r.textContent = '';
  setTimeout(() => {
    r.textContent = String(text);
  }, 50);
}

// Move keyboard focus to the view's <h1> (made focusable without entering the Tab order).
export function focusHeading(view) {
  const heading = view?.querySelector('h1');
  if (!heading) return;
  heading.setAttribute('tabindex', '-1');
  heading.focus();
}
