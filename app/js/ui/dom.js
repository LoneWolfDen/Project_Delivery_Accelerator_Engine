// Safe DOM builder (UI-01, ADR-010; TARGET_ARCHITECTURE.md §23).
// The only way views create elements. Strings always become text nodes, never markup.
// Attributes go through setAttribute with checks: no event-handler attributes, no style,
// no srcdoc, and URL attributes must be same-origin relative ('./…', '#…') or 'blob:'.
// Event listeners are attached with addEventListener via the `on` prop.

const BLOCKED_TAGS = new Set(['script', 'iframe', 'frame', 'object', 'embed', 'style', 'link', 'meta', 'base']);
const BLOCKED_ATTRS = new Set(['style', 'srcdoc', 'srcset', 'is']);
const URL_ATTRS = new Set(['href', 'src', 'action', 'formaction', 'poster', 'cite', 'data', 'xlink:href']);
// Links to the OpenRouter site are added when app/js/ai/openrouter.js exists (AI-02, decision BD-21).
const URL_PREFIXES = ['./', '#', 'blob:'];
const NAME_RE = /^[a-z][a-z0-9-]*$/;
const ATTR_RE = /^[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?$/;
const PROPS = new Set(['class', 'id', 'attrs', 'on']);

function checkUrl(name, value) {
  if (!URL_PREFIXES.some((p) => value.startsWith(p))) {
    throw new TypeError(`Unsafe URL in ${name}: only './', '#' or 'blob:' URLs are allowed`);
  }
}

function setAttr(el, name, value) {
  if (value === false || value === null || value === undefined) return;
  if (typeof name !== 'string' || !ATTR_RE.test(name)) throw new TypeError(`Invalid attribute name: ${String(name)}`);
  if (name.startsWith('on')) throw new TypeError(`Event-handler attribute not allowed: ${name}; use the 'on' prop`);
  if (BLOCKED_ATTRS.has(name)) throw new TypeError(`Attribute not allowed: ${name}`);
  const text = value === true ? '' : String(value);
  if (URL_ATTRS.has(name)) checkUrl(name, text);
  el.setAttribute(name, text);
}

function appendChildren(el, children) {
  for (const child of children) {
    if (child === null || child === undefined || child === false) continue;
    if (Array.isArray(child)) appendChildren(el, child);
    else if (child instanceof Node) el.append(child);
    else if (typeof child === 'string' || typeof child === 'number') el.append(document.createTextNode(String(child)));
    else throw new TypeError(`Unsupported child: ${typeof child}`);
  }
}

// h('button', { class: 'primary', attrs: { type: 'button' }, on: { click: save } }, 'Save')
export function h(tag, props = {}, ...children) {
  if (typeof tag !== 'string' || !NAME_RE.test(tag)) throw new TypeError(`Invalid tag: ${String(tag)}`);
  if (BLOCKED_TAGS.has(tag)) throw new TypeError(`Tag not allowed: ${tag}`);
  const el = document.createElement(tag);
  const p = props ?? {};
  for (const key of Object.keys(p)) {
    if (!PROPS.has(key)) throw new TypeError(`Unknown prop: ${key}`);
  }
  if (p.class !== undefined) el.className = Array.isArray(p.class) ? p.class.filter(Boolean).join(' ') : String(p.class);
  if (p.id !== undefined) el.id = String(p.id);
  for (const [name, value] of Object.entries(p.attrs ?? {})) setAttr(el, name, value);
  for (const [type, listener] of Object.entries(p.on ?? {})) {
    if (typeof listener !== 'function') throw new TypeError(`Listener for ${type} must be a function`);
    el.addEventListener(type, listener);
  }
  appendChildren(el, children);
  return el;
}

// Remove all children of el.
export function clear(el) {
  el.replaceChildren();
  return el;
}

// Replace all children of el with the given children (same rules as h()).
export function replace(el, ...children) {
  clear(el);
  appendChildren(el, children);
  return el;
}
