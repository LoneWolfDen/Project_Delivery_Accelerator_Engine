// Unit tests for tools/check-forbidden-apis.mjs (SEC-01).
// Every rule has at least one failing sample and one passing sample.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { RULES, scanFile, scanRepo } from '../../tools/check-forbidden-apis.mjs';

const ids = (file, text) => scanFile(file, text).map((v) => v.rule);

// [rule id, file, failing text, passing text]
const CASES = [
  ['FA-01', 'app/js/x.js', 'el.innerHTML = x;', 'el.textContent = x;'],
  ['FA-02', 'app/js/x.js', 'el.outerHTML = x;', 'el.replaceWith(y);'],
  ['FA-03', 'app/js/x.js', "el.insertAdjacentHTML('beforeend', x);", "el.insertAdjacentElement('beforeend', y);"],
  ['FA-04', 'app/js/x.js', 'document.write(x);', 'document.title = x;'],
  ['FA-04', 'app/js/x.js', 'document.writeln(x);', 'doc.writer = x;'],
  ['FA-05', 'app/js/x.js', 'eval(code);', 'evaluate(code);'],
  ['FA-05', 'app/js/x.js', "window['eval'](code);", "window['evaluate'](code);"],
  ['FA-06', 'app/js/x.js', "const f = new Function('a', 'return a');", 'const f = function (a) { return a; };'],
  ['FA-07', 'app/js/x.js', "setTimeout('run()', 10);", 'setTimeout(run, 10);'],
  ['FA-07', 'app/js/x.js', 'setInterval(`tick()`, 10);', 'setInterval(() => tick(), 10);'],
  ['FA-08', 'app/index.html', '<button onclick="go()">Go</button>', '<button type="button" id="go">Go</button>'],
  ['FA-09', 'app/index.html', '<script>alert(1)</script>', '<script type="module" src="js/main.js"></script>'],
  ['FA-10', 'app/index.html', '<div style="color:red">x</div>', '<div class="warn">x</div>'],
  ['NET-01', 'app/js/x.js', 'fetch(url);', 'prefetchHint(url);'],
  ['NET-02', 'app/js/x.js', 'new XMLHttpRequest();', 'new XMLSerializer();'],
  ['NET-03', 'app/js/x.js', "new WebSocket('wss' + host);", 'new BroadcastChannel(name);'],
  ['NET-04', 'app/js/x.js', 'new EventSource(url);', 'new EventTarget();'],
  ['NET-05', 'app/js/x.js', 'navigator.sendBeacon(url, data);', 'navigator.storage.persist();'],
  ['NET-06', 'app/js/x.js', "const u = 'https://example.com/api';", "const u = './api';"],
  ['NET-06', 'app/styles.css', 'body { background: url(http://cdn.example.com/a.png); }', 'body { background: url(img/a.png); }'],
  ['NET-06', 'app/js/x.js', "const s = 'wss://example.com';", "const s = 'local';"],
  ['STO-01', 'app/js/x.js', "localStorage.setItem('k', v);", "prefs.set('k', v);"],
  ['STO-01', 'app/js/x.js', 'sessionStorage.clear();', 'session.clear();'],
  ['FAB-01', 'app/js/x.js', "const a = 'Lorem ipsum dolor';", "const a = 'No answer found in your documents';"],
  ['FAB-01', 'app/js/x.js', "const t = 'Demo answer: all good';", "const t = 'Answer';"],
  ['FAB-01', 'app/js/x.js', 'return SAMPLE RESPONSE;', 'return response;'],
  ['FAB-01', 'app/index.html', '<p>As an AI language model</p>', '<p>Assistant</p>'],
  ['FAB-01', 'app/js/x.js', 'const rows = MOCK_DATA;', 'const rows = data;'],
  ['FAB-01', 'app/js/x.js', '// uses mock data', '// uses stored data'],
  ['FAB-01', 'app/styles.css', '/* placeholder answer */', '/* answer panel */'],
];

for (const [id, file, bad, good] of CASES) {
  test(`${id} fails on: ${bad}`, () => {
    assert.ok(ids(file, bad).includes(id), `expected ${id} in ${JSON.stringify(ids(file, bad))}`);
  });
  test(`${id} passes on: ${good}`, () => {
    assert.deepEqual(ids(file, good), []);
  });
}

test('every rule has a failing-sample test', () => {
  const tested = new Set(CASES.map((c) => c[0]));
  for (const rule of RULES) assert.ok(tested.has(rule.id), `${rule.id} has no test case`);
});

