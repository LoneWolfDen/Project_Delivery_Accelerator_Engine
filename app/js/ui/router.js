// Hash router (UI-02). Routes: #/projects, #/project/:id/:tab, #/settings, #/trash, #/help.
// Anything else is replaced with #/projects (no history entry added).

export const DEFAULT_HASH = '#/projects';
export const DEFAULT_PROJECT_TAB = 'sources';
const ID_RE = /^[A-Za-z0-9_-]{1,64}$/;
const TAB_RE = /^[a-z-]{1,32}$/;

// Parse a location hash into { name, params } or null when it is not a known route.
export function parseHash(hash) {
  const parts = String(hash || '').replace(/^#\/?/, '').split('/');
  const [first, id, tab, ...rest] = parts;
  if (['projects', 'settings', 'trash', 'help'].includes(first) && parts.length === 1) {
    return { name: first, params: {} };
  }
  if (first === 'project' && ID_RE.test(id ?? '') && rest.length === 0) {
    if (tab === undefined) return { name: 'project', params: { id, tab: DEFAULT_PROJECT_TAB } };
    if (TAB_RE.test(tab)) return { name: 'project', params: { id, tab } };
  }
  return null;
}

export function navigate(hash) {
  if (location.hash === hash) return;
  location.hash = hash;
}

// Call onRoute(route) now and on every hash change. Unknown hashes are replaced with the default.
export function startRouter(onRoute) {
  const handle = () => {
    const route = parseHash(location.hash);
    if (!route) {
      location.replace(DEFAULT_HASH);
      return;
    }
    onRoute(route);
  };
  window.addEventListener('hashchange', handle);
  handle();
  return () => window.removeEventListener('hashchange', handle);
}
