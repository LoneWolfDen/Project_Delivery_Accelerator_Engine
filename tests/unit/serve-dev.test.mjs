// Unit tests for tools/serve-dev.mjs (TST-01).
// The legacy server's path traversal (SECURITY_PRIVACY_ASSESSMENT.md B-1) must not be repeated.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { serveDev, resolveSafe, contentType, DEFAULT_HOST, DEFAULT_PORT } from '../../tools/serve-dev.mjs';

let tmp, root, server, port;

// Raw request: Node's http client sends the path unmodified, like `curl --path-as-is`.
function get(rawPath, method = 'GET') {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port, path: rawPath, method }, (res) => {
      let body = '';
      res.on('data', (c) => { body += c; });
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body }));
    });
    req.on('error', reject);
    req.end();
  });
}

before(async () => {
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'pdae-serve-dev-'));
  root = path.join(tmp, 'app');
  fs.mkdirSync(path.join(root, 'sub'), { recursive: true });
  fs.writeFileSync(path.join(root, 'index.html'), '<!doctype html><title>t</title>');
  fs.writeFileSync(path.join(root, 'a.js'), 'export {};');
  fs.writeFileSync(path.join(root, 'b.mjs'), 'export {};');
  fs.writeFileSync(path.join(root, 'c.css'), 'body{}');
  fs.writeFileSync(path.join(root, 'd.json'), '{}');
  fs.writeFileSync(path.join(root, 'manifest.webmanifest'), '{}');
  fs.writeFileSync(path.join(root, 'e.svg'), '<svg xmlns="http://www.w3.org/2000/svg"/>');
  fs.writeFileSync(path.join(root, 'sub', 'index.html'), 'sub');
  fs.writeFileSync(path.join(tmp, 'secret.txt'), 'SECRET-OUTSIDE-ROOT');
  fs.symlinkSync(path.join(tmp, 'secret.txt'), path.join(root, 'link-out.txt'));
  server = await serveDev({ root, port: 0 });
  port = server.address().port;
});

after(async () => {
  await new Promise((r) => server.close(r));
  fs.rmSync(tmp, { recursive: true, force: true });
});

test('defaults are loopback host and fixed port 8765 (ADR-022)', () => {
  assert.equal(DEFAULT_HOST, '127.0.0.1');
  assert.equal(DEFAULT_PORT, 8765);
});

test('binds to 127.0.0.1 only', () => {
  assert.equal(server.address().address, '127.0.0.1');
});

test('refuses a non-loopback host', async () => {
  await assert.rejects(() => serveDev({ root, host: '0.0.0.0', port: 0 }), /loopback/);
});

test('serves files with correct MIME types', async () => {
  const cases = {
    '/index.html': 'text/html; charset=utf-8',
    '/a.js': 'text/javascript; charset=utf-8',
    '/b.mjs': 'text/javascript; charset=utf-8',
    '/c.css': 'text/css; charset=utf-8',
    '/d.json': 'application/json; charset=utf-8',
    '/manifest.webmanifest': 'application/manifest+json; charset=utf-8',
    '/e.svg': 'image/svg+xml',
  };
  for (const [p, type] of Object.entries(cases)) {
    const res = await get(p);
    assert.equal(res.status, 200, p);
    assert.equal(res.headers['content-type'], type, p);
    assert.equal(res.headers['x-content-type-options'], 'nosniff', p);
  }
  assert.equal(contentType('x.unknownext'), 'application/octet-stream');
});

test('directory requests serve index.html', async () => {
  assert.equal((await get('/')).status, 200);
  assert.equal((await get('/sub/')).body, 'sub');
});

test('query strings and fragments are ignored for file lookup', async () => {
  assert.equal((await get('/a.js?v=1')).status, 200);
});

test('path traversal attempts return 404 and never leak outside files', async () => {
  const attempts = [
    '/../secret.txt',
    '/../package.json',
    '/%2e%2e/secret.txt',
    '/%2e%2e/package.json',
    '/..%2fsecret.txt',
    '/%2e%2e%2fsecret.txt',
    '/..%5csecret.txt',
    '/sub/../../secret.txt',
    '/./../secret.txt',
    '//../secret.txt',
    '/index.html%00.js',
    '/%E0%A4%A',          // malformed percent-encoding
    '/link-out.txt',      // symlink pointing outside root
  ];
  for (const p of attempts) {
    const res = await get(p);
    assert.equal(res.status, 404, `${p} → ${res.status}`);
    assert.ok(!res.body.includes('SECRET-OUTSIDE-ROOT'), p);
  }
});

test('resolveSafe rejects escapes and accepts in-root paths', () => {
  assert.equal(resolveSafe(root, '/../secret.txt'), null);
  assert.equal(resolveSafe(root, '/%2e%2e/secret.txt'), null);
  assert.equal(resolveSafe(root, '/a%00.js'), null);
  assert.equal(resolveSafe(root, '/%E0%A4%A'), null);
  assert.equal(resolveSafe(root, '/a.js'), path.join(root, 'a.js'));
});

test('missing files return 404', async () => {
  assert.equal((await get('/nope.js')).status, 404);
});

test('only GET and HEAD are allowed', async () => {
  assert.equal((await get('/index.html', 'POST')).status, 405);
  assert.equal((await get('/index.html', 'HEAD')).status, 200);
});

test('health endpoint responds 200 even when root has no index', async () => {
  const res = await get('/__serve-dev-health');
  assert.equal(res.status, 200);
});
