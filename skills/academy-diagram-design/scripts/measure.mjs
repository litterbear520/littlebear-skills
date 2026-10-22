#!/usr/bin/env node
// 用法：node measure.mjs <原图> <查询.json>
// 在原图上取色、量文字墨迹、找框边。查询是一个数组，每项是下面一种（都可以带 "label" 方便认）：
//   {"op":"px",  "x":20, "y":20}                          取 5×5 邻域的中位色（避开压缩噪点）
//   {"op":"ink", "box":[x0,y0,x1,y1], "dark":110}         盒内比 dark 暗的像素的外接框：文字墨迹的左右上下
//   {"op":"run", "y":300, "x0":0, "x1":1920, "min":2}     沿一行列出颜色分段（长度 ≥ min）：找框的左右边、线宽
//   {"op":"col", "x":500, "y0":0, "y1":1080, "min":2}     沿一列列出颜色分段：找框的上下边、虚线的段长
//   {"op":"top", "box":[x0,y0,x1,y1], "n":6}              盒内最多的几种颜色：细笔画、代码字的颜色
import fs from 'node:fs';
import path from 'node:path';
import { dataUri, die, withChrome } from './lib.mjs';

const [img, queryFile] = process.argv.slice(2);
if (!img || !queryFile) die('用法：node measure.mjs <原图> <查询.json>');
const queries = JSON.parse(fs.readFileSync(queryFile, 'utf8'));

const SCRIPT = `(async () => {
  const img = new Image();
  img.src = ${JSON.stringify(dataUri(path.resolve(img)))};
  await img.decode();
  const W = img.naturalWidth, H = img.naturalHeight;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d');
  g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, W, H).data;
  const at = (x, y) => { const i = (y * W + x) * 4; return [d[i], d[i + 1], d[i + 2]]; };
  const hex = (p) => '#' + p.map((v) => v.toString(16).padStart(2, '0')).join('');
  const lum = (p) => 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2];
  const q12 = (p) => p.map((v) => Math.min(255, Math.round(v / 12) * 12));
  const segs = (pts, min) => {
    const out = []; let prev = null, start = 0;
    pts.forEach(([pos, h], i) => {
      if (h !== prev) { if (prev !== null) out.push([start, pts[i - 1][0], prev]); prev = h; start = pos; }
    });
    out.push([start, pts[pts.length - 1][0], prev]);
    return out.filter(([a, b]) => b - a + 1 >= (min ?? 1)).map(([a, b, h]) => a + '-' + b + ':' + h).join(' ');
  };
  const lines = ['尺寸 ' + W + '×' + H];
  for (const t of ${JSON.stringify(queries)}) {
    const tag = (t.label ? t.label + ' ' : '');
    if (t.op === 'px') {
      const ps = [];
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) ps.push(at(t.x + dx, t.y + dy));
      const med = [0, 1, 2].map((k) => ps.map((p) => p[k]).sort((a, b) => a - b)[12]);
      lines.push(tag + 'px(' + t.x + ',' + t.y + ') ' + hex(med));
    } else if (t.op === 'ink') {
      const [x0, y0, x1, y1] = t.box; let a = 1e9, b = 1e9, e = -1, f = -1;
      for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
        if (lum(at(x, y)) < (t.dark ?? 110)) { a = Math.min(a, x); e = Math.max(e, x); b = Math.min(b, y); f = Math.max(f, y); }
      }
      lines.push(tag + 'ink[' + t.box + '] ' + (e < 0 ? '没有墨迹' : 'x ' + a + '-' + e + '（宽 ' + (e - a + 1) + '） y ' + b + '-' + f + '（高 ' + (f - b + 1) + '）'));
    } else if (t.op === 'run') {
      const pts = []; for (let x = t.x0; x <= t.x1; x++) pts.push([x, hex(q12(at(x, t.y)))]);
      lines.push(tag + 'run y=' + t.y + ': ' + segs(pts, t.min));
    } else if (t.op === 'col') {
      const pts = []; for (let y = t.y0; y <= t.y1; y++) pts.push([y, hex(q12(at(t.x, y)))]);
      lines.push(tag + 'col x=' + t.x + ': ' + segs(pts, t.min));
    } else if (t.op === 'top') {
      const [x0, y0, x1, y1] = t.box; const cnt = new Map();
      for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
        const h = hex(at(x, y).map((v) => Math.min(255, Math.round(v / 16) * 16))); cnt.set(h, (cnt.get(h) ?? 0) + 1);
      }
      lines.push(tag + 'top[' + t.box + '] ' + [...cnt].sort((p, q) => q[1] - p[1]).slice(0, t.n ?? 6).map(([h, n]) => h + ':' + n).join(' '));
    }
  }
  return lines.join('\\n');
})()`;

console.log(await withChrome(async (page) => {
  await page.goto('<!doctype html><meta charset="utf-8">', 'measure');
  return page.eval(SCRIPT);
}));
