// Application entry point (BLD-01). Later items add: diagnostics → storage → router → views.
import { APP_VERSION } from '../version.js';

const APP_NAME = 'Project Delivery Accelerator';

function start() {
  // file:// guard: module scripts and storage don't work reliably from a file path,
  // so leave the boot message visible and render nothing (ADR-024).
  if (location.protocol === 'file:') return;

  const app = document.getElementById('app');
  const title = document.createElement('h1');
  title.textContent = APP_NAME;
  const version = document.createElement('p');
  version.className = 'app-version';
  version.id = 'app-version';
  version.textContent = `Version ${APP_VERSION}`;
  app.replaceChildren(title, version);

  document.getElementById('boot-msg').hidden = true;
  document.documentElement.dataset.ready = 'true';
}

start();
