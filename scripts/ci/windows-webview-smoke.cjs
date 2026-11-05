// Test-only CDP attachment to the REAL installed WebView2. No browser download,
// no shipped debugging flag, and no mocked API. playwright-core is installed only
// into the CI runner's temporary tools directory.
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');
const output = process.argv[2];
assert.ok(output, 'output directory required');
fs.mkdirSync(output, { recursive: true });
const result = { checks: [], observedPageErrors: [], observedConsoleErrors: [],
  limitations: ['CDP attaches after startup; errors/traffic before attachment are not fully observed.',
    'Installed light build, not approved full offline model/render/export acceptance.'] };
function check(name, ok, detail = '') {
  result.checks.push({ name, passed: !!ok, detail });
  console.log(`::${ok ? 'notice' : 'error'} title=Installed WebView acceptance::${name} : ${!!ok}`);
  assert.ok(ok, name);
}
(async () => {
  let browser;
  try {
    browser = await chromium.connectOverCDP('http://127.0.0.1:9222', { timeout: 30000 });
    let page;
    const deadline = Date.now() + 30000;
    do {
      const pages = browser.contexts().flatMap(c => c.pages());
      result.targets = pages.map(p => p.url());
      page = pages.find(p => p.url().startsWith('http://127.0.0.1:8756/'));
      if (page) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    } while (Date.now() < deadline);
    check('native WebView actually navigated to owned same-origin backend', !!page, JSON.stringify(result.targets));
    result.page = page.url();
    page.on('pageerror', e => result.observedPageErrors.push(e.message));
    page.on('console', m => { if (m.type() === 'error') result.observedConsoleErrors.push(m.text()); });
    await page.getByText('هستهٔ پردازش متصل است', { exact: true }).waitFor({ timeout: 20000 });
    check('real installed React reports connected processing core', true);
    check('real installed main workspace visible', await page.getByRole('main').isVisible());
    check('native default Persian RTL renders', await page.locator('html').getAttribute('dir') === 'rtl');
    const health = await page.evaluate(async () => (await fetch('/api/v1/health')).json());
    check('relative fetch from native WebView reaches healthy offline API', health.status === 'ok' && health.offline === true);
    result.resources = await page.evaluate(() => performance.getEntriesByType('resource').map(e => e.name));
    check('native frontend never loaded Vite client', !result.resources.some(u => /@vite|@react-refresh/.test(u)));
    check('observed native resource entries stay local', result.resources.every(u => !/^https?:/.test(u) || new URL(u).origin === 'http://127.0.0.1:8756'));
    const bytes = await page.screenshot({ path: path.join(output, 'installed-webview-fa.png'), fullPage: true });
    result.screenshot = { file: 'installed-webview-fa.png', bytes: bytes.length,
      sha256: crypto.createHash('sha256').update(bytes).digest('hex') };
    check('native WebView screenshot captured', bytes.length > 10000);
    check('no page errors observed after CDP attachment', result.observedPageErrors.length === 0, JSON.stringify(result.observedPageErrors));
    check('no console errors observed after CDP attachment', result.observedConsoleErrors.length === 0, JSON.stringify(result.observedConsoleErrors));
    console.log('::notice title=Installed WebView summary::' + JSON.stringify({ page: result.page, screenshot: result.screenshot, checks: result.checks.length }));
  } catch (error) {
    result.failure = error.message;
    throw error;
  } finally {
    fs.writeFileSync(path.join(output, 'webview.json'), JSON.stringify(result, null, 2));
    if (browser) await browser.close(); // connectOverCDP disconnects its transport; it does not own the native app.
  }
})().catch(error => {
  console.error('::error title=Installed WebView execution::' + error.message.replace(/%/g, '%25').replace(/\r/g, '%0D').replace(/\n/g, '%0A'));
  process.exitCode = 1;
});
