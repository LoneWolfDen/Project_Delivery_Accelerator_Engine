// Trusted Types enforcement (SEC-02). Runs wherever the browser supports Trusted Types
// (Chromium/Edge; newer WebKit); skipped with a reason elsewhere.
import { test, expect, openApp } from './helpers.mjs';

async function requireTrustedTypes(page) {
  const supported = await page.evaluate(() => typeof window.trustedTypes !== 'undefined');
  test.skip(!supported, 'Trusted Types not supported');
}

test('CSP requires Trusted Types with the single pdae-script-url policy', async ({ page, problems }) => {
  await openApp(page);
  const csp = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
  expect(csp).toContain("require-trusted-types-for 'script'");
  expect(csp).toContain('trusted-types pdae-script-url');
  expect(problems).toEqual([]);
});

test('assigning an HTML string to innerHTML throws', async ({ page }) => {
  await openApp(page);
  await requireTrustedTypes(page);
  const result = await page.evaluate(() => {
    try {
      document.body.innerHTML = '<b>x</b>';
      return 'no error';
    } catch (e) {
      return e.name;
    }
  });
  expect(result).toBe('TypeError');
  await expect(page.locator('#app h1')).toBeVisible(); // page content unchanged
});

test('scriptURL allows ./sw.js only', async ({ page }) => {
  await openApp(page);
  await requireTrustedTypes(page);
  const result = await page.evaluate(async () => {
    const tt = await import('./js/core/trusted-types.js');
    const ok = tt.scriptURL('./sw.js');
    let evil = 'no error';
    try {
      tt.scriptURL('./evil.js');
    } catch (e) {
      evil = e.message;
    }
    return {
      allowList: [...tt.ALLOWED_SCRIPT_URLS],
      frozen: Object.isFrozen(tt.ALLOWED_SCRIPT_URLS),
      okIsTrusted: window.trustedTypes.isScriptURL(ok),
      okText: String(ok),
      evil,
    };
  });
  expect(result.allowList).toEqual(['./sw.js']);
  expect(result.frozen).toBe(true);
  expect(result.okIsTrusted).toBe(true);
  expect(result.okText).toBe('./sw.js');
  expect(result.evil).toContain('Script URL not allowed');
});

test('a second policy cannot be created', async ({ page }) => {
  await openApp(page);
  await requireTrustedTypes(page);
  const result = await page.evaluate(() => {
    try {
      window.trustedTypes.createPolicy('attacker', { createHTML: (s) => s });
      return 'created';
    } catch (e) {
      return e.name;
    }
  });
  expect(result).toBe('TypeError');
});
