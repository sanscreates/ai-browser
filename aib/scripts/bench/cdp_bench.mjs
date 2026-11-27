// Copyright 2026 The AI Browser Authors. BSD-3-Clause (same as Chromium).
//
// Drives a Chromium-based browser over the DevTools protocol and prints a
// JSON line of measurements. Used by aib/scripts/bench.sh; needs Node 22+
// (global WebSocket, fetch). Run with Chromium's bundled node:
//   third_party/node/mac_arm64/node-darwin-arm64/bin/node cdp_bench.mjs \
//     --binary "/path/App.app/Contents/MacOS/App" --tasks startup,memory,speedometer
//
// Measurements:
//   startup     spawn -> first rendered local page, fresh profile (1st run)
//               and warm (same profile) runs; median of warm runs
//   memory      summed RSS of the browser's process tree: 1 idle tab after
//               30 s, then 10 tabs after 60 s
//   speedometer Speedometer 3.1 score
//   jetstream   JetStream 2.2 score
//   motionmark  MotionMark 1.3.1 score

import {spawn, execFileSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => {
  if (a.startsWith('--')) acc.push([a.slice(2), all[i + 1]]);
  return acc;
}, []));
const BINARY = args.binary;
const TASKS = (args.tasks || 'startup,memory,speedometer,jetstream,motionmark').split(',');
const WARM_RUNS = Number(args['warm-runs'] || 5);
const sleep = ms => new Promise(r => setTimeout(r, ms));

// Identical flags for every browser under test: no first-run UI and no
// background throttling (the window may be occluded on a shared machine).
const COMMON_FLAGS = [
  '--no-first-run', '--no-default-browser-check',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
  '--disable-backgrounding-occluded-windows', '--remote-debugging-port=0',
  '--window-size=1400,1000',
];

class Browser {
  static async launch(profile, url) {
    const b = new Browser();
    b.profile = profile;
    // A warm run reuses the profile; drop the previous run's port file.
    fs.rmSync(path.join(profile, 'DevToolsActivePort'), {force: true});
    b.t0 = performance.now();
    b.proc = spawn(BINARY, [...COMMON_FLAGS, `--user-data-dir=${profile}`, url],
                   {stdio: 'ignore'});
    // The browser writes DevToolsActivePort ("<port>\n<path>") once its
    // DevTools server is up; it may briefly exist but be empty.
    const portFile = path.join(profile, 'DevToolsActivePort');
    let port = '';
    for (let i = 0; i < 600 && !/^\d+$/.test(port); i++) {
      await sleep(50);
      try {
        port = fs.readFileSync(portFile, 'utf8').split('\n')[0].trim();
      } catch {}
    }
    if (!/^\d+$/.test(port)) throw new Error('no DevToolsActivePort');
    b.base = `http://127.0.0.1:${port}`;
    return b;
  }
  async targets() {
    // DevToolsActivePort can appear before the HTTP endpoint accepts
    // connections; retry briefly.
    for (let i = 0; ; i++) {
      try {
        return await (await fetch(`${this.base}/json/list`)).json();
      } catch (e) {
        if (i >= 200) throw e;
        await sleep(25);
      }
    }
  }
  async page(pred) {
    for (let i = 0; i < 1200; i++) {
      const t = (await this.targets()).find(x => x.type === 'page' && pred(x));
      if (t) return new Page(t.webSocketDebuggerUrl);
      await sleep(50);
    }
    throw new Error('page not found');
  }
  async newTab(url) {
    await fetch(`${this.base}/json/new?${encodeURI(url)}`, {method: 'PUT'});
  }
  rssKb() {
    const out = execFileSync('ps', ['-A', '-o', 'pid=,ppid=,rss=']).toString();
    const kids = new Map();
    const rss = new Map();
    for (const line of out.trim().split('\n')) {
      const [pid, ppid, r] = line.trim().split(/\s+/).map(Number);
      rss.set(pid, r);
      if (!kids.has(ppid)) kids.set(ppid, []);
      kids.get(ppid).push(pid);
    }
    let total = 0;
    const stack = [this.proc.pid];
    while (stack.length) {
      const p = stack.pop();
      total += rss.get(p) || 0;
      stack.push(...(kids.get(p) || []));
    }
    return total;
  }
  async close() {
    this.proc.kill('SIGTERM');
    for (let i = 0; i < 200 && this.proc.exitCode === null; i++) await sleep(50);
    if (this.proc.exitCode === null) this.proc.kill('SIGKILL');
  }
}

