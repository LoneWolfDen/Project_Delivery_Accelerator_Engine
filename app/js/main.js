// Application entry point (BLD-01, UI-02). Later items add: diagnostics → storage → views.
// The Trusted Types policy is created first, before anything else can claim a sink (SEC-02).
import './core/trusted-types.js';
import { APP_VERSION } from '../version.js';
import { h, replace } from './ui/dom.js';
import { getState, update } from './ui/store.js';
import { startRouter, navigate } from './ui/router.js';
import { liveRegion, announce, focusHeading } from './ui/a11y.js';
import * as notBuilt from './ui/views/not-built.js';
import { log } from './diagnostics/log.js';
import { showError } from './ui/components/banner.js';
import { openDb } from './storage/db.js';

const APP_NAME = 'Project Delivery Accelerator';
const NAV = [['projects', 'Projects', '#/projects'], ['trash', 'Trash', '#/trash'], ['settings', 'Settings', '#/settings'], ['help', 'Help', '#/help']];
const VIEWS = { projects: notBuilt, project: notBuilt, settings: notBuilt, trash: notBuilt, help: notBuilt };

function header(main) {
  const skip = h('a', { class: 'skip-link', attrs: { href: '#app' }, on: { click: (e) => { e.preventDefault(); focusHeading(main); } } }, 'Skip to main content');
  const buttons = NAV.map(([name, label, hash]) => h('button', { class: 'nav-button', attrs: { type: 'button', 'data-route': name }, on: { click: () => navigate(hash) } }, label));
  const bar = h('header', { class: 'app-header' }, h('p', { class: 'app-name' }, APP_NAME), h('nav', { attrs: { 'aria-label': 'Main' } }, buttons), h('p', { class: 'app-version', id: 'app-version' }, `Version ${APP_VERSION}`));
  return [skip, bar];
}

function start() {
  // file:// guard: module scripts and storage don't work reliably from a file path,
  // so leave the boot message visible and render nothing (ADR-024).
  if (location.protocol === 'file:') return;
  // Uncaught errors: log the code only (never the message, which may contain content) and show a banner.
  const unexpected = () => {
    log('error', 'APP-UNEXPECTED', 'main');
    showError('APP-UNEXPECTED');
  };
  window.addEventListener('error', unexpected);
  window.addEventListener('unhandledrejection', unexpected);
  const main = document.getElementById('app');
  main.before(...header(main));
  document.body.append(liveRegion());
  let first = true;
  startRouter((route) => {
    update({ route });
    const view = VIEWS[route.name].render(route);
    replace(main, view);
    for (const b of document.querySelectorAll('.nav-button')) {
      if (b.dataset.route === route.name) b.setAttribute('aria-current', 'page');
      else b.removeAttribute('aria-current');
    }
    document.title = `${notBuilt.TITLES[route.name]} – ${APP_NAME}`;
    if (!first) { focusHeading(view); announce(`${notBuilt.TITLES[route.name]} page`); }
    first = false;
  });
  // Test-only hook for e2e (DAT-01): exposed only with ?test=1.
  if (new URLSearchParams(location.search).get('test') === '1') window.__pdaeTest = { openDb, getState };
  openDb().then(
    ({ db, readOnly }) => update({ db, readOnly }),
    (err) => showError(err.code ?? 'STO-OPEN-FAIL'),
  );
  document.getElementById('boot-msg').hidden = true;
  document.documentElement.dataset.ready = 'true';
}

start();
