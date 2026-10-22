#!/usr/bin/env node
// 用法：node calib.mjs <样本.json>
// 认字体、反推字号：把同一串字用候选字体在 100px 下渲染，量墨迹的宽高，和原图上量到的宽 W、高 H 比。
// 宽、高推出的字号相差在 5% 以内，说明字体认对了；字号取宽度推出的那个（高度容易被上下伸的笔画带偏）。
// 样本是数组：[{"text":"Our Server","family":"Lora","weight":400,"style":"normal","W":270,"H":39}]
// 输出的“基线 = 墨迹顶 + r × 字号”里的 r，用来从原图的墨迹顶算出 SVG 里该写的基线 y。
import fs from 'node:fs';
import { fontLinks, die, withChrome } from './lib.mjs';

const file = process.argv[2];
if (!file) die('用法：node calib.mjs <样本.json>');
const cases = JSON.parse(fs.readFileSync(file, 'utf8'));

const SCRIPT = `(async () => {
  const lines = [];
  for (const c of ${JSON.stringify(cases)}) {
    const font = (c.style || 'normal') + ' ' + (c.weight || 400) + ' 100px "' + c.family + '"';
    await document.fonts.load(font, c.text);
    const cv = document.createElement('canvas'); cv.width = 4000; cv.height = 320;
    const g = cv.getContext('2d');
    g.fillStyle = '#fff'; g.fillRect(0, 0, 4000, 320); g.fillStyle = '#000'; g.font = font; g.fillText(c.text, 20, 220);
    const d = g.getImageData(0, 0, 4000, 320).data;
    let a = 1e9, b = 1e9, e = -1, f = -1;
    for (let y = 0; y < 320; y++) for (let x = 0; x < 4000; x++) {
      if (d[(y * 4000 + x) * 4] < 110) { a = Math.min(a, x); e = Math.max(e, x); b = Math.min(b, y); f = Math.max(f, y); }
    }
    const w = e - a + 1, h = f - b + 1;
    const byW = 100 * c.W / w, byH = 100 * c.H / h;
    const ok = Math.abs(byW - byH) / byW <= 0.05 ? '吻合' : '不吻合';
    lines.push(c.text + ' — ' + font.replace(' 100px', '') + '：按宽 ' + byW.toFixed(1) + 'px，按高 ' + byH.toFixed(1) + 'px（' + ok + '）；基线 = 墨迹顶 + ' + ((220 - b) / 100).toFixed(2) + ' × 字号');
  }
  return lines.join('\\n');
})()`;

console.log(await withChrome(async (page) => {
  await page.goto(`<!doctype html><meta charset="utf-8">${fontLinks()}`, 'calib');
  return page.eval(SCRIPT);
}));
