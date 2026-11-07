// Real built React + same-origin API/media, no Vite and no mocked API.
// External browser test tooling/owned media fixtures are not shipped.
const chromium = require('@sparticuz/chromium').default;
const { chromium: pw } = require('playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');
const base = process.env.CE_E2E_UI || 'http://127.0.0.1:1422';
const fixture = process.env.CE_E2E_MEDIA || '/tmp/ce-media/clips/clip1.mp4';
const out = process.env.CE_E2E_OUTPUT || path.resolve(__dirname, '../../docs/evidence/desktop-r2c');
const result = { checks: [], errors: [], external: [], requests: [], consoleErrors: [], limitations: [
  'Linux built-frontend HTTP browser gate, not a Windows WebView pixel assertion.',
  'Diagnostic LGPL FFmpeg for import/probe only, not the shipping runtime or render/export.',
  'MPEG4 Part 2 fixture was not decodable in Chromium; general codec/proxy support remains OPEN.',
  'Standalone preview accepts its proxy host; managed desktop host/origin boundary is tested separately.',
] };
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function check(name, ok, detail = '') { result.checks.push({ name, passed: !!ok, detail }); console.log(ok ? 'PASS' : 'FAIL', name, detail); assert.ok(ok, name); }
async function saved(page) { await page.waitForFunction(() => document.querySelector('[data-testid="workspace-status"]')?.textContent === 'Saved locally', {}, { timeout: 20000 }); }
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const before = hash(fixture);
  const browser = await pw.launch({ executablePath: await chromium.executablePath(), args: chromium.args, headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    page.on('pageerror', e => result.errors.push(e.message));
    page.on('console', m => { if (m.type() === 'error') result.consoleErrors.push(m.text()); });
    page.on('request', r => {
      const u = new URL(r.url());
      if (['http:', 'https:'].includes(u.protocol) && u.host !== new URL(base).host) result.external.push(r.url());
      result.requests.push({ method: r.method(), url: r.url() });
    });
    const document = await page.goto(base);
    check('disk-built frontend is the document', document.status() === 200 && (await document.text()).includes('type="module"'));
    check('same-origin policy on built UI', document.headers()['content-security-policy'].includes("connect-src 'self'"));
    await page.getByRole('button', { name: 'زبان', exact: true }).click();
    await page.getByText('Processing core connected', { exact: true }).waitFor();
    check('built UI reaches real backend', true);
    await page.getByRole('button', { name: 'New project', exact: true }).click();
    const title = 'Release transport — مسیر محلی';
    await page.getByRole('textbox', { name: 'Project name', exact: true }).fill(title);
    await saved(page);
    check('real local project saved', true);
    const posted = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/uploads') && r.status() === 201);
    await page.locator('input[type="file"]').first().setInputFiles(fixture);
    const asset = await (await posted).json();
    await saved(page);
    check('same-origin multipart import/probe succeeds', asset.duration > 0 && asset.available);
    const video = page.locator('video');
    await video.waitFor();
    await page.waitForFunction(() => { const v = document.querySelector('video'); return v?.readyState >= 2 && v.videoWidth > 0; });
    check('real imported video decodes', true);
    const media = await video.evaluate(v => v.currentSrc);
    check('media stays on document origin', new URL(media).origin === new URL(base).origin);
    const range = await page.request.get(media, { headers: { Range: 'bytes=0-15' } });
    check('native media range streaming works', range.status() === 206 && (await range.body()).equals(fs.readFileSync(fixture).subarray(0, 16)));
    await video.evaluate(async v => { v.muted = true; await v.play(); });
    await page.waitForFunction(() => document.querySelector('video')?.currentTime > .2);
    await video.evaluate(v => v.pause());
    check('source playback advances without proxy', true);
    await page.getByRole('button', { name: 'Add to timeline ' + path.basename(fixture), exact: true }).click();
    await saved(page);
    check('timeline change persists through real API', true);
    await page.screenshot({ path: path.join(out, 'built-ui-en.png'), fullPage: true });
    await page.reload();
    await saved(page);
    check('project reload survives without Vite', await page.getByRole('textbox', { name: 'Project name', exact: true }).inputValue() === title);
    check('import is restored from SQLite', await page.getByRole('button', { name: path.basename(fixture), exact: true }).count() === 1);
    const health = await page.request.get(new URL('/api/v1/health', base).href);
    const project = await page.request.get(new URL('/api/v1/projects/' + asset.project_id, base).href);
    check('same-origin persisted project API', project.status() === 200 && (await project.json()).name === title);
    const workspace = await (await page.request.get(new URL('/api/v1/projects/' + asset.project_id + '/workspace', base).href)).json();
    check('SQLite restores actual timeline clip', workspace.snapshot.timeline.clips.some(c => c.mediaId === asset.path));
    check('diagnostic profile isolated from primary', (await health.json()).database.startsWith('/tmp/ce-desktop-browser-data/'));
    await page.getByRole('button', { name: 'Language', exact: true }).click();
    check('built frontend switches to Persian RTL', await page.locator('html').getAttribute('dir') === 'rtl');
    await page.waitForFunction(() => document.querySelector('[data-testid="workspace-status"]')?.textContent === 'ذخیره‌شده در رایانه', {}, { timeout: 20000 });
    await page.screenshot({ path: path.join(out, 'built-ui-fa.png'), fullPage: true });
    const missing = await page.request.get(new URL('/api/v1/nonexistent', base).href);
    check('API misses remain 404, never SPA success', missing.status() === 404 && !(await missing.text()).includes('<html'));
    check('no Vite dev client loaded', !result.requests.some(r => /@vite|@react-refresh/.test(r.url)));
    check('fixture source unchanged', hash(fixture) === before);
    check('no external HTTP requests', result.external.length === 0);
    check('no live JavaScript errors', result.errors.length === 0, JSON.stringify(result.errors));
    // The intentional 404 request uses the API client, not the rendered page.
    check('no browser console errors', result.consoleErrors.length === 0, JSON.stringify(result.consoleErrors));
  } finally {
    fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify(result, null, 2));
    await browser.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