class Page {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 0;
    this.pending = new Map();
    this.ready = new Promise(r => this.ws.addEventListener('open', r));
    this.ws.addEventListener('message', ev => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        this.pending.get(msg.id)(msg);
        this.pending.delete(msg.id);
      }
    });
  }
  async send(method, params = {}) {
    await this.ready;
    const id = ++this.id;
    this.ws.send(JSON.stringify({id, method, params}));
    return new Promise(r => this.pending.set(id, r));
  }
  async eval(expr) {
    const r = await this.send('Runtime.evaluate',
                              {expression: expr, returnByValue: true,
                               awaitPromise: true});
    return r.result?.result?.value;
  }
  async waitFor(expr, timeoutMs, pollMs = 1000) {
    const end = Date.now() + timeoutMs;
    while (Date.now() < end) {
      const v = await this.eval(expr).catch(() => undefined);
      if (v !== undefined && v !== null && v !== '' && v !== false) return v;
      await sleep(pollMs);
    }
    return null;
  }
  close() { this.ws.close(); }
}

const MARK = 'data:text/html,<title>aib-bench</title>ready';

async function startup(results) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'aib-bench-'));
  const runs = [];
  for (let i = 0; i <= WARM_RUNS; i++) {
    const b = await Browser.launch(profile, MARK);
    const p = await b.page(t => t.title === 'aib-bench');
    await p.waitFor('document.readyState === "complete"', 30000, 20);
    runs.push(performance.now() - b.t0);
    p.close();
    await b.close();
    await sleep(2000);
  }
  const warm = runs.slice(1).sort((a, b) => a - b);
  results.startup_fresh_profile_ms = Math.round(runs[0]);
  results.startup_warm_median_ms = Math.round(warm[Math.floor(warm.length / 2)]);
  fs.rmSync(profile, {recursive: true, force: true});
}

const TEN_TABS = [
  'https://en.wikipedia.org/wiki/Web_browser', 'https://example.com/',
  'https://developer.mozilla.org/en-US/docs/Web/JavaScript',
  'https://www.rust-lang.org/', 'https://www.python.org/',
  'https://en.wikipedia.org/wiki/Chromium_(web_browser)',
  'https://news.ycombinator.com/', 'https://www.gnu.org/',
  'https://developer.apple.com/documentation/', 'https://www.w3.org/',
];

async function memory(results) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'aib-bench-'));
  const b = await Browser.launch(profile, MARK);
  (await b.page(t => t.title === 'aib-bench')).close();
  await sleep(30000);
  results.memory_idle_1tab_mb = Math.round(b.rssKb() / 1024);
  for (const u of TEN_TABS) {
    await b.newTab(u);
    await sleep(1500);
  }
  await sleep(60000);
  results.memory_10tabs_mb = Math.round(b.rssKb() / 1024);
  await b.close();
  fs.rmSync(profile, {recursive: true, force: true});
}

async function webBench(results, key, url, startExpr, scoreExpr, timeoutMs) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'aib-bench-'));
  const b = await Browser.launch(profile, url);
  const p = await b.page(t => t.url.startsWith(url.split('?')[0]));
  await p.waitFor('document.readyState === "complete"', 60000);
  await sleep(3000);
  if (startExpr) await p.eval(startExpr);
  const score = await p.waitFor(scoreExpr, timeoutMs, 5000);
  results[key] = score === null ? null : Number(String(score).replace(/[^\d.]/g, ''));
  p.close();
  await b.close();
  fs.rmSync(profile, {recursive: true, force: true});
}

const results = {binary: BINARY, date: new Date().toISOString()};
for (const task of TASKS) {
  try {
    if (task === 'startup') await startup(results);
    if (task === 'memory') await memory(results);
    if (task === 'speedometer') {
      await webBench(results, 'speedometer3', 'https://browserbench.org/Speedometer3.1/',
                     'document.querySelector("button.start-tests-button")?.click()',
                     'document.querySelector("#result-number")?.textContent',
                     30 * 60000);
    }
    if (task === 'jetstream') {
      await webBench(results, 'jetstream2', 'https://browserbench.org/JetStream2.2/',
                     'JetStream.start()',
                     'document.querySelector("#result-summary .score")?.textContent',
                     40 * 60000);
    }
    if (task === 'motionmark') {
      await webBench(results, 'motionmark', 'https://browserbench.org/MotionMark1.3.1/',
                     'benchmarkController.startBenchmark()',
                     'document.querySelector("#results .score")?.textContent',
                     30 * 60000);
    }
  } catch (e) {
    results[`${task}_error`] = String(e) + (e.cause ? ` (cause: ${e.cause})` : "");
    if (process.env.AIB_BENCH_DEBUG) console.error(e);
  }
}
console.log(JSON.stringify(results));
