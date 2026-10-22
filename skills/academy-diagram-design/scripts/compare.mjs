#!/usr/bin/env node
// 用法：node compare.mjs <原图> <复刻.png> <输出前缀>
// 产出两张图：
//   <前缀>-stack.png  上原图、下复刻，给人并排看
//   <前缀>-diff.png   两张相减：一样的地方是黑的，亮出来的轮廓就是位置、字号或粗细没对上的地方
import path from 'node:path';
import { url, die, withChrome } from './lib.mjs';

const [orig, rep, prefix] = process.argv.slice(2);
if (!orig || !rep || !prefix) die('用法：node compare.mjs <原图> <复刻.png> <输出前缀>');
const [o, r, p] = [orig, rep, prefix].map((f) => path.resolve(f));

await withChrome(async (page) => {
  await page.goto('<!doctype html><meta charset="utf-8">', 'compare-size');
  const [w, h] = await page.eval(`(async () => { const i = new Image(); i.src = ${JSON.stringify(url(o))}; await i.decode(); return [i.naturalWidth, i.naturalHeight]; })()`);
  const W = 1920;
  const H = Math.round((W * h) / w);
  const bar = (text) => `<div style="height:56px;display:flex;align-items:center;padding:0 24px;background:#3a3a37;color:#f0efec;font:500 26px sans-serif">${text}</div>`;
  const img = (src, extra = '') => `<img src="${url(src)}" style="display:block;width:${W}px;height:${H}px;${extra}">`;

  await page.goto(`<!doctype html><meta charset="utf-8"><body style="margin:0">${bar('上：原图')}${img(o)}${bar('下：复刻')}${img(r)}</body>`, 'compare-stack', W, 2 * H + 112);
  await page.shot(`${p}-stack.png`, W, 2 * H + 112);

  await page.goto(`<!doctype html><meta charset="utf-8"><body style="margin:0;background:#000"><div style="position:relative;width:${W}px;height:${H}px">${img(o, 'position:absolute;inset:0')}${img(r, 'position:absolute;inset:0;mix-blend-mode:difference')}</div></body>`, 'compare-diff', W, H);
  await page.shot(`${p}-diff.png`, W, H);
});
console.log(`${p}-stack.png\n${p}-diff.png`);
