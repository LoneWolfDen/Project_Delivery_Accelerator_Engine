// Forbidden-API and fabrication guard (SEC-01, ADR-008, ADR-010).
// Scans app/**/*.{js,mjs,html,css} (app/vendor/** skipped: verified by hash instead) and
// fails with `file:line rule-id message` on HTML sinks, dynamic code, network APIs and
// absolute URLs outside their allow-lists, web storage outside app/js/ui/prefs.js,
// and canned/fabricated answer text.
//
// Known limits (regex per line, no AST, by design):
// - Comments and strings are scanned too: a forbidden word in a comment fails the check.
//   That is intentional (stricter, never looser); reword the comment.
// - Code split across lines or built by string concatenation (el['inner' + 'HTML'],
//   window['ev' + 'al']) is not detected. Code review and CSP/Trusted Types (SEC-02)
//   are the second line of defence.
// - The checker never prints the offending line, only file, line number and rule.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SCAN_DIR = 'app';
const SKIP = ['app/vendor'];
const EXTS = ['.js', '.mjs', '.html', '.css'];

const JS = ['.js', '.mjs'];
const HTML = ['.html'];
const ALL = EXTS;

const NETWORK_ALLOW = ['app/sw.js', 'app/js/ai/openrouter.js'];
const OPENROUTER_ALLOW = ['app/index.html', 'app/js/ai/openrouter.js'];
const NAMESPACE_URIS = ['http://www.w3.org/2000/svg', 'http://www.w3.org/1999/xhtml'];
const NAMESPACE_PREFIXES = ['http://schemas.openxmlformats.org/'];

export const FABRICATION_PHRASES = [
  'lorem ipsum',
  'demo answer',
  'sample response',
  'as an ai',
  'mock data',
  'mock_data',
  'placeholder answer',
];

const onlyIn = (files) => (file) => files.includes(file);

function urlAllowed(file, url) {
  if (OPENROUTER_ALLOW.includes(file) && (url === 'https://openrouter.ai' || url.startsWith('https://openrouter.ai/'))) {
    return true;
  }
  if (file.startsWith('app/js/')) {
    if (NAMESPACE_URIS.includes(url)) return true;
    if (NAMESPACE_PREFIXES.some((p) => url.startsWith(p))) return true;
  }
  return false;
}

