#!/usr/bin/env node
// 用法：node render.mjs <图.svg> [--webp <路径>] [--png <路径>] [--no-webp] [--quality 90]
// 把 SVG 连同 academy.css 和字体放进一张网页：先检查，再截 PNG 和 WebP。
// 默认 WebP 写在 SVG 旁边（同名），PNG 写到临时目录给自己看（路径会打印出来）。
// 检查有 ERROR 时退出码为 1，图照样产出，方便对着图改。
import fs from 'node:fs';
import path from 'node:path';
import { STYLE, fontLinks, url, tmp, die, withChrome } from './lib.mjs';

const argv = process.argv.slice(2);
if (!argv.length || argv[0].startsWith('-')) {
  die('用法：node render.mjs <图.svg> [--webp <路径>] [--png <路径>] [--no-webp] [--quality 90]');
}
const opt = (name) => {
  const i = argv.indexOf(name);
  return i > 0 ? argv[i + 1] : undefined;
};
const svgPath = path.resolve(argv[0]);
const base = path.basename(svgPath, '.svg');
const pngPath = path.resolve(opt('--png') ?? tmp(`${base}.png`));
const webpPath = argv.includes('--no-webp')
  ? null
  : path.resolve(opt('--webp') ?? path.join(path.dirname(svgPath), `${base}.webp`));
const quality = Number(opt('--quality') ?? 90);

