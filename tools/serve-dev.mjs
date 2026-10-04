// Development static server for the PWA (TST-01).
// Serves app/ on http://127.0.0.1:8765 (fixed loopback origin, ADR-022). Dev/test only; never shipped.
// Usage: node tools/serve-dev.mjs [--port 8765] [--root app]
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const DEFAULT_HOST = '127.0.0.1';
export const DEFAULT_PORT = 8765;
export const HEALTH_PATH = '/__serve-dev-health';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const LOOPBACK = new Set(['127.0.0.1', 'localhost', '::1']);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.pdf': 'application/pdf',
  '.wasm': 'application/wasm',
};

export function contentType(filePath) {
  return MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
}

// Map a request path to an absolute file path inside root, or null if it is unsafe.
// Decodes once, rejects NUL bytes, backslashes and any ".." segment, then checks containment.
export function resolveSafe(root, urlPath) {
  const rawPath = String(urlPath).split(/[?#]/)[0];
  let decoded;
  try {
    decoded = decodeURIComponent(rawPath);
  } catch {
    return null; // malformed percent-encoding
  }
  if (decoded.includes('\0') || decoded.includes('\\')) return null;
  if (decoded.split('/').some((seg) => seg === '..')) return null;
  const absRoot = path.resolve(root);
  const target = path.resolve(absRoot, '.' + path.posix.normalize('/' + decoded));
  if (target !== absRoot && !target.startsWith(absRoot + path.sep)) return null;
  return target;
}

// Follow symlinks and directories; return a real file path inside root, or null.
function realFileInside(root, target) {
  let realRoot;
  let real;
  try {
    realRoot = fs.realpathSync(root);
    real = fs.realpathSync(target);
  } catch {
    return null;
  }
  if (real !== realRoot && !real.startsWith(realRoot + path.sep)) return null;
  const stat = fs.statSync(real);
  if (stat.isDirectory()) {
    return realFileInside(root, path.join(real, 'index.html'));
  }
  return stat.isFile() ? real : null;
}

function send(res, status, body, type = 'text/plain; charset=utf-8', headOnly = false) {
  res.writeHead(status, {
    'Content-Type': type,
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
  });
  res.end(headOnly ? undefined : body);
}

export function serveDev({ root = path.join(REPO_ROOT, 'app'), host = DEFAULT_HOST, port = DEFAULT_PORT } = {}) {
  if (!LOOPBACK.has(host)) {
    return Promise.reject(new Error(`serve-dev only binds to a loopback address, not ${host}`));
  }
  const server = http.createServer((req, res) => {
    const headOnly = req.method === 'HEAD';
    if (req.method !== 'GET' && !headOnly) {
      send(res, 405, 'Method not allowed');
      return;
    }
    if (req.url === HEALTH_PATH) {
      send(res, 200, 'ok', undefined, headOnly);
      return;
    }
    const target = resolveSafe(root, req.url);
    const file = target && realFileInside(root, target);
    if (!file) {
      send(res, 404, 'Not found', undefined, headOnly);
      return;
    }
    fs.readFile(file, (err, data) => {
      if (err) {
        send(res, 404, 'Not found', undefined, headOnly);
        return;
      }
      send(res, 200, data, contentType(file), headOnly);
    });
  });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, host, () => resolve(server));
  });
}

function argValue(name) {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : undefined;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(argValue('--port') ?? DEFAULT_PORT);
  const root = path.resolve(REPO_ROOT, argValue('--root') ?? 'app');
  serveDev({ root, port }).then(
    (server) => {
      const { address, port: p } = server.address();
      console.log(`serve-dev: serving ${root} at http://${address}:${p}/`);
    },
    (err) => {
      console.error(`serve-dev: ${err.message}`);
      process.exit(1);
    },
  );
}
