// 几个脚本共用：找 Chrome，通过 DevTools 协议驱动无头 Chrome（Node 22 自带 WebSocket，不用装 puppeteer）。
// 机器内存小，有 flock 时所有调用排队，同一时间只开一个 Chrome。
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const SKILL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const STYLE = path.join(SKILL, 'assets/academy.css');
export const LATIN_FONTS = path.join(SKILL, 'assets/fonts/fonts.css');
// 中文字体：设了 CJK_FONTS_CSS 就用那份自托管的 @font-face CSS（图里的中文和正文同一套字形），否则用本机装的 Noto 字体
export const CJK_FONTS = process.env.CJK_FONTS_CSS ? path.resolve(process.env.CJK_FONTS_CSS) : null;

export const url = (p) => pathToFileURL(p).href;

export function fontLinks() {
  return [LATIN_FONTS, CJK_FONTS]
    .filter((p) => p && fs.existsSync(p))
    .map((p) => `<link rel="stylesheet" href="${url(p)}">`)
    .join('\n');
}

export function tmp(name) {
  const dir = path.join(os.tmpdir(), 'academy-diagram');
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, name);
}

export function dataUri(file) {
  const ext = path.extname(file).slice(1).toLowerCase().replace('jpg', 'jpeg');
  return `data:image/${ext};base64,${fs.readFileSync(file).toString('base64')}`;
}

export function die(msg) {
  console.error(msg);
  process.exit(2);
}

const CANDIDATES = [
  process.env.CHROME,
  '/opt/google/chrome/chrome',
  'google-chrome',
  'google-chrome-stable',
  'chromium',
  'chromium-browser',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
];

function findChrome() {
  for (const c of CANDIDATES) {
    if (!c) continue;
    if (c.includes('/')) {
      if (fs.existsSync(c)) return c;
    } else if (spawnSync('which', [c]).status === 0) {
      return c;
    }
  }
  throw new Error('找不到 Chrome：把环境变量 CHROME 设成浏览器可执行文件的路径');
}

// 用一个 flock 进程占住锁，Chrome 用完再放开；没有 flock（如 macOS）就不排队
async function lock() {
  if (spawnSync('which', ['flock']).status !== 0) return () => {};
  const file = path.join(os.tmpdir(), 'academy-diagram-chrome.lock');
  const holder = spawn('flock', ['-w', '900', file, '-c', 'echo locked; cat'], { stdio: ['pipe', 'pipe', 'ignore'] });
  await new Promise((resolve, reject) => {
    holder.stdout.on('data', (d) => String(d).includes('locked') && resolve());
    holder.on('exit', () => reject(new Error('等了 15 分钟还没轮到用 Chrome')));
  });
  return () => holder.stdin.end();
}

// 开一个 Chrome，把一个 page 对象交给 fn：goto(html) 打开页面，eval(js) 求值（会等 Promise），shot(path, w, h) 截图
export async function withChrome(fn) {
  const release = await lock();
  // Chrome 在 TMPDIR 和配置目录里建 Unix socket，路径超过 108 字节就直接崩：TMPDIR 太长时一律退回 /tmp
  const base = os.tmpdir().length > 40 && fs.existsSync('/tmp') ? '/tmp' : os.tmpdir();
  const profile = fs.mkdtempSync(path.join(base, 'academy-chrome-'));
  const proc = spawn(findChrome(), [
    '--headless=new', '--no-proxy-server', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
    '--allow-file-access-from-files', '--remote-debugging-port=0', '--remote-allow-origins=*',
    // 文字用灰度抗锯齿：默认的亚像素抗锯齿会在字边留下蓝、橙色毛边，图缩小后很显眼
    '--disable-lcd-text', '--font-render-hinting=none',
    `--user-data-dir=${profile}`, 'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'], env: { ...process.env, TMPDIR: base } });
  try {
    const wsUrl = await new Promise((resolve, reject) => {
      let log = '';
      proc.stderr.on('data', (d) => {
        log += d;
        const m = log.match(/DevTools listening on (ws:\/\/\S+)/);
        if (m) resolve(m[1]);
      });
      proc.on('exit', (code) => reject(new Error(`Chrome 没起来（退出码 ${code}）\n${log.slice(-800)}`)));
    });
    const ws = new WebSocket(wsUrl);
    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = () => reject(new Error('连不上 Chrome 的调试端口'));
    });
    let seq = 0;
    const pending = new Map();
    const waiters = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { resolve, reject } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result);
      } else if (msg.method) {
        for (const w of [...waiters]) if (w.method === msg.method) { waiters.splice(waiters.indexOf(w), 1); w.resolve(msg); }
      }
    };
    const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
    });
    const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
    const s = (method, params) => send(method, params, sessionId);
    await s('Page.enable');
    const size = (width, height) => s('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });

    const page = {
      async goto(html, name = 'page', width = 1920, height = 1080) {
        await size(width, height);
        const file = tmp(`${name}.html`);
        fs.writeFileSync(file, html);
        const loaded = new Promise((resolve) => waiters.push({ method: 'Page.loadEventFired', resolve }));
        await s('Page.navigate', { url: url(file) });
        await loaded;
        // 等字体都到位、再多走两帧，截图里的字才是最终字体
        await page.eval('document.fonts.ready.then(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))))');
      },
      async eval(expression) {
        const r = await s('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
        if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
        return r.result.value;
      },
      async shot(file, width, height, { format = 'png', quality } = {}) {
        await size(width, height);
        await page.eval('new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))');
        const { data } = await s('Page.captureScreenshot', { format, ...(quality ? { quality } : {}), clip: { x: 0, y: 0, width, height, scale: 1 } });
        fs.mkdirSync(path.dirname(file), { recursive: true });
        fs.writeFileSync(file, Buffer.from(data, 'base64'));
      },
    };
    const result = await fn(page);
    await send('Browser.close').catch(() => {});
    ws.close();
    return result;
  } finally {
    await new Promise((resolve) => {
      if (proc.exitCode !== null) return resolve();
      const t = setTimeout(() => { proc.kill('SIGKILL'); resolve(); }, 5000);
      proc.on('exit', () => { clearTimeout(t); resolve(); });
    });
    fs.rmSync(profile, { recursive: true, force: true });
    release();
  }
}