// Each rule: id, message, pattern (global regex), appliesTo (extensions),
// allow(file, matchText) → true when this match is permitted in this file.
export const RULES = [
  { id: 'FA-01', message: 'innerHTML is forbidden; build DOM with app/js/ui/dom.js', pattern: /\binnerHTML\b/g, appliesTo: JS },
  { id: 'FA-02', message: 'outerHTML is forbidden', pattern: /\bouterHTML\b/g, appliesTo: JS },
  { id: 'FA-03', message: 'insertAdjacentHTML is forbidden', pattern: /\binsertAdjacentHTML\b/g, appliesTo: JS },
  { id: 'FA-04', message: 'document.write is forbidden', pattern: /\bdocument\s*\.\s*write(?:ln)?\b/g, appliesTo: JS },
  { id: 'FA-05', message: 'eval is forbidden', pattern: /\beval\s*\(|\[\s*['"`]eval['"`]\s*\]/g, appliesTo: JS },
  { id: 'FA-06', message: 'new Function is forbidden', pattern: /\bnew\s+Function\s*\(/g, appliesTo: JS },
  { id: 'FA-07', message: 'setTimeout/setInterval with a string is forbidden; pass a function', pattern: /\bset(?:Timeout|Interval)\s*\(\s*['"`]/g, appliesTo: JS },
  { id: 'FA-08', message: 'inline event handler attribute is forbidden', pattern: /<[^>]*\son[a-z]+\s*=/gi, appliesTo: HTML },
  { id: 'FA-09', message: 'inline <script> without src is forbidden', pattern: /<script\b(?![^>]*\bsrc\s*=)[^>]*>/gi, appliesTo: HTML },
  { id: 'FA-10', message: 'style= attribute is forbidden; use a stylesheet class', pattern: /<[^>]*\sstyle\s*=/gi, appliesTo: HTML },
  { id: 'NET-01', message: 'fetch is only allowed in app/sw.js and app/js/ai/openrouter.js', pattern: /\bfetch\b/g, appliesTo: JS, allow: onlyIn(NETWORK_ALLOW) },
  { id: 'NET-02', message: 'XMLHttpRequest is only allowed in app/sw.js and app/js/ai/openrouter.js', pattern: /\bXMLHttpRequest\b/g, appliesTo: JS, allow: onlyIn(NETWORK_ALLOW) },
  { id: 'NET-03', message: 'WebSocket is only allowed in app/sw.js and app/js/ai/openrouter.js', pattern: /\bWebSocket\b/g, appliesTo: JS, allow: onlyIn(NETWORK_ALLOW) },
  { id: 'NET-04', message: 'EventSource is only allowed in app/sw.js and app/js/ai/openrouter.js', pattern: /\bEventSource\b/g, appliesTo: JS, allow: onlyIn(NETWORK_ALLOW) },
  { id: 'NET-05', message: 'sendBeacon is only allowed in app/sw.js and app/js/ai/openrouter.js', pattern: /\bsendBeacon\b/g, appliesTo: JS, allow: onlyIn(NETWORK_ALLOW) },
  { id: 'NET-06', message: 'absolute URL outside the allow-list', pattern: /\b(?:https?|wss?):\/\/[^\s'"`)<>,;]*/gi, appliesTo: ALL, allow: urlAllowed },
  { id: 'STO-01', message: 'localStorage/sessionStorage only allowed in app/js/ui/prefs.js', pattern: /\b(?:localStorage|sessionStorage)\b/g, appliesTo: JS.concat(HTML), allow: onlyIn(['app/js/ui/prefs.js']) },
  {
    id: 'FAB-01',
    message: 'fabricated/canned answer phrase is forbidden',
    pattern: new RegExp(FABRICATION_PHRASES.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'gi'),
    appliesTo: ALL,
  },
];

// Scan one file's text. `file` is the repo-relative path with forward slashes.
export function scanFile(file, text) {
  const ext = path.extname(file).toLowerCase();
  const violations = [];
  const lines = String(text).split(/\r?\n/);
  for (const rule of RULES) {
    if (!rule.appliesTo.includes(ext)) continue;
    lines.forEach((line, i) => {
      for (const m of line.matchAll(rule.pattern)) {
        if (rule.allow && rule.allow(file, m[0])) continue;
        violations.push({ file, line: i + 1, rule: rule.id, message: rule.message });
        break; // one report per rule per line
      }
    });
  }
  return violations.sort((a, b) => a.line - b.line || a.rule.localeCompare(b.rule));
}

function walk(root, dir, out) {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    const rel = path.relative(root, full).split(path.sep).join('/');
    if (SKIP.some((s) => rel === s || rel.startsWith(s + '/'))) continue;
    if (entry.isDirectory()) walk(root, full, out);
    else if (EXTS.includes(path.extname(entry.name).toLowerCase())) out.push(rel);
  }
  return out;
}

// Scan app/ under `root` (default: this repository). Returns scanned files and violations.
export function scanRepo(root = REPO_ROOT) {
  const files = walk(root, path.join(root, SCAN_DIR), []);
  const violations = files.flatMap((rel) => scanFile(rel, fs.readFileSync(path.join(root, rel), 'utf8')));
  return { files, violations };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const { files, violations } = scanRepo();
  for (const v of violations) console.error(`${v.file}:${v.line}: ${v.rule} ${v.message}`);
  console.log(`check-forbidden-apis: ${files.length} file(s) scanned, ${violations.length} violation(s)`);
  process.exit(violations.length ? 1 : 0);
}