const svg = fs.readFileSync(svgPath, 'utf8');
const vb = svg.match(/viewBox\s*=\s*"\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"/);
if (!vb) die('SVG 根元素要写 viewBox，比如 viewBox="0 0 1920 1080"');
const W = 1920;
const H = Math.round((W * Number(vb[2])) / Number(vb[1]));
// 调色板就是 academy.css 里出现的颜色
const palette = [...new Set((fs.readFileSync(STYLE, 'utf8').match(/#[0-9a-f]{6}\b/gi) ?? []).map((c) => c.toLowerCase()))];

const html = `<!doctype html><html><head><meta charset="utf-8">
${fontLinks()}
<link rel="stylesheet" href="${url(STYLE)}">
<style>html,body{margin:0;background:#f4f7f2;overflow:hidden}body>svg{display:block;width:${W}px;height:${H}px}</style>
</head><body>${svg}</body></html>`;

// 先把含中文的斜体改正体（中文没有斜体字形，浏览器会硬压斜），再检查
const CHECK = `(async () => {
  const CJK = /[\\u2e80-\\u9fff\\uf900-\\ufaff\\uff00-\\uffef]/;
  const LATIN = /[A-Za-z0-9]/;
  const svg = document.querySelector('body > svg');
  for (const t of svg.querySelectorAll('text, tspan')) {
    if (CJK.test(t.textContent) && getComputedStyle(t).fontStyle !== 'normal') {
      t.style.fontStyle = 'normal';
      t.setAttribute('data-upright', '');
    }
  }
  await document.fonts.ready;

  const vb = svg.viewBox.baseVal;
  const sr = svg.getBoundingClientRect();
  const k = vb.width / sr.width;
  const box = (el) => {
    const r = el.getBoundingClientRect();
    return { x: (r.left - sr.left) * k + vb.x, y: (r.top - sr.top) * k + vb.y, w: r.width * k, h: r.height * k };
  };
  const errors = [], warns = [], infos = [], used = new Set();
  const faces = [...document.fonts].filter((f) => f.status === 'loaded')
    .map((f) => ({ fam: f.family.replace(/["']/g, ''), style: f.style, w: f.weight.split(' ').map(Number) }));
  const has = (fam, style, w) => faces.some((f) => f.fam === fam && f.style === style && w >= f.w[0] && w <= (f.w[1] ?? f.w[0]));
  const name = (t) => '「' + t.textContent.trim().replace(/\\s+/g, ' ').slice(0, 20) + '」';
  const texts = [...svg.querySelectorAll('text')].filter((t) => t.textContent.trim() && !t.closest('defs'));

  // 文字的“字身”：横向取渲染宽度，纵向取基线上 0.72em 到基线下 0.12em，免得把字体自带的上下留白算成重叠
  const core = (t) => {
    const b = box(t), size = parseFloat(getComputedStyle(t).fontSize);
    const y = t.y.baseVal.numberOfItems ? t.y.baseVal.getItem(0).value : null;
    const down = CJK.test(t.textContent) ? 0.14 : 0.12;  // 中文字身比英文更往下沉
    return y === null ? b : { x: b.x, w: b.w, y: y - 0.72 * size, h: (0.72 + down) * size };
  };

  for (const t of texts) {
    const cs = getComputedStyle(t);
    const fams = cs.fontFamily.split(',').map((f) => f.trim().replace(/["']/g, ''));
    const w = Number(cs.fontWeight), style = cs.fontStyle, size = parseFloat(cs.fontSize);
    if (LATIN.test(t.textContent)) {
      used.add(fams[0] + ' ' + w + (style === 'italic' ? ' 斜体' : ''));
      if (!has(fams[0], style, w)) warns.push(name(t) + ' 要的字体没有：' + fams[0] + ' ' + w + ' ' + style + '（会用回退字体或合成粗体、斜体）');
    }
    if (CJK.test(t.textContent)) {
      const cjk = fams.find((f) => /SC$/.test(f));
      if (cjk) used.add(cjk); else warns.push(name(t) + ' 有中文，但字体列表里没有 Noto Serif SC / Noto Sans SC');
    }
    if (size < 24) warns.push(name(t) + ' 字号 ' + size + 'px：在 1920 宽画布上小于 24，放进正文后太小');
    if (t.hasAttribute('data-upright')) infos.push(name(t) + ' 含中文，已改成正体');
  }

  const cores = texts.map((t) => ({ t, c: core(t) }));
  for (const { t, c } of cores) {
    if (c.x < vb.x - 1 || c.y < vb.y - 1 || c.x + c.w > vb.x + vb.width + 1 || c.y + c.h > vb.y + vb.height + 1) errors.push(name(t) + ' 出了画布');
  }
  for (let i = 0; i < cores.length; i++) for (let j = i + 1; j < cores.length; j++) {
    const a = cores[i].c, b = cores[j].c;
    const ix = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
    const iy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
    if (ix > 2 && iy > 2) warns.push(name(cores[i].t) + ' 和 ' + name(cores[j].t) + ' 叠在一起');
  }

  // 文字落在哪个框里（包含文字中心的最小色块或框），就不该超出那个框
  const shapes = [...svg.querySelectorAll('rect, path, circle, ellipse, polygon')]
    .filter((s) => !s.closest('defs, marker') && !s.classList.contains('bg'))
    .filter((s) => {
      const cs = getComputedStyle(s);
      return (cs.fill !== 'none' && cs.fillOpacity !== '0') || (cs.stroke !== 'none' && s.tagName !== 'path');
    })
    .map((s) => {
      // 描边一半压在框里，框的内沿要往里收
      const cs = getComputedStyle(s), b = box(s);
      const half = cs.stroke !== 'none' ? parseFloat(cs.strokeWidth) / 2 : 0;
      return { s, b: { x: b.x + half, y: b.y + half, w: b.w - 2 * half, h: b.h - 2 * half } };
    })
    .filter(({ b }) => b.w > 20 && b.h > 20 && b.w * b.h < vb.width * vb.height * 0.9);
  for (const { t, c } of cores) {
    const cx = c.x + c.w / 2, cy = c.y + c.h / 2;
    const hit = shapes.filter(({ b }) => cx > b.x && cx < b.x + b.w && cy > b.y && cy < b.y + b.h)
      .sort((p, q) => p.b.w * p.b.h - q.b.w * q.b.h)[0];
    if (!hit) continue;
    // 左右至少留 6，上下至少留 3：中文比英文大写字母更往下沉，贴边时肉眼看着就是顶到框
    const b = hit.b, padX = 6, padY = 3;
    const sides = [
      c.x < b.x + padX && '左边', c.x + c.w > b.x + b.w - padX && '右边',
      c.y < b.y + padY && '上边', c.y + c.h > b.y + b.h - padY && '下边',
    ].filter(Boolean);
    if (sides.length) {
      warns.push(name(t) + ' 顶到或超出所在框的' + sides.join('、') + '（框内宽 ' + Math.round(b.w) + '、高 ' + Math.round(b.h) + '；字宽 ' + Math.round(c.w) + '）');
    }
  }

  // 颜色只用 academy.css 里的
  const pal = new Set(${JSON.stringify(palette)});
  const hex = (v) => {
    const m = v.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
    return m ? '#' + [m[1], m[2], m[3]].map((n) => Number(n).toString(16).padStart(2, '0')).join('') : null;
  };
  const off = new Map();
  for (const el of svg.querySelectorAll('rect, path, circle, ellipse, polygon, polyline, line, text, tspan')) {
    if (el.closest('defs') && !el.closest('marker')) continue;
    const cs = getComputedStyle(el);
    const props = ['line', 'polyline'].includes(el.tagName) ? ['stroke'] : ['fill', 'stroke'];
    for (const p of props) {
      if (cs[p] === 'none' || (p === 'fill' && cs.fillOpacity === '0')) continue;
      const h = hex(cs[p]);
      if (h && !pal.has(h)) off.set(h, (off.get(h) ?? 0) + 1);
    }
  }
  for (const [h, n] of off) warns.push('颜色 ' + h + ' 不在 academy.css 的调色板里（' + n + ' 处），改用类名');

  return { errors, warns, infos, fonts: [...used] };
})()`;

const report = await withChrome(async (page) => {
  await page.goto(html, `${base}-render`, W, H);
  const r = await page.eval(CHECK);
  await page.shot(pngPath, W, H);
  if (webpPath) await page.shot(webpPath, W, H, { format: 'webp', quality });
  return r;
});

console.log(`检查 ${path.relative(process.cwd(), svgPath)}`);
console.log(`  字体：${report.fonts.join('、') || '（没有文字）'}`);
for (const e of report.errors) console.log(`  ERROR ${e}`);
for (const w of report.warns) console.log(`  WARN  ${w}`);
for (const i of report.infos) console.log(`  INFO  ${i}`);
if (!report.errors.length && !report.warns.length) console.log('  没有问题');
console.log(`PNG  ${pngPath}（${W}×${H}，${Math.round(fs.statSync(pngPath).size / 1024)} KB）`);
if (webpPath) console.log(`WebP ${webpPath}（${Math.round(fs.statSync(webpPath).size / 1024)} KB）`);
process.exit(report.errors.length ? 1 : 0);
