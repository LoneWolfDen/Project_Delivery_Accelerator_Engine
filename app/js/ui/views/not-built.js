// Placeholder for views that are not built yet (UI-02). Shows no sample data.
import { h } from '../dom.js';

export const TITLES = Object.freeze({
  projects: 'Projects',
  project: 'Project',
  settings: 'Settings',
  trash: 'Trash',
  help: 'Help',
});

export function render(route) {
  return h(
    'section',
    { class: 'view', attrs: { 'aria-labelledby': 'view-title' } },
    h('h1', { id: 'view-title' }, TITLES[route.name] ?? 'Page'),
    h('p', { class: 'not-built' }, "This part isn't built yet."),
  );
}