test('violations report file, 1-based line and rule id', () => {
  const v = scanFile('app/js/x.js', 'const a = 1;\nconst b = 2;\nel.innerHTML = a;');
  assert.deepEqual(v, [{ file: 'app/js/x.js', line: 3, rule: 'FA-01', message: v[0].message }]);
});

test('network APIs are allowed only in app/sw.js and app/js/ai/openrouter.js', () => {
  assert.deepEqual(ids('app/sw.js', 'event.respondWith(fetch(event.request));'), []);
  assert.deepEqual(ids('app/js/ai/openrouter.js', 'await fetch(endpoint, options);'), []);
  assert.deepEqual(ids('app/js/ai/other.js', 'await fetch(endpoint, options);'), ['NET-01']);
});

test('openrouter URL is allowed only in app/index.html and app/js/ai/openrouter.js', () => {
  const csp = '<meta http-equiv="Content-Security-Policy" content="connect-src \'self\' https://openrouter.ai">';
  assert.deepEqual(ids('app/index.html', csp), []);
  assert.deepEqual(ids('app/js/ai/openrouter.js', "const BASE = 'https://openrouter.ai/api/v1';"), []);
  assert.deepEqual(ids('app/js/ui/x.js', "const BASE = 'https://openrouter.ai/api/v1';"), ['NET-06']);
  // A lookalike domain must not slip through the allow-list.
  assert.deepEqual(ids('app/js/ai/openrouter.js', "const BASE = 'https://openrouter.ai.evil.example/';"), ['NET-06']);
  assert.deepEqual(ids('app/index.html', '<a href="https://example.com">x</a>'), ['NET-06']);
});

test('XML namespace URIs are allowed only under app/js (V-20)', () => {
  assert.deepEqual(ids('app/js/ui/icons.js', "const SVG_NS = 'http://www.w3.org/2000/svg';"), []);
  assert.deepEqual(ids('app/js/ui/dom.js', "const XHTML_NS = 'http://www.w3.org/1999/xhtml';"), []);
  assert.deepEqual(
    ids('app/js/import/docx.js', "const W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';"),
    [],
  );
  assert.deepEqual(ids('app/index.html', '<svg xmlns="http://www.w3.org/2000/svg"></svg>'), ['NET-06']);
  assert.deepEqual(ids('app/js/x.js', "const u = 'http://www.w3.org/2000/svg/evil';"), ['NET-06']);
});

test('web storage is allowed only in app/js/ui/prefs.js', () => {
  assert.deepEqual(ids('app/js/ui/prefs.js', "localStorage.getItem('theme');"), []);
  assert.deepEqual(ids('app/js/ui/other.js', "localStorage.getItem('theme');"), ['STO-01']);
});

test('HTML-only rules do not apply to JS and vice versa', () => {
  assert.deepEqual(ids('app/js/x.js', "button.addEventListener('click', go); // not onclick=go"), []);
  assert.deepEqual(ids('app/index.html', '<p>innerHTML is described in docs</p>'), []);
});

test('scanRepo scans app/ only and skips app/vendor', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'pdae-sec01-'));
  try {
    fs.mkdirSync(path.join(tmp, 'app', 'vendor'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'app', 'js'), { recursive: true });
    fs.mkdirSync(path.join(tmp, 'static'), { recursive: true });
    fs.writeFileSync(path.join(tmp, 'app', 'vendor', 'lib.js'), 'el.innerHTML = x;');
    fs.writeFileSync(path.join(tmp, 'static', 'old.js'), 'el.innerHTML = x;');
    fs.writeFileSync(path.join(tmp, 'app', 'js', 'ok.js'), 'export const a = 1;');
    fs.writeFileSync(path.join(tmp, 'app', 'js', 'bad.js'), 'export const a = 1;\nel.innerHTML = x;');
    fs.writeFileSync(path.join(tmp, 'app', 'notes.txt'), 'el.innerHTML = x;');
    const { files, violations } = scanRepo(tmp);
    assert.deepEqual(files.sort(), ['app/js/bad.js', 'app/js/ok.js']);
    assert.deepEqual(violations.map((v) => `${v.file}:${v.line}:${v.rule}`), ['app/js/bad.js:2:FA-01']);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('CLI exits 0 on the current app/', () => {
  const script = fileURLToPath(new URL('../../tools/check-forbidden-apis.mjs', import.meta.url));
  const r = spawnSync(process.execPath, [script], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
});
