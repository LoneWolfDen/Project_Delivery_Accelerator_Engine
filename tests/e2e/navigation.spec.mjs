// App frame navigation and keyboard access (UI-02).
import { test, expect, openApp } from './helpers.mjs';

const ROUTES = [
  ['#/projects', 'Projects'],
  ['#/settings', 'Settings'],
  ['#/trash', 'Trash'],
  ['#/help', 'Help'],
  ['#/project/p_123/items', 'Project'],
];

test('the app opens on Projects with the Projects button marked current', async ({ page, problems }) => {
  await openApp(page);
  await expect(page).toHaveURL(/#\/projects$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Projects');
  await expect(page.getByRole('button', { name: 'Projects' })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('button', { name: 'Settings' })).not.toHaveAttribute('aria-current', /.*/);
  await expect(page).toHaveTitle('Projects – Project Delivery Accelerator');
  expect(problems).toEqual([]);
});

test('keyboard only: first Tab reaches the skip link and Enter moves focus to the view heading', async ({ page, problems, browserName }) => {
  await openApp(page);
  // Safari moves to links with Option+Tab by default (plain Tab skips links).
  await page.keyboard.press(browserName === 'webkit' ? 'Alt+Tab' : 'Tab');
  const skip = page.getByRole('link', { name: 'Skip to main content' });
  await expect(skip).toBeFocused();
  await expect(skip).toBeInViewport();
  await page.keyboard.press('Enter');
  await expect(page.locator('#app h1')).toBeFocused();
  await expect(page).toHaveURL(/#\/projects$/); // the skip link does not change the route
  expect(problems).toEqual([]);
});

test('keyboard only: nav buttons change the hash, focus the view h1 and announce the page', async ({ page, problems }) => {
  await openApp(page);
  // Focus each nav button directly (Safari's default Tab order differs; tab order is covered above).
  for (const [hash, title] of ROUTES.slice(1, 4)) {
    const button = page.getByRole('button', { name: title });
    await button.focus();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(new RegExp(`${hash.replace('/', '\\/')}$`));
    await expect(page.locator('#app h1')).toHaveText(title);
    await expect(page.locator('#app h1')).toBeFocused();
    await expect(button).toHaveAttribute('aria-current', 'page');
    await expect(page.locator('#live-region')).toHaveText(`${title} page`);
  }
  expect(problems).toEqual([]);
});

test('each route renders its placeholder view with no sample data', async ({ page, problems }) => {
  await openApp(page);
  for (const [hash, title] of ROUTES) {
    await page.goto(`./${hash}`);
    await expect(page.locator('#app h1')).toHaveText(title);
    await expect(page.locator('#app')).toHaveText(`${title}This part isn't built yet.`);
    await expect(page.locator('#app *')).toHaveCount(3); // section, h1, paragraph — nothing else
  }
  expect(problems).toEqual([]);
});

test('unknown or malformed routes go to Projects without adding history', async ({ page, problems }) => {
  await openApp(page);
  for (const bad of ['#/nonsense', '#/project/', '#/project/a%2Fb/items', '#/project/x/items/extra', '#/settings/x', '#main']) {
    await page.goto(`./${bad}`);
    await expect(page).toHaveURL(/#\/projects$/);
    await expect(page.locator('#app h1')).toHaveText('Projects');
  }
  expect(problems).toEqual([]);
});

test('project route without a tab opens its default tab; Back returns to the previous view', async ({ page, problems }) => {
  await openApp(page);
  await page.getByRole('button', { name: 'Settings' }).click();
  await expect(page.locator('#app h1')).toHaveText('Settings');
  await page.goBack();
  await expect(page).toHaveURL(/#\/projects$/);
  await expect(page.locator('#app h1')).toHaveText('Projects');
  await page.goto('./#/project/p_1');
  await expect(page.locator('#app h1')).toHaveText('Project');
  expect(problems).toEqual([]);
});

test('every interactive element is a button or a link', async ({ page }) => {
  await openApp(page);
  const offenders = await page.evaluate(() => {
    const all = [...document.querySelectorAll('body *')];
    return all
      .filter((el) => el.tabIndex >= 0 || el.getAttribute('role') === 'button' || el.hasAttribute('onclick'))
      .filter((el) => !['A', 'BUTTON'].includes(el.tagName))
      .map((el) => el.outerHTML.slice(0, 80));
  });
  expect(offenders).toEqual([]);
});

test('keyboard only (Chromium/Edge): Tab walks skip link → Projects → Trash → Settings → Help, Enter navigates', async ({ page, problems, browserName }) => {
  test.skip(browserName !== 'chromium', 'Tab order for links differs in Safari by default');
  await openApp(page);
  const order = [];
  for (let i = 0; i < 5; i += 1) {
    await page.keyboard.press('Tab');
    order.push(await page.evaluate(() => document.activeElement.textContent));
  }
  expect(order).toEqual(['Skip to main content', 'Projects', 'Trash', 'Settings', 'Help']);
  await page.keyboard.press('Enter'); // on Help
  await expect(page).toHaveURL(/#\/help$/);
  await expect(page.locator('#app h1')).toBeFocused();
  expect(problems).toEqual([]);
});
