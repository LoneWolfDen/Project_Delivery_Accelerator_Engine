// Syntax check for browser and tool code (TST-01): runs `node --check` on every
// app/**/*.js, app/**/*.mjs and tools/**/*.mjs. Missing folders are skipped.
// app/vendor/** is skipped (third-party files are verified by hash instead).
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TARGETS = [
  { dir: 'app', exts: ['.js', '.mjs'], skip: ['app/vendor'] },
  { dir: 'tools', exts: ['.mjs'], skip: [] },
];

function walk(dir, exts, skip, out) {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    const rel = path.relative(REPO_ROOT, full).split(path.sep).join('/');
    if (skip.some((s) => rel === s || rel.startsWith(s + '/'))) continue;
    if (entry.isDirectory()) walk(full, exts, skip, out);
    else if (exts.includes(path.extname(entry.name))) out.push(full);
  }
  return out;
}

const files = TARGETS.flatMap((t) => walk(path.join(REPO_ROOT, t.dir), t.exts, t.skip, []));
let failed = 0;
for (const file of files) {
  const r = spawnSync(process.execPath, ['--check', file], { encoding: 'utf8' });
  if (r.status !== 0) {
    failed += 1;
    console.error(`✖ ${path.relative(REPO_ROOT, file)}\n${r.stderr.trim()}\n`);
  }
}
console.log(`check-syntax: ${files.length} file(s) checked, ${failed} failed`);
process.exit(failed ? 1 : 0);
