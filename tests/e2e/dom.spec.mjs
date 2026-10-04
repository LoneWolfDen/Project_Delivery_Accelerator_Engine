// Safe DOM builder behaviour in a real browser (UI-01).
import { test, expect, openApp } from './helpers.mjs';

// Each page.evaluate below first imports app/js/ui/dom.js inside the page.
const DOM = './js/ui/dom.js';

test.beforeEach(async ({ page }) => {
  await openApp(page);
});

test('markup in a string renders as literal text, never as elements', async ({ page, problems }) => {
  const payload = '<img src=x onerror="window.__xss=1">';
  const result = await page.evaluate(async ([path, p]) => {
    const dom = await import(path);
    const app = document.getElementById('app');
    dom.replace(app, dom.h('p', { id: 'out' }, p));
    return { text: app.querySelector('#out').textContent, imgs: app.querySelectorAll('img').length };
  }, [DOM, payload]);
  expect(result).toEqual({ text: payload, imgs: 0 });
  await page.waitForTimeout(100);
  expect(await page.evaluate(() => window.__xss)).toBeUndefined();
  expect(problems).toEqual([]);
});

test('event-handler attributes throw', async ({ page }) => {
  const errors = await page.evaluate(async (path) => {
    const dom = await import(path);
    return ['onclick', 'onerror', 'onload', 'ONCLICK'].map((name) => {
      try {
        dom.h('div', { attrs: { [name]: 'x' } });
        return 'no error';
      } catch (e) {
        return e.name;
      }
    });
  }, DOM);
  expect(errors).toEqual(['TypeError', 'TypeError', 'TypeError', 'TypeError']);
});

test('unsafe URLs throw; relative, fragment and blob URLs are allowed', async ({ page }) => {
  const result = await page.evaluate(async (path) => {
    const dom = await import(path);
    const attempt = (attrs, tag = 'a') => {
      try {
        dom.h(tag, { attrs });
        return 'ok';
      } catch (e) {
        return e.name;
      }
    };
    return {
      js: attempt({ href: 'javascript:alert(1)' }),
      jsUpper: attempt({ href: 'JavaScript:alert(1)' }),
      jsSpace: attempt({ href: ' javascript:alert(1)' }),
      data: attempt({ href: 'data:text/html,<b>x</b>' }),
      external: attempt({ href: 'https://example.com/' }),
      protocolRelative: attempt({ href: '//example.com/' }),
      imgSrc: attempt({ src: 'https://example.com/x.png' }, 'img'),
      formAction: attempt({ formaction: 'https://example.com/' }, 'button'),
      relative: attempt({ href: './docs/help.html' }),
      fragment: attempt({ href: '#/projects' }),
      blob: attempt({ href: 'blob:http://127.0.0.1:8765/1234' }),
    };
  }, DOM);
  expect(result).toEqual({
    js: 'TypeError',
    jsUpper: 'TypeError',
    jsSpace: 'TypeError',
    data: 'TypeError',
    external: 'TypeError',
    protocolRelative: 'TypeError',
    imgSrc: 'TypeError',
    formAction: 'TypeError',
    relative: 'ok',
    fragment: 'ok',
    blob: 'ok',
  });
});

test('style, srcdoc, dangerous tags and unknown props throw', async ({ page }) => {
  const result = await page.evaluate(async (path) => {
    const dom = await import(path);
    const attempt = (fn) => {
      try {
        fn();
        return 'ok';
      } catch (e) {
        return e.name;
      }
    };
    return [
      attempt(() => dom.h('div', { attrs: { style: 'color:red' } })),
      attempt(() => dom.h('div', { attrs: { srcdoc: '<b>x</b>' } })),
      attempt(() => dom.h('script')),
      attempt(() => dom.h('iframe')),
      attempt(() => dom.h('div', { innerHTML: '<b>x</b>' })),
      attempt(() => dom.h('img onerror=x')),
      attempt(() => dom.h('div', {}, { toString: () => '<b>x</b>' })),
    ];
  }, DOM);
  expect(result).toEqual(['TypeError', 'TypeError', 'TypeError', 'TypeError', 'TypeError', 'TypeError', 'TypeError']);
});

test('listeners fire, classes/ids/attributes are set, children are flattened and null skipped', async ({ page, problems }) => {
  await page.evaluate(async (path) => {
    const dom = await import(path);
    window.__clicks = 0;
    const btn = dom.h(
      'button',
      { id: 'b', class: ['primary', null, 'big'], attrs: { type: 'button', 'aria-label': 'Count', disabled: false, 'data-x': 1 }, on: { click: () => { window.__clicks += 1; } } },
      'Click ',
      [null, ['me', undefined], false],
      3,
    );
    dom.replace(document.getElementById('app'), btn);
  }, DOM);
  const btn = page.locator('#b');
  await expect(btn).toHaveText('Click me3');
  await expect(btn).toHaveClass('primary big');
  await expect(btn).toHaveAttribute('aria-label', 'Count');
  await expect(btn).toHaveAttribute('data-x', '1');
  await expect(btn).not.toHaveAttribute('disabled', '');
  await btn.click();
  await btn.press('Enter');
  expect(await page.evaluate(() => window.__clicks)).toBe(2);
  expect(problems).toEqual([]);
});

test('clear and replace', async ({ page }) => {
  const result = await page.evaluate(async (path) => {
    const dom = await import(path);
    const box = dom.h('div', {}, dom.h('span', {}, 'a'), dom.h('span', {}, 'b'));
    dom.replace(box, 'x', dom.h('em', {}, 'y'));
    const afterReplace = box.textContent;
    const count = box.childNodes.length;
    dom.clear(box);
    return { afterReplace, count, afterClear: box.childNodes.length };
  }, DOM);
  expect(result).toEqual({ afterReplace: 'xy', count: 2, afterClear: 0 });
});
