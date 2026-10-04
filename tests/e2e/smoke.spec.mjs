// Smoke test for the application shell (BLD-01).
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { test, expect, openApp } from './helpers.mjs';
import { APP_VERSION } from '../../app/version.js';

test('app starts: title and version visible, boot message hidden, no problems', async ({ page, problems }) => {
  await openApp(page);
  await expect(page.getByRole('heading', { level: 1, name: 'Project Delivery Accelerator' })).toBeVisible();
  await expect(page.locator('#app-version')).toHaveText(`Version ${APP_VERSION}`);
  await expect(page.locator('#boot-msg')).toBeHidden();
  expect(problems).toEqual([]);
});

test('CSP meta is present and allows no other origin than openrouter.ai', async ({ page, problems }) => {
  await openApp(page);
  const csp = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
  expect(csp).toContain("script-src 'self'");
  expect(csp).toContain("style-src 'self'");
  expect(csp).toContain("object-src 'none'");
  expect(csp).toContain("base-uri 'none'");
  expect(csp.match(/https?:\/\/[^\s;]+/g)).toEqual(['https://openrouter.ai']);
  expect(problems).toEqual([]);
});

test('CSP blocks an injected inline script', async ({ page }) => {
  await openApp(page);
  const ran = await page.evaluate(async () => {
    window.__inlineRan = false;
    const s = document.createElement('script');
    s.textContent = 'window.__inlineRan = true;';
    const blocked = new Promise((resolve) => document.addEventListener('securitypolicyviolation', () => resolve(true), { once: true }));
    document.body.append(s);
    await Promise.race([blocked, new Promise((r) => setTimeout(r, 1000))]);
    return window.__inlineRan;
  });
  expect(ran).toBe(false);
});

test('opened as a file, the boot message stays visible', async ({ page }) => {
  // Plain page (no problem watcher): browsers log errors for module scripts on file://.
  const fileUrl = pathToFileURL(path.resolve('app/index.html')).href;
  await page.goto(fileUrl);
  await page.waitForTimeout(500);
  await expect(page.locator('#boot-msg')).toBeVisible();
  await expect(page.locator('#boot-msg')).toContainText('opening the file directly is not supported');
  await expect(page.locator('#app h1')).toHaveCount(0);
});
