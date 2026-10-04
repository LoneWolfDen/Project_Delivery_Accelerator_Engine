// Visible error banner for uncaught errors (DGN-01).
import { test, expect, openApp } from './helpers.mjs';

// These tests throw on purpose, so they use the plain page (no problem watcher).

test('an uncaught error shows the APP-UNEXPECTED banner with code and is logged without its message', async ({ page }) => {
  await openApp(page);
  await page.evaluate(() => setTimeout(() => { throw new Error('SECRET document sentence'); }, 0));
  const banner = page.getByRole('alert');
  await expect(banner).toBeVisible();
  await expect(banner).toContainText('Something went wrong');
  await expect(banner).toContainText('Diagnostic code: APP-UNEXPECTED');
  await expect(banner).not.toContainText('SECRET');
  const events = await page.evaluate(async () => (await import('./js/diagnostics/log.js')).getEvents());
  expect(events.map((e) => [e.level, e.code, e.module])).toEqual([['error', 'APP-UNEXPECTED', 'main']]);
  expect(JSON.stringify(events)).not.toContain('SECRET');
});

test('an unhandled promise rejection shows the banner once (same code replaces, does not stack)', async ({ page }) => {
  await openApp(page);
  await page.evaluate(() => { Promise.reject(new Error('one')); Promise.reject(new Error('two')); });
  await expect(page.locator('.banner[data-code="APP-UNEXPECTED"]')).toHaveCount(1);
});

test('showError renders catalogue text, optional detail, copy and dismiss buttons', async ({ page, context, browserName }) => {
  if (browserName === 'chromium') await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await openApp(page);
  await page.evaluate(async () => {
    const { showError } = await import('./js/ui/components/banner.js');
    showError('STO-QUOTA', '<b>2 of 3</b> files saved');
  });
  const banner = page.locator('.banner[data-code="STO-QUOTA"]');
  await expect(banner).toHaveAttribute('role', 'alert');
  await expect(banner.locator('.banner-title')).toHaveText('Storage is full');
  await expect(banner.locator('.banner-detail')).toHaveText('<b>2 of 3</b> files saved'); // text, not markup
  await expect(banner.locator('b')).toHaveCount(0);
  const copy = banner.getByRole('button').first(); // its label changes after clicking
  await expect(copy).toHaveText('Copy diagnostic code');
  await copy.click();
  if (browserName === 'chromium') {
    await expect(copy).toHaveText('Copied');
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('STO-QUOTA');
  } else {
    await expect(copy).toHaveText(/Copied|Copy failed – the code is STO-QUOTA/);
  }
  await banner.getByRole('button', { name: 'Dismiss' }).click();
  await expect(banner).toHaveCount(0);
});

test('an unknown code falls back to APP-UNEXPECTED', async ({ page, problems }) => {
  await openApp(page);
  await page.evaluate(async () => {
    const { showError } = await import('./js/ui/components/banner.js');
    showError('NOT-A-CODE');
  });
  await expect(page.locator('.banner[data-code="APP-UNEXPECTED"]')).toBeVisible();
  expect(problems).toEqual([]);
});
