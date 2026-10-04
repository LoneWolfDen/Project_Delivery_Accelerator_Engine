// Shared Playwright helpers (BLD-01).
// `test` replaces Playwright's test: every test that uses `page` fails if the page reports a
// Content-Security-Policy violation, a console error or an uncaught exception.
import { test as base, expect } from '@playwright/test';

export { expect };

// Attach problem listeners to a page. Returns the live array of problems found.
export function watchPage(page) {
  const problems = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') problems.push(`console error: ${msg.text()}`);
  });
  page.on('pageerror', (err) => problems.push(`uncaught: ${err.message}`));
  // Runs before any page script; reports CSP violations through an exposed binding.
  page.exposeBinding('__pdaeReportViolation', (_source, v) => {
    problems.push(`CSP violation: ${v.directive} blocked ${v.blocked}`);
  });
  page.addInitScript(() => {
    document.addEventListener('securitypolicyviolation', (e) => {
      window.__pdaeReportViolation({ directive: e.violatedDirective, blocked: e.blockedURI });
    });
  });
  return problems;
}

export const test = base.extend({
  problems: async ({ page }, use) => {
    const problems = watchPage(page);
    await use(problems);
    expect(problems, 'page reported problems').toEqual([]);
  },
});

// Open the app at its root and wait until main.js has finished starting.
export async function openApp(page, path = './') {
  await page.goto(path);
  await expect(page.locator('html')).toHaveAttribute('data-ready', 'true');
}
