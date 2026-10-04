// Visible error banner (DGN-01). Shows the catalogue title and help for a code, the code itself,
// and a 'Copy diagnostic code' button. One banner per code; showing it again replaces the old one.
import { h } from '../dom.js';
import { getError } from '../../diagnostics/errors.js';
import { announce } from '../a11y.js';

function region() {
  let el = document.getElementById('banner-region');
  if (!el) {
    el = h('div', { id: 'banner-region', class: 'banner-region' });
    document.getElementById('app').before(el);
  }
  return el;
}

async function copyCode(button, code) {
  try {
    await navigator.clipboard.writeText(code);
    button.textContent = 'Copied';
    announce(`Diagnostic code ${code} copied`);
  } catch {
    button.textContent = `Copy failed – the code is ${code}`;
  }
}

// detail: optional short plain-text line (shown, never logged).
export function showError(code, detail) {
  const entry = getError(code);
  const shownCode = entry.code;
  const existing = document.querySelector(`.banner[data-code="${shownCode}"]`);
  const copy = h('button', { class: 'banner-button', attrs: { type: 'button' }, on: { click: () => copyCode(copy, shownCode) } }, 'Copy diagnostic code');
  const dismiss = h('button', { class: 'banner-button', attrs: { type: 'button' }, on: { click: () => banner.remove() } }, 'Dismiss');
  const banner = h(
    'div',
    { class: 'banner banner-error', attrs: { role: 'alert', 'data-code': shownCode } },
    h('p', { class: 'banner-title' }, entry.title),
    h('p', { class: 'banner-help' }, entry.help),
    detail ? h('p', { class: 'banner-detail' }, String(detail)) : null,
    h('p', { class: 'banner-code' }, 'Diagnostic code: ', h('code', {}, shownCode)),
    h('div', { class: 'banner-actions' }, copy, dismiss),
  );
  if (existing) existing.replaceWith(banner);
  else region().append(banner);
  return banner;
}
