#!/usr/bin/env node
/**
 * capture_page.mjs - capture proof that a page behaves as claimed, in a real browser.
 *
 * Records every console message, every uncaught error (including the ones thrown
 * inside event listeners, which the devtools console does not always surface),
 * every network request with its status, the rendered text assertions, and
 * optionally a screenshot. Writes one JSON evidence file to .prove-it/.
 *
 * Exit codes: 0 every expectation held - 1 an expectation failed - 2 cannot run.
 *
 * Usage:
 *   node capture_page.mjs --url URL
 *        [--expect-text STR]...        text that must appear in the rendered page
 *        [--expect-request REGEX]...   a network request that must be sent
 *        [--expect-no-request REGEX]... a network request that must NOT be sent
 *        [--click SELECTOR]...         clicked in order before assertions
 *        [--wait MS]                   extra settle time after load (default 1500)
 *        [--viewport WxH]              default 1280x800
 *        [--screenshot] [--full-page]
 *        [--out DIR] [--timeout MS] [--headed] [--allow-errors]
 *
 * Examples:
 *   node capture_page.mjs --url https://example.com --expect-text "Pro plan" --screenshot
 *   node capture_page.mjs --url https://example.com --expect-request 'facebook\.com/tr'
 */

import { mkdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';

const CHROMIUM_SCREENSHOT_CAP = 8192; // px: beyond this Chromium silently folds the capture

function parseArgs(argv) {
  const o = {
    url: null, expectText: [], expectRequest: [], expectNoRequest: [], click: [],
    wait: 1500, viewport: '1280x800', screenshot: false, fullPage: false,
    out: '.prove-it', timeout: 30000, headed: false, allowErrors: false,
  };
  const need = (i, f) => {
    if (i + 1 >= argv.length) { console.error(`${f} needs a value`); process.exit(2); }
    return argv[i + 1];
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    switch (a) {
      case '--url': o.url = need(i, a); i++; break;
      case '--expect-text': o.expectText.push(need(i, a)); i++; break;
      case '--expect-request': o.expectRequest.push(need(i, a)); i++; break;
      case '--expect-no-request': o.expectNoRequest.push(need(i, a)); i++; break;
      case '--click': o.click.push(need(i, a)); i++; break;
      case '--wait': o.wait = Number(need(i, a)); i++; break;
      case '--viewport': o.viewport = need(i, a); i++; break;
      case '--out': o.out = need(i, a); i++; break;
      case '--timeout': o.timeout = Number(need(i, a)); i++; break;
      case '--screenshot': o.screenshot = true; break;
      case '--full-page': o.screenshot = true; o.fullPage = true; break;
      case '--headed': o.headed = true; break;
      case '--allow-errors': o.allowErrors = true; break;
      case '-h': case '--help': printHelp(); process.exit(0);
      default:
        if (a.startsWith('-')) { console.error(`unknown option: ${a}`); process.exit(2); }
        if (!o.url) o.url = a; else { console.error(`unexpected argument: ${a}`); process.exit(2); }
    }
  }
  if (!o.url) { printHelp(); process.exit(2); }
  return o;
}

function printHelp() {
  console.error(`capture_page.mjs --url URL [--expect-text STR] [--expect-request REGEX]
                 [--expect-no-request REGEX] [--click SELECTOR] [--wait MS]
                 [--viewport WxH] [--screenshot] [--full-page] [--out DIR]
                 [--timeout MS] [--headed] [--allow-errors]`);
}

async function loadPlaywright() {
  const pick = (m) => m?.chromium ?? m?.default?.chromium ?? null;
  // Resolve from this script first, then from the project being verified - the
  // skill's scripts usually live outside the repo they are proving.
  for (const name of ['playwright', 'playwright-core']) {
    try { const c = pick(await import(name)); if (c) return c; } catch { /* try next */ }
  }
  const req = createRequire(pathToFileURL(join(process.cwd(), 'package.json')).href);
  for (const name of ['playwright', 'playwright-core']) {
    try {
      const c = pick(await import(pathToFileURL(req.resolve(name)).href));
      if (c) return c;
    } catch { /* try next */ }
  }
  console.error(
`UNPROVABLE HERE - Playwright is not installed, so no browser evidence can be captured.

  npm i -D playwright && npx playwright install chromium

Do not substitute a weaker proof. Report UNPROVABLE HERE, or use another real
browser tool available in this session.`);
  process.exit(2);
}

const opts = parseArgs(process.argv.slice(2));
const chromium = await loadPlaywright();

const [vw, vh] = opts.viewport.split('x').map(Number);
if (!vw || !vh) { console.error(`bad --viewport: ${opts.viewport}`); process.exit(2); }

const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
const slug = (opts.url.startsWith('file://') ? opts.url.split('/').pop() : opts.url.replace(/^https?:\/\//, ''))
  .replace(/[^A-Za-z0-9]/g, '-').slice(0, 60);
mkdirSync(opts.out, { recursive: true });
const base = join(opts.out, `page-${slug}-${stamp}`);

const SECRET = /(authorization|cookie|token|key|secret|password|session)=([^&\s]+)/gi;
const scrub = (s) => String(s ?? '').replace(SECRET, '$1=[redacted]');

const consoleMessages = [];
const pageErrors = [];
const requests = [];
const statusByUrl = new Map();
const failed = [];
const warnings = [];

// Prefer Playwright's bundled Chromium; fall back to a system browser so the
// evidence can still be captured without a 150 MB download.
let browser = null, browserChannel = 'bundled-chromium';
for (const channel of [null, 'chrome', 'msedge']) {
  try {
    browser = await chromium.launch({ headless: !opts.headed, ...(channel ? { channel } : {}) });
    if (channel) browserChannel = channel;
    break;
  } catch (e) { browser = null; }
}
if (!browser) {
  console.error(
`UNPROVABLE HERE - no browser could be launched (no bundled Chromium, no system Chrome or Edge).

  npx playwright install chromium

Report UNPROVABLE HERE rather than substituting a weaker proof.`);
  process.exit(2);
}
const context = await browser.newContext({ viewport: { width: vw, height: vh } });

// Installed before any page script runs: the only reliable capture for errors
// thrown inside event listeners and for unhandled promise rejections.
await context.addInitScript(() => {
  window.__proveIt = { errors: [] };
  window.addEventListener('error', (e) => {
    window.__proveIt.errors.push({
      kind: 'error',
      message: String(e.message || e.error || 'unknown'),
      source: `${e.filename || ''}:${e.lineno || 0}:${e.colno || 0}`,
    });
  }, true);
  window.addEventListener('unhandledrejection', (e) => {
    window.__proveIt.errors.push({
      kind: 'unhandledrejection',
      message: String((e.reason && (e.reason.message || e.reason)) || 'unknown'),
      source: '',
    });
  });
});

const page = await context.newPage();
page.on('console', (m) => consoleMessages.push({ type: m.type(), text: scrub(m.text()) }));
page.on('pageerror', (e) => pageErrors.push({ kind: 'pageerror', message: scrub(e.message), source: '' }));
page.on('request', (r) => requests.push({ url: scrub(r.url()), method: r.method(), type: r.resourceType() }));
page.on('response', (r) => statusByUrl.set(scrub(r.url()), r.status()));
page.on('requestfailed', (r) => failed.push({ url: scrub(r.url()), reason: r.failure()?.errorText ?? 'unknown' }));

let navStatus = null, navError = null;
try {
  const resp = await page.goto(opts.url, { waitUntil: 'networkidle', timeout: opts.timeout });
  navStatus = resp ? resp.status() : null;
} catch (e) {
  navError = String(e.message).split('\n')[0];
}

const clicked = [];
if (!navError) {
  for (const sel of opts.click) {
    try {
      await page.click(sel, { timeout: 5000 });
      clicked.push({ selector: sel, ok: true });
      await page.waitForTimeout(500);
    } catch (e) {
      clicked.push({ selector: sel, ok: false, error: String(e.message).split('\n')[0] });
      warnings.push(`click failed: ${sel}`);
    }
  }
  if (opts.wait > 0) await page.waitForTimeout(opts.wait);
}

let bodyText = '', title = '', finalUrl = opts.url, docHeight = 0;
if (!navError) {
  bodyText = await page.evaluate(() => document.body?.innerText ?? '').catch(() => '');
  title = await page.title().catch(() => '');
  finalUrl = page.url();
  docHeight = await page.evaluate(() => document.documentElement.scrollHeight).catch(() => 0);
  const injected = await page.evaluate(() => (window.__proveIt?.errors ?? [])).catch(() => []);
  for (const e of injected) pageErrors.push({ ...e, message: scrub(e.message) });
}

let screenshotPath = null;
if (opts.screenshot && !navError) {
  screenshotPath = `${base}.png`;
  if (opts.fullPage && docHeight > CHROMIUM_SCREENSHOT_CAP) {
    warnings.push(
      `full-page screenshot: document is ${docHeight}px tall, above the ~${CHROMIUM_SCREENSHOT_CAP}px Chromium cap. ` +
      `The image is folded and may repeat the top of the page. Treat it as partial evidence.`);
  }
  await page.screenshot({ path: screenshotPath, fullPage: opts.fullPage }).catch((e) => {
    warnings.push(`screenshot failed: ${e.message}`);
    screenshotPath = null;
  });
}

const withStatus = requests.map((r) => ({ ...r, status: statusByUrl.get(r.url) ?? null }));
const match = (pattern) => {
  const re = new RegExp(pattern, 'i');
  return withStatus.filter((r) => re.test(r.url));
};

const requestChecks = opts.expectRequest.map((p) => {
  const hits = match(p);
  return { pattern: p, expected: true, count: hits.length, ok: hits.length > 0, samples: hits.slice(0, 3) };
});
const noRequestChecks = opts.expectNoRequest.map((p) => {
  const hits = match(p);
  return { pattern: p, expected: false, count: hits.length, ok: hits.length === 0, samples: hits.slice(0, 3) };
});
const textChecks = opts.expectText.map((t) => ({ text: t, ok: bodyText.includes(t) }));

// The same throw surfaces twice: once via Playwright's pageerror, once via the
// listener installed before page scripts. Keep one entry per distinct message.
const seenErrors = new Set();
const uniqueErrors = pageErrors.filter((e) => {
  const k = e.message.replace(/^Uncaught [A-Za-z]*Error: /, '').trim();
  if (seenErrors.has(k)) return false;
  seenErrors.add(k);
  return true;
});
pageErrors.length = 0;
pageErrors.push(...uniqueErrors);

const errorCount = pageErrors.length + consoleMessages.filter((m) => m.type === 'error').length;
const checks = [...requestChecks, ...noRequestChecks, ...textChecks];
const failedChecks = checks.filter((c) => !c.ok);
const ok = !navError
  && (navStatus === null || navStatus < 400)
  && failedChecks.length === 0
  && (opts.allowErrors || errorCount === 0)
  && clicked.every((c) => c.ok);

const evidence = {
  tool: 'capture_page.mjs',
  captured_at: stamp,
  url: opts.url,
  final_url: finalUrl,
  title,
  viewport: `${vw}x${vh}`,
  browser: browserChannel,
  nav_status: navStatus,
  nav_error: navError,
  clicked,
  text_checks: textChecks,
  request_checks: [...requestChecks, ...noRequestChecks],
  console_errors: consoleMessages.filter((m) => m.type === 'error'),
  console_warnings: consoleMessages.filter((m) => m.type === 'warning'),
  page_errors: pageErrors,
  failed_requests: failed,
  request_count: withStatus.length,
  requests: withStatus,
  screenshot: screenshotPath,
  warnings,
  verdict: ok ? 'PROVEN' : 'NOT PROVEN',
};
writeFileSync(`${base}.json`, JSON.stringify(evidence, null, 2));

await context.close();
await browser.close();

console.log(`${evidence.verdict}  nav=${navStatus ?? navError}  requests=${withStatus.length}  errors=${errorCount}`);
for (const c of textChecks) console.log(`  text  ${c.ok ? 'OK  ' : 'MISS'}  ${JSON.stringify(c.text)}`);
for (const c of requestChecks) console.log(`  req   ${c.ok ? 'OK  ' : 'MISS'}  /${c.pattern}/  x${c.count}${c.samples[0] ? `  ${c.samples[0].url} -> ${c.samples[0].status}` : ''}`);
for (const c of noRequestChecks) console.log(`  req   ${c.ok ? 'OK  ' : 'SENT'}  NOT /${c.pattern}/  x${c.count}`);
for (const e of pageErrors.slice(0, 5)) console.log(`  error ${e.kind}: ${e.message}`);
for (const w of warnings) console.log(`  warn  ${w}`);
if (screenshotPath) console.log(`  shot  ${screenshotPath}`);
console.log(`evidence: ${base}.json`);
process.exit(ok ? 0 : 1);
