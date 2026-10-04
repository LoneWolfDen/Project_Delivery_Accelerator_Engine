// Trusted Types policy (SEC-02, ADR-010; TARGET_ARCHITECTURE.md §23).
// The CSP requires Trusted Types for script sinks and allows only this one policy.
// There is no HTML policy: any string written to an HTML sink throws.
// navigator.serviceWorker.register() and new Worker() are script-URL sinks, so their
// URLs must come from scriptURL(), which accepts only the fixed allow-list below.

export const ALLOWED_SCRIPT_URLS = Object.freeze(['./sw.js']);

function checkAllowed(url) {
  if (!ALLOWED_SCRIPT_URLS.includes(url)) {
    throw new TypeError(`Script URL not allowed: ${String(url)}`);
  }
  return url;
}

const policy =
  typeof window !== 'undefined' && window.trustedTypes
    ? window.trustedTypes.createPolicy('pdae-script-url', { createScriptURL: checkAllowed })
    : null;

// Returns a TrustedScriptURL for an allow-listed path (or the plain string where the
// browser has no Trusted Types). Throws for anything else.
export function scriptURL(path) {
  return policy ? policy.createScriptURL(path) : checkAllowed(path);
}
