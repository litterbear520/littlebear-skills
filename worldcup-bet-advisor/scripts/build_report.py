#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 merged.json（数据）+ analysis.json（模型的判断与三档方案）渲染成单文件 HTML 报告。
视觉：Anthropic 编辑感纸张美学（亮）/ 暖炭灰（暗），Fraunces 衬线标题，等宽数字，价值高亮克制。

特性：
- 双主题（亮/暗），跟随系统、可手动切换并记忆（localStorage），<head> 内联防闪白。
- 左侧文档大纲目录：大块（赛程/三档/博冷/复盘）+ 逐场（开赛时间+全名）跳转 + 主题切换 + 导出 PDF；
  滚动高亮当前所在节；宽屏常驻、窄屏收成 ☰ 目录抽屉。
- 渐进披露：每场常驻"结论卡 + 重点玩法（胜平负）"，全部赔率表 / 模型讨论默认折叠。
- 模型品牌图标（内联 SVG，零网络依赖，主题自适应）。
- PDF 导出：window.print() + @media print（自动展开折叠、隐藏导航/按钮、A4 分页、强制浅色）。

analysis.json 由模型产出，schema 见 SKILL.md。本脚本只负责确定性渲染 + 串关赔率计算，
不做判断。缺 analysis 条目的比赛会以"仅数据"形式呈现。
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from functools import reduce
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BEIJING = timezone(timedelta(hours=8))


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def emph(s):
    """门面摘要专用的轻量强调：先转义，再把 **关键词** 渲染成 <strong>。
    其余 Markdown 一律不解析——避免裸 ** 当字面量漏到页面上（开头摘要最忌讳的杂乱）。"""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(s))


def fmt_kickoff(iso, fmt="%m-%d %H:%M"):
    """kickoff_at 是 UTC ISO（如 2026-06-17T17:00:00+00:00）；统一转北京时间(+8)显示，
    与竞彩侧/截图一致。解析失败则退回原样切片。"""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
        dt = dt.astimezone(BEIJING) if dt.tzinfo else dt + timedelta(hours=8)
        return dt.strftime(fmt)
    except Exception:
        return str(iso).replace("T", " ")[:16]


def conf_dots(n):
    n = max(0, min(5, int(n or 0)))
    return '<span class="dots">' + "●" * n + '<span class="dots-o">' + "○" * (5 - n) + "</span></span>"


def parlay_odds(legs):
    vals = [l.get("odds") for l in legs if l.get("odds")]
    if not vals:
        return None
    return round(reduce(lambda a, b: a * b, vals, 1.0), 2)


def fp(x):
    return f"{round(x*100):d}%" if isinstance(x, (int, float)) else ""


def pct(x):
    return round(x * 100) if isinstance(x, (int, float)) else None


# ---------- 模型品牌图标（内联 SVG / 主题自适应） ----------
_P_CLAUDE = ("m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729"
             "-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179"
             ".1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 "
             "9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607"
             ".2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733"
             "-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287"
             ".1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429"
             ".8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468"
             "-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429"
             "-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 "
             "1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 "
             "1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136"
             "-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857"
             "-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 "
             "2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l"
             ".4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 "
             "17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468"
             ".3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 "
             "1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 "
             "1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467"
             ".2307-.2429 1.9064-1.3114Z")

_P_OPENAI = ("M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 "
             "6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 "
             "5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 "
             "24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0"
             "-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a"
             ".7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 "
             "0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a"
             ".7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 "
             "4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 "
             "0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 "
             "0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 "
             "2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142"
             "-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284"
             "-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 "
             "0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 "
             "0 0-.3927.6813zm1.0976-2.3654 2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z")

_P_DEEPSEEK = ("M23.748 4.651c-.254-.124-.364.113-.512.233-.051.04-.094.09-.137.137-.372.397-.806.657"
               "-1.373.626-.829-.046-1.537.214-2.163.848-.133-.782-.575-1.248-1.247-1.548-.352-.155-.708"
               "-.311-.955-.65-.172-.24-.219-.509-.305-.774-.055-.16-.11-.323-.293-.35-.2-.031-.278.136"
               "-.356.276-.313.572-.434 1.202-.422 1.84.027 1.436.633 2.58 1.838 3.393.137.094.172.187.129"
               ".323-.082.28-.18.553-.266.833-.055.179-.137.218-.328.14a5.5 5.5 0 0 1-1.737-1.179c-.857"
               "-.828-1.631-1.743-2.597-2.46a12 12 0 0 0-.689-.47c-.985-.957.13-1.743.387-1.836.27-.098"
               ".094-.433-.778-.428-.872.003-1.67.295-2.687.685a3 3 0 0 1-.465.136 9.6 9.6 0 0 0-2.883"
               "-.101c-1.885.21-3.39 1.1-4.497 2.622C.082 8.776-.231 10.854.152 13.02c.403 2.284 1.568 "
               "4.175 3.36 5.653 1.857 1.533 3.997 2.284 6.438 2.14 1.482-.085 3.132-.284 4.994-1.86.47"
               ".234.962.328 1.78.398.629.058 1.235-.031 1.705-.129.735-.155.684-.836.418-.961-2.155"
               "-1.004-1.682-.595-2.112-.926 1.095-1.295 2.768-3.598 3.284-6.733.05-.346.115-.834.108"
               "-1.114-.004-.171.035-.238.23-.257a4.2 4.2 0 0 0 1.545-.475c1.397-.763 1.96-2.016 2.093"
               "-3.517.02-.23-.004-.467-.247-.588M11.58 18.168c-2.088-1.642-3.101-2.183-3.52-2.16-.39.024"
               "-.32.472-.234.763.09.288.207.487.371.74.114.167.192.416-.113.603-.673.416-1.842-.14-1.897"
               "-.168-1.361-.801-2.5-1.86-3.301-3.306-.775-1.393-1.225-2.888-1.299-4.482-.02-.385.094-.522"
               ".477-.592a4.7 4.7 0 0 1 1.53-.038c2.131.311 3.946 1.264 5.467 2.774.868.86 1.525 1.887 "
               "2.202 2.89.72 1.066 1.494 2.082 2.48 2.915.348.291.626.513.892.677-.802.09-2.14.109-3.055"
               "-.615zm1.001-6.44a.306.306 0 0 1 .415-.287.3.3 0 0 1 .113.074.3.3 0 0 1 .086.214c0 .17"
               "-.136.307-.308.307a.303.303 0 0 1-.306-.307m3.11 1.596c-.2.081-.4.151-.591.16a1.25 1.25 0 "
               "0 1-.798-.254c-.274-.23-.47-.358-.551-.758a1.7 1.7 0 0 1 .015-.588c.07-.327-.007-.537-.238"
               "-.727-.188-.156-.426-.199-.689-.199a.6.6 0 0 1-.254-.078.253.253 0 0 1-.114-.358 1 1 0 0 1 "
               ".192-.21c.356-.202.767-.136 1.146.016.352.144.618.408 1.001.782.392.451.462.576.685.915"
               ".176.264.336.536.446.848.066.194-.02.353-.25.45")

_P_GEMINI = ("M11.04 19.32Q12 21.51 12 24q0-2.49.93-4.68.96-2.19 2.58-3.81t3.81-2.55Q21.51 12 24 12q-2.49 "
             "0-4.68-.93a12.3 12.3 0 0 1-3.81-2.58 12.3 12.3 0 0 1-2.58-3.81Q12 2.49 12 0q0 2.49-.96 4.68"
             "-.93 2.19-2.55 3.81a12.3 12.3 0 0 1-3.81 2.58Q2.49 12 0 12q2.49 0 4.68.96 2.19.93 3.81 "
             "2.55t2.55 3.81")

# GLM / Kimi 无公开标准矢量，用简洁字形简标（随主题适配）
_P_GLM = "M5 4H19V7.6L10.6 16.4H19V20H5V16.4L13.4 7.6H5Z"
_P_KIMI = "M6 4H10V10.6L16.4 4H21.4L13.6 11.8L21.6 20H16.5L10 13.1V20H6Z"

# c: 品牌色 / "mono"（随主题黑白）/ "grad"（Gemini 渐变）
BRAND_SVG = {
    "Claude":   ("#D97757", f'<path d="{_P_CLAUDE}"/>'),
    "DeepSeek": ("#4D6BFE", f'<path d="{_P_DEEPSEEK}"/>'),
    "GPT":      ("mono",    f'<path d="{_P_OPENAI}"/>'),
    "OpenAI":   ("mono",    f'<path d="{_P_OPENAI}"/>'),
    "Gemini":   ("grad",    _P_GEMINI),  # 渐变在 brand_icon 里按实例生成唯一 id（见 _GEM）
    "GLM":      ("mono",    f'<path d="{_P_GLM}"/>'),
    "Kimi":     ("mono",    f'<path d="{_P_KIMI}"/>'),
}
_BRAND_ALIAS = {"claude": "Claude", "deepseek": "DeepSeek", "gpt": "GPT", "openai": "GPT",
                "chatgpt": "GPT", "gemini": "Gemini", "glm": "GLM", "zhipu": "GLM",
                "kimi": "Kimi", "moonshot": "Kimi"}

# Gemini 是唯一用渐变填充的图标。整页若复用同一个 id="gemg"，Safari/部分 WebKit 会
# 因「重复 id 的 paint server」解析失败而把星形画成透明（暗色背景下=看不见）。
# 故每个实例生成一个唯一 id，让每个 <svg> 自包含、跨浏览器都稳。
_GEM = [0]


def _gemini_svg():
    _GEM[0] += 1
    gid = f"gemg{_GEM[0]}"
    return (f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="24" y2="24" '
            f'gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#4285F4"/>'
            f'<stop offset=".5" stop-color="#9168C0"/><stop offset="1" stop-color="#D96570"/>'
            f'</linearGradient></defs><path fill="url(#{gid})" d="{_P_GEMINI}"/>')


def brand_icon(brand, cls=""):
    key = (brand or "").strip()
    norm = BRAND_SVG.get(key) and key or _BRAND_ALIAS.get(key.lower())
    spec = BRAND_SVG.get(norm) if norm else None
    if not spec:
        return f'<span class="bic gen {cls}">{esc(key[:1].upper() or "?")}</span>'
    c, inner = spec
    if c == "grad":
        return f'<span class="bic {cls}"><svg viewBox="0 0 24 24" aria-hidden="true">{_gemini_svg()}</svg></span>'
    if c == "mono":
        return f'<span class="bic mono {cls}"><svg viewBox="0 0 24 24" aria-hidden="true">{inner}</svg></span>'
    return f'<span class="bic {cls}" style="color:{c}"><svg viewBox="0 0 24 24" aria-hidden="true">{inner}</svg></span>'


# ---------- 玩法表 ----------
def single_badge(flag):
    return '<span class="single yes">可单买这场</span>' if flag else '<span class="single no">只能串着买</span>'


def prob_cell(p):
    if p is None:
        return '<td class="num soft"></td>'
    return (f'<td class="num soft"><span class="probc"><span class="pbar"><i style="width:{p}%"></i></span>'
            f'<span class="pn">{p}%</span></span></td>')


def odds_table(title, outcomes, single_flag, value_labels, label_key="label"):
    if not outcomes:
        return ""
    rows = ""
    for o in outcomes:
        lab = o.get(label_key) or o.get("sel") or ""
        is_val = lab in value_labels or o.get("sel") in value_labels
        cls = ' class="val"' if is_val else ""
        star = ' <span class="vmark">价值</span>' if is_val else ""
        rows += (f'<tr{cls}><td class="lab">{esc(lab)}{star}</td>'
                 f'<td class="num od">{o.get("odds","")}</td>{prob_cell(pct(o.get("fair_prob")))}</tr>')
    return f'''<div class="mkt">
      <div class="mkt-h"><span class="mkt-t">{esc(title)}</span>{single_badge(single_flag)}</div>
      <table><thead><tr><th>选项</th><th class="num">赔率</th><th class="num">真实概率</th></tr></thead>
      <tbody>{rows}</tbody></table></div>'''


def score_block(score_mk, single_flag, value_labels):
    outs = score_mk.get("outcomes", [])
    if not outs:
        return ""
    top = score_mk.get("top", [])
    chips = "".join(f'<span class="chip">{esc(t["label"])} <b>{t["odds"]}</b> <i>{fp(t.get("fair_prob"))}</i></span>'
                    for t in top)
    side_name = {"home": "主胜", "draw": "平局", "away": "客胜"}
    full = ""
    for side in ("home", "draw", "away"):
        sub = [o for o in outs if o.get("side") == side]
        if not sub:
            continue
        cells = "".join(
            f'<span class="sc {"val" if o["label"] in value_labels else ""}">{esc(o["label"])}<b>{o["odds"]}</b></span>'
            for o in sub)
        full += f'<div class="sc-row"><span class="sc-side">{side_name[side]}</span>{cells}</div>'
    return f'''<div class="mkt wide">
      <div class="mkt-h"><span class="mkt-t">比分</span>{single_badge(single_flag)}</div>
      <div class="top-chips"><span class="tc-l">最可能</span>{chips}</div>
      <details><summary>展开全部比分赔率</summary><div class="sc-full">{full}</div></details></div>'''


# ---------- 比赛卡 ----------
def rank_compare(m):
    """FIFA 排名对比条：主/客分列两端，更强的一侧(排名数字更小)高亮，中间用文字点出差距，
    让强弱悬殊一眼可见。排名缺失/非数字则降级为空(不渲染)。"""
    if not m.get("odds_matched"):
        return ""
    try:
        hr, ar = int(m.get("homerank")), int(m.get("awayrank"))
    except (TypeError, ValueError):
        return ""
    gap = abs(hr - ar)
    gtxt = "实力接近" if gap <= 5 else (f"相差 {gap} 位" if gap <= 20 else f"实力悬殊 · 差 {gap} 位")
    hcls = " strong" if hr < ar else ""
    acls = " strong" if ar < hr else ""
    return (f'<div class="rankcmp" title="FIFA 排名数字越小越强">'
            f'<span class="rk{hcls}"><i>FIFA</i><b>{hr}</b></span>'
            f'<span class="rk-gap">{gtxt}</span>'
            f'<span class="rk{acls}"><i>FIFA</i><b>{ar}</b></span></div>')


# ---------- 嘉豪先疯一句（逐字呈现，不做解读） ----------
FAN_LABELS = ["我更看好", "常规时间方向", "最可能比分", "我敢押的一个具体画面"]


# 四点标签可能各占一行，也可能内联挤在同一行（DeepSeek 偶发把四点写成一段）。
# 按"标签出现位置"切片、不依赖换行——否则行首正则的 (.*)$ 会把同行后面的标签一起吞进首个字段。
_FAN_FINDER = re.compile(r'(我更看好|常规时间方向|最可能比分|我敢押[^：:\n]{0,12})\s*[：:]')


def extract_fan_block(md):
    """从 discussion_md 抠出『## 嘉豪先疯一句』那一段的四个要点，原文照搬。
    各模型措辞不一（缩进 / 全角冒号 / 加粗 / 四点内联同一行），按标签出现位置切片。"""
    if not md:
        return None
    mt = re.search(r'##\s*嘉豪先疯一句\s*(.*?)(?:\n\s*---|\n\s*##|\Z)', md, re.S)
    if not mt:
        return None
    text = mt.group(1).replace("**", "")
    hits = [(mm.start(), mm.end(),
             "我敢押的一个具体画面" if mm.group(1).startswith("我敢押") else mm.group(1))
            for mm in _FAN_FINDER.finditer(text)]
    out = {}
    for i, (st, en, lab) in enumerate(hits):
        nxt = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        val = re.sub(r'[\s\-*·•]+$', '', text[en:nxt].strip())
        if val and lab not in out:
            out[lab] = val.strip()
    return out or None


def render_fan_card(model):
    """单模型嘉豪先疯一句卡片：四行原话照搬。比分行单独高亮（用户最关心的『猜测比分』）。"""
    fb = extract_fan_block(model.get("discussion_md"))
    if not fb:
        return ""
    rows = ""
    for lab in FAN_LABELS:
        if not fb.get(lab):
            continue
        cls = " fan-score" if lab == "最可能比分" else (" fan-pic" if lab.startswith("我敢押") else "")
        rows += (f'<div class="fan-row{cls}"><span class="fan-k">{esc(lab)}</span>'
                 f'<span class="fan-v">{esc(fb[lab])}</span></div>')
    if not rows:
        return ""
    return (f'<div class="fan"><div class="fan-h">{brand_icon(model.get("brand"))}'
            f'<span class="brand">{esc(model.get("brand",""))}</span>'
            f'<span class="mname">{esc(model.get("model_name",""))}</span></div>{rows}</div>')


def render_market(m):
    """市场视角（纯赔率事实，不含我们的判断）：胜平负去水概率 + 比分榜 top。
    去水＝把赔率换成概率再扣掉庄家抽水，代表市场实际怎么看这场。"""
    mk = m.get("markets") or {}
    spf = mk.get("spf") or {}
    outs = [o for o in (spf.get("outcomes") or []) if o.get("fair_prob") is not None]
    fav = max(outs, key=lambda o: o["fair_prob"], default=None)
    bars = ""
    for o in outs:
        fpb = o["fair_prob"]
        bars += (f'<div class="mkt-bar{" fav" if o is fav else ""}">'
                 f'<span class="mkt-nm">{esc(o.get("label",""))}</span>'
                 f'<span class="mkt-track"><span style="width:{round(fpb*100)}%"></span></span>'
                 f'<b class="mkt-pct">{fp(fpb)}</b>'
                 f'<span class="mkt-od">@{esc(str(o.get("odds","")))}</span></div>')
    top = (mk.get("score") or {}).get("top") or []
    tops = "".join(f'<span class="mkt-sc">{esc(o["label"])}<i>{fp(o["fair_prob"])}</i></span>'
                   for o in top[:5] if o.get("fair_prob") is not None)
    if not bars and not tops:
        return ""
    judge = f'市场最看好 <b>{esc(fav.get("label",""))}</b>（去水 {fp(fav["fair_prob"])}）' if fav else ""
    bars_block = (f'<div class="mkt-bars"><div class="mkt-l">胜平负 · 去水概率</div>{bars}</div>'
                  if bars else "")
    tops_block = (f'<div class="mkt-tops"><div class="mkt-l">比分榜 · 市场最看好</div>'
                  f'<div class="mkt-scs">{tops}</div></div>' if tops else "")
    judge_block = f'<p class="mkt-judge">{judge}</p>' if judge else ""
    return (f'<div class="market"><div class="market-h">市场怎么看</div>'
            f'{judge_block}{bars_block}{tops_block}</div>')


def render_match(idx, m, a, value_labels):
    """单场：市场视角（赔率事实）+ 各模型嘉豪先疯一句原文 + 折叠的全部玩法赔率。不含任何我们的分析判断。"""
    ta, tb = esc(m["team_a"]), esc(m["team_b"])
    lot = esc(m.get("lotteryid", ""))
    ko = esc(fmt_kickoff(m.get("kickoff_at")))

    # 各模型嘉豪先疯一句（原文照搬）
    fans = "".join(render_fan_card(mod) for mod in m.get("models", []))
    fans_block = (f'<div class="fans"><div class="fans-l">⬡ 嘉豪先疯一句 · 各模型原话</div>'
                  f'<div class="fans-grid">{fans}</div></div>') if fans else ""

    # 玩法倍率：胜平负常驻为"重点玩法"，其余折叠
    key_html, rest_html = "", ""
    if m.get("odds_matched"):
        mk = m["markets"]
        sg = m.get("singles", {})
        spf = mk.get("spf", {})
        score_html = score_block(mk.get("score", {}), sg.get("score"), value_labels)
        rq = mk.get("rqspf", {})
        rq_html = (odds_table(f"让球（{rq.get('line')}）", rq["outcomes"], sg.get("rqspf"),
                              value_labels, label_key="sel") if rq.get("outcomes") else "")
        goals_html = odds_table("总进球", mk.get("goals", {}).get("outcomes", []), sg.get("goals"), value_labels)
        htft_html = odds_table("半全场", mk.get("htft", {}).get("outcomes", []), sg.get("htft"), value_labels)
        rest_items = []
        if spf.get("outcomes"):
            key_html = odds_table("胜平负", spf["outcomes"], sg.get("spf"), value_labels)
            if score_html:
                rest_items.append(("比分", score_html))
        else:
            key_html = score_html
        for name, h in (("让球", rq_html), ("总进球", goals_html), ("半全场", htft_html)):
            if h:
                rest_items.append((name, h))
        if rest_items:
            sub = " · ".join(n for n, _ in rest_items)
            inner = "".join(h for _, h in rest_items)
            rest_html = (f'<details class="fold"><summary><span class="fold-t">展开全部玩法赔率</span>'
                         f'<span class="fold-s">{sub}</span></summary>'
                         f'<div class="markets">{inner}</div></details>')
    else:
        key_html = f'<div class="no-odds">⚠ {esc(m.get("odds_note","暂无倍率数据"))}</div>'
    key_block = f'<div class="key-mkt">{key_html}</div>' if key_html else ""

    delay = min(idx * 0.05, 0.3)
    return f'''<section class="match reveal" id="m{idx}" style="animation-delay:{delay:.2f}s">
      <div class="m-top">
        <span class="m-id">{lot}</span>
        <h2>{team_logo_img(m.get("team_a_logo"), "m-logo")}{ta} <span class="vs">vs</span> {team_logo_img(m.get("team_b_logo"), "m-logo")}{tb}</h2>
        <div class="m-meta"><span class="ko">{ko}</span></div>
      </div>
      {rank_compare(m)}
      {render_market(m)}
      {fans_block}
      {key_block}
      {rest_html}
    </section>'''


# ---------- 各模型猜测比分一览（tab 切换比赛 · 共识视角） ----------
_SCORE_TOK = re.compile(r'(\d{1,2})\s*[:\-：]\s*(\d{1,2})')


def _score_tokens(s):
    """把一个模型的比分原话拆成归一比分 token 列表（主-客，统一成『a:b』）。
    支持 '1-0 / 1-1' 多选、'2:1 或 1:0' 等夹字写法；同模型内去重保序。
    若整串抠不出任何 数:数 ，退回清洗后的原文当单 token（不丢信息）。"""
    if not s:
        return []
    toks, seen = [], set()
    for a, b in _SCORE_TOK.findall(s):
        t = f"{int(a)}:{int(b)}"
        if t not in seen:
            seen.add(t)
            toks.append(t)
    if toks:
        return toks
    raw = str(s).strip()
    return [raw] if raw else []


def render_model_scores(order):
    """嘉豪 · 各模型猜测比分一览（共识视角）：把视角从「模型→比分」翻成「比分→哪些模型 + 几个」。
    同一比分被越多模型提到，排得越靠上、占比条越长（扎堆=值得留意）；命中市场比分榜的再标出市场去水概率。
    比分一律用 agent 归一后的『主队-客队』朝向；多比分（如 1:0 / 1:1）拆开各计一次。"""
    panels, heads, n = "", "", 0
    for m in order:
        # 1) 收集每个模型的归一比分 token（缺归一才退回原话抽取）
        picks = []  # [(brand, [tok,...])]
        for mod in m.get("models", []):
            sc = mod.get("pred_score_norm")
            if not sc:
                fb = extract_fan_block(mod.get("discussion_md"))
                sc = (fb or {}).get("最可能比分")
            toks = _score_tokens(sc)
            if toks:
                picks.append((mod.get("brand", ""), toks))
        if not picks:
            continue
        n_models = len(picks)
        # 2) 市场比分榜（去水概率），键归一成 a:b 以便和模型比分对齐
        top = ((m.get("markets") or {}).get("score") or {}).get("top") or []
        mkt_prob = {}
        for o in top:
            lab = o.get("label")
            if lab and o.get("fair_prob") is not None:
                mkt_prob[str(lab).replace("-", ":").replace("：", ":")] = o["fair_prob"]
        # 3) 按比分聚合：score -> [brand,...]（同比分内同模型去重）
        tally = {}
        for brand, toks in picks:
            for t in toks:
                bs = tally.setdefault(t, [])
                if brand not in bs:
                    bs.append(brand)
        # 4) 排序：选的人多优先 → 市场概率高优先 → 比分字串兜底
        items = sorted(tally.items(),
                       key=lambda kv: (-len(kv[1]), -(mkt_prob.get(kv[0]) or 0), kv[0]))
        maxc = max(len(v) for _, v in items)
        rows = ""
        for score, brands in items:
            cnt = len(brands)
            pctw = round(cnt / n_models * 100)  # 占比＝该比分模型数 / 总模型数（与右侧 /N 一致）
            lead = cnt == maxc and maxc >= 2  # 全是 1 票时不高亮（谈不上扎堆）
            chips = "".join(f'<span class="msc-chip">{brand_icon(b)}<i>{esc(b)}</i></span>'
                            for b in brands)
            prob = mkt_prob.get(score)
            mk = f'<span class="msc-mk2">市场 {fp(prob)}</span>' if prob is not None else ""
            tag = '<span class="msc-tag">最多模型</span>' if lead else ""
            # 横条轨道靠「比分 + 条 + 定宽计数」固定，长短只由人数决定；变宽的标签放到第二行
            tags = f'<div class="msc-tags">{tag}{mk}</div>' if (tag or mk) else ""
            rows += (f'<div class="msc-row{" lead" if lead else ""}">'
                     f'<div class="msc-head"><span class="msc-sc">{esc(score)}</span>'
                     f'<div class="msc-bar"><span style="width:{pctw}%"></span></div>'
                     f'<span class="msc-cnt"><b>{cnt}</b><i>/{n_models}</i></span></div>'
                     f'<div class="msc-foot"><div class="msc-chips">{chips}</div>{tags}</div></div>')
        # 5) 市场比分榜兜底行：没被任何模型选中的高概率比分也别丢
        mkt = "".join(f'<span class="msc-mk">{esc(o["label"])}<i>{fp(o["fair_prob"])}</i></span>'
                      for o in top[:4] if o.get("fair_prob") is not None)
        mkt_row = (f'<div class="msc-mktrow"><span class="msc-mkl">市场比分榜</span>'
                   f'<span class="msc-scs">{mkt}</span></div>') if mkt else ""
        ta, tb = esc(m["team_a"]), esc(m["team_b"])
        on = " on" if n == 0 else ""
        heads += (f'<button class="tab ms-tab{on}" type="button" role="tab" data-i="{n}">'
                  f'<span class="tt"><span class="tn">{ta}<i>vs</i>{tb}</span></span></button>')
        panels += (f'<div class="tab-panel ms-panel{on}" role="tabpanel" data-i="{n}">'
                   f'<div class="msc-list">{rows}</div>{mkt_row}</div>')
        n += 1
    if not panels:
        return ""
    return (f'<section class="modelscores reveal" id="modelscores">'
            f'<div class="mb-head"><span class="mb-k">⬡ 嘉豪预测</span>'
            f'<h2 class="mb-title">各模型猜测比分一览</h2></div>'
            f'<p class="mb-intro">把同一比分被几个模型提到摆到一起——选的模型越多，排得越靠上、占比条越长，<b>扎堆＝该画面值得留意</b>。每行图标即选它的模型；多比分（如 1:0 / 1:1）拆开各计一次。命中市场比分榜的标出市场去水概率（模型＋市场都看好＝信号更强）。点上方标签切换比赛。</p>'
            f'<div class="tabs ms-tabs"><div class="tabs-head" role="tablist">{heads}</div>{panels}</div></section>')


def render_retro(retro):
    """报告最顶部的"上期复盘"：上一期各模型的下注 + 猜分对照终场，沿用报告自身的视觉母题
    （准确率榜＝鼠尾草进度条 + Fraunces 数字；逐场＝今日赛程同款卡片：队徽 + 终场比分 + 谁押中）。
    纯呈现 retro.json 里的确定性事实，不写本站判断/校准/买法。无 retro 即不渲染。"""
    if not retro or not retro.get("matches"):
        return ""
    summary = retro.get("summary", [])
    matches = retro.get("matches", [])
    order = [s["brand"] for s in summary]  # 排名顺序：榜单 + 卡片里"谁押中"都按它

    # —— 准确率榜：每模型一行，方向命中率走鼠尾草进度条，数字走 Fraunces ——
    rows = ""
    for i, s in enumerate(summary):
        brand = s["brand"]
        dh, dt = s.get("dir_hit", 0), s.get("dir_total", 0)
        sc, st = s.get("score_hit", 0), s.get("score_total", 0)
        pct = round(dh / dt * 100) if dt else 0
        lead = i == 0 and dh > 0
        tag = '<span class="rt-tag">上期最准</span>' if lead else ""
        sc_cls = "" if sc else " zero"
        rows += (
            f'<div class="rt-row{" lead" if lead else ""}">'
            f'<span class="rt-rank">{i+1}</span>'
            f'<span class="rt-who">{brand_icon(brand)}<i>{esc(brand)}</i>{tag}</span>'
            f'<span class="rt-meter"><span class="rt-track"><span style="width:{pct}%"></span></span>'
            f'<span class="rt-dir">{dh}<i>/{dt} 方向</i></span></span>'
            f'<span class="rt-sc{sc_cls}">比分 <b>{sc}/{st}</b></span>'
            f'</div>')

    # —— 逐场卡片：照搬今日赛程卡片骨架，中央换终场比分，底部列谁押中方向 / 谁猜中比分 ——
    cards = ""
    for m in matches:
        cells = m.get("cells", {})
        dir_hits = [b for b in order if cells.get(b, {}).get("dir")]
        score_hits = [b for b in order if cells.get(b, {}).get("score")]

        final_disp = esc(m.get("final", ""))

        def dir_chips(brands):
            # 方向：图标 + 悬停看该模型押了啥
            return "".join(
                f'<span class="rt-hit" title="{esc(b)}：押 {esc(cells.get(b,{}).get("bet",""))}">'
                f'{brand_icon(b)}</span>' for b in brands)

        def score_chips(brands):
            # 比分：图标 + 命中的那个比分（=终场），悬停看该模型完整猜分（含没中的备选）
            return "".join(
                f'<span class="rt-schit" title="{esc(b)} 猜 {esc(cells.get(b,{}).get("pred",""))}">'
                f'{brand_icon(b)}<b>{final_disp}</b></span>' for b in brands)

        dir_cell = (f'<span class="rt-hits dir">{dir_chips(dir_hits)}</span>'
                    if dir_hits else '<span class="rt-none">六家全黑</span>')
        score_cell = (f'<span class="rt-hits">{score_chips(score_hits)}</span>'
                      if score_hits else '<span class="rt-none">无</span>')
        up = '<span class="up">冷</span>' if m.get("upset") else ""
        final = final_disp.replace(":", " : ")
        cards += (
            f'<div class="rt-card{" up" if m.get("upset") else ""}">'
            f'<div class="rt-c-top"><span class="rt-c-stage">终场</span>'
            f'<span class="rt-c-res">{esc(m.get("result",""))}{up}</span></div>'
            f'<div class="rt-mid">'
            f'<span class="rt-team">{team_logo_img(m.get("team_a_logo"),"rt-logo")}<b>{esc(m.get("team_a",""))}</b></span>'
            f'<span class="rt-score">{final}</span>'
            f'<span class="rt-team">{team_logo_img(m.get("team_b_logo"),"rt-logo")}<b>{esc(m.get("team_b",""))}</b></span></div>'
            f'<div class="rt-foot">'
            f'<div class="rt-line"><span class="lab">方向命中</span>{dir_cell}</div>'
            f'<div class="rt-line"><span class="lab">比分命中</span>{score_cell}</div></div>'
            f'</div>')

    date = esc(retro.get("reviewed_date", ""))
    return (f'<section class="retro reveal" id="retro">'
            f'<div class="mb-head"><span class="mb-k">⬡ 上期复盘</span>'
            f'<h2 class="mb-title">上期各模型准确率 · {date} {retro.get("n_matches",0)}场</h2></div>'
            f'<p class="mb-intro">上一期各模型的下注与「最可能比分」对照终场——只摆事实，不构成本站倾向。'
            f'方向＝实际下注（含让球结算）是否押中胜平负；比分＝最可能比分是否完全命中（多个比分命中任一即算）。</p>'
            f'<div class="rt-sub">各模型准确率 · 按方向命中排序</div>'
            f'<div class="rt-board">{rows}</div>'
            f'<div class="rt-sub">逐场 · 终场比分与谁押中</div>'
            f'<div class="rt-grid">{cards}</div></section>')


def render_nav(order, sections):
    """左侧文档大纲目录栏：先列在场的大块（赛程/三档/博冷/复盘），再逐场。
    sections = [(anchor_id, label), ...]（只含本报告实际存在的大块）。
    宽屏常驻、窄屏收成 ☰ 目录抽屉（JS 控制 .open + 遮罩）。滚动高亮见 MAIN_JS。"""
    secs = "".join(f'<a href="#{sid}" class="nj-sec">{esc(lab)}</a>' for sid, lab in sections)
    jumps = ""
    for i, m in enumerate(order, 1):
        ko = esc(fmt_kickoff(m.get("kickoff_at"), "%H:%M"))
        jumps += (f'<a href="#m{i}" class="nj-match"><span class="nj-ko">{ko}</span>'
                  f'<span class="nj-nm">{esc(m["team_a"])}<i> / </i>{esc(m["team_b"])}</span></a>')
    match_label = '<div class="nj-label">逐场分析</div>' if jumps else ""
    # 图标：panel = 展开（浮动钮）；chevron« = 收起（侧栏内）
    panel_icon = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
                  'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                  '<rect x="3" y="4.5" width="18" height="15" rx="2.5"/>'
                  '<line x1="9.4" y1="4.5" x2="9.4" y2="19.5"/></svg>')
    chev_icon = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                 '<polyline points="14.5 6.5 9 12 14.5 17.5"/></svg>')
    return f'''<button class="toc-toggle" id="tocToggle" type="button" aria-label="展开目录" title="目录">{panel_icon}</button>
<div class="toc-scrim" id="tocScrim"></div>
<nav class="sidebar" id="toc" aria-label="报告目录">
  <div class="sb-head">
    <div class="sb-brand"><span class="sb-k">World Cup 2026</span><span class="sb-t">玩法分析</span></div>
    <button class="sb-collapse" id="tocCollapse" type="button" aria-label="收起目录" title="收起目录">{chev_icon}</button>
  </div>
  <div class="nav-jump">{secs}{match_label}{jumps}</div>
  <div class="nav-act">
    <button id="themeBtn" class="nbtn" type="button" aria-label="切换深浅色">
      <span class="ti" aria-hidden="true"></span><span class="tlabel"></span></button>
    <button id="pdfBtn" class="nbtn primary" type="button"><span aria-hidden="true">⤓</span> 导出 PDF</button>
  </div>
</nav>'''


def team_logo_img(logo, cls="sch-logo"):
    """有 base64 徽标(team_*_logo)就渲染圆形 <img>，否则空圆占位——纯文字降级，不报错。"""
    if logo:
        return f'<img class="{cls}" src="{logo}" alt="" loading="lazy">'
    return f'<span class="{cls} ph" aria-hidden="true"></span>'


def render_schedule(order):
    """标题下、三档方案上的"今日赛程"卡片栅格。每卡 = 队徽 + 队名 + 阶段 + 开赛(北京时间) + 排名，
    整卡是 <a href="#mN"> 点击平滑跳到下方对应分析区（复用比赛卡锚点 + scroll-margin-top）。"""
    if not order:
        return ""
    cards = ""
    for i, m in enumerate(order, 1):
        stage = esc(m.get("stage") or "赛程")
        lot = esc(m.get("lotteryid") or "")
        ko = esc(fmt_kickoff(m.get("kickoff_at"), "%H:%M"))
        day = esc(fmt_kickoff(m.get("kickoff_at"), "%m-%d"))
        rank = ""
        if m.get("odds_matched") and m.get("homerank") and m.get("awayrank"):
            rank = f'<span class="sch-rank">FIFA {esc(m.get("homerank"))} · {esc(m.get("awayrank"))}</span>'
        foot = " · ".join(x for x in (lot, day) if x)
        cards += f'''<a class="sch-card" href="#m{i}">
          <div class="sch-top"><span class="sch-stage">{stage}</span><span class="sch-status">未开赛</span></div>
          <div class="sch-mid">
            <span class="sch-team">{team_logo_img(m.get("team_a_logo"))}<b>{esc(m["team_a"])}</b></span>
            <span class="sch-ko">{ko}</span>
            <span class="sch-team">{team_logo_img(m.get("team_b_logo"))}<b>{esc(m["team_b"])}</b></span>
          </div>
          <div class="sch-foot"><span>{foot}</span>{rank}</div></a>'''
    return f'''<section class="schedule" id="sched"><div class="sch-h"><h2>今日赛程</h2>
      <span class="sch-sub">点击任意比赛跳到下方分析 · 北京时间</span></div>
      <div class="sch-grid">{cards}</div></section>'''


SEL_IDX = {"H": 0, "D": 1, "A": 2}  # selection_code → 盘口选项次序（spf:[胜,平,负] / rqspf:[让胜,让平,让负]）


def render_model_bets(order):
    """嘉豪 · 各模型下注一览：tab 切换比赛，每场把各模型图标落到它们在嘉豪实际下注的盘口选项格上。
    数据全部来自 models[].bet（pool_code 定盘口 HAD/HHAD、selection_code 定选项格 H/D/A），不依赖 lean。"""
    def has_bet(mm):
        return mm.get("has_bet") and isinstance(mm.get("bet"), dict)

    if not any(any(has_bet(mm) for mm in m.get("models", [])) for m in order):
        return ""
    heads, panels, n = "", "", 0
    for m in order:
        models = m.get("models", [])
        pools = [mm["bet"].get("pool_code") for mm in models if has_bet(mm) and mm["bet"].get("pool_code")]
        if not pools:
            continue
        pool = max(set(pools), key=pools.count)  # 主盘口：下注模型里出现最多的 pool_code
        ta, tb = esc(m["team_a"]), esc(m["team_b"])
        mk = m.get("markets", {})
        if pool == "HHAD":
            outs = (mk.get("rqspf", {}) or {}).get("outcomes", [])
            line = esc(str((mk.get("rqspf", {}) or {}).get("line", "")))
            pool_label = f"让球盘 · {ta} {line}"
            names = [f"{ta} 赢盘", "走盘 (平)", f"{tb} 赢盘"]
        else:
            outs = (mk.get("spf", {}) or {}).get("outcomes", [])
            pool_label = "标准盘 · 胜平负"
            names = [esc(o.get("label", "")) for o in outs]
        if not outs:
            continue
        odds = [o.get("odds") for o in outs]
        buckets = [[], [], []]
        for mm in models:
            if not has_bet(mm) or mm["bet"].get("pool_code") != pool:
                continue
            gi = SEL_IDX.get(mm["bet"].get("selection_code"))
            if gi is not None and gi < 3:
                buckets[gi].append(mm.get("brand"))
        total = sum(len(b) for b in buckets)
        topn = max((len(b) for b in buckets), default=0)
        cells = ""
        for gi in range(min(3, len(outs))):
            brands = buckets[gi]
            hot = " hot" if brands and len(brands) == topn else ""
            icons = ("".join(f'<span class="mb-ic">{brand_icon(b)}<i>{esc(b)}</i></span>' for b in brands)
                     or '<span class="mb-empty">—</span>')
            cnt = f'<span class="mb-cnt">{len(brands)}/{total}</span>' if brands else ""
            od = f'<span class="mb-odds">@{odds[gi]}</span>' if odds[gi] is not None else ""
            nm = names[gi] if gi < len(names) else ""
            cells += (f'<div class="mb-cell{hot}"><div class="mb-opt">'
                      f'<span class="mb-name">{nm}</span>{od}{cnt}</div>'
                      f'<div class="mb-icons">{icons}</div></div>')
        on = " on" if n == 0 else ""
        heads += (f'<button class="tab mb-tab{on}" type="button" role="tab" data-i="{n}">'
                  f'<span class="tt"><span class="tn">{ta}<i>vs</i>{tb}</span></span></button>')
        panels += (f'<div class="tab-panel mb-panel{on}" role="tabpanel" data-i="{n}">'
                   f'<div class="mb-pool">{pool_label}</div>'
                   f'<div class="mb-grid">{cells}</div></div>')
        n += 1
    if not panels:
        return ""
    return (f'<section class="modelbets reveal" id="modelbets">'
            f'<div class="mb-head"><span class="mb-k">⬡ 嘉豪预测</span>'
            f'<h2 class="mb-title">各模型下注一览</h2></div>'
            f'<p class="mb-intro">六个模型在嘉豪平台对每场的实际下注落位——点上方标签切换比赛，'
            f'高亮格是当前最多模型押的方向。</p>'
            f'<div class="tabs mb-tabs"><div class="tabs-head" role="tablist">{heads}</div>{panels}</div></section>')


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
 color-scheme:light;
 --paper:#FAF8F3;--paper2:#F1EBDD;--panel:#FFFFFF;--panel2:#FBF8F1;
 --ink:#1A1813;--ink2:#574F40;--muted:#928873;
 --line:#E8E1D1;--line2:#D7CDB8;
 --clay:#C2603F;--clay-d:#A2492E;--clay-t:#F6E7DD;
 --sage:#5E6B4F;--gold:#9A7A2C;
 --val-bg:#F8E9DE;--val-line:#E2B79B;
 --warn-bg:#F6EFD7;--warn-line:#DCC68A;--danger:#B0413A;--danger-bg:#F7E3DF;--danger-line:#E0B3AC;
 --upset:#9A4F63;--upset-d:#7E3E50;--upset-t:#F3E6EA;--upset-line:#DCBFC8;
 --brand-mono:#26221A;
 --shadow:0 1px 2px rgba(40,33,20,.05),0 14px 34px -18px rgba(40,33,20,.22);
 --shadow-s:0 1px 2px rgba(40,33,20,.05);
 --r:16px;--rs:11px;
}
[data-theme="dark"]{
 color-scheme:dark;
 /* 对齐 claude.ai 官网深色 token（从站点实采）：
    画布 bg-100 #1F1F1E（暖中性炭灰、饱和仅~2%，非近黑非橄榄），
    卡片靠"提亮"做层次→ bg-000 #2C2C2A（比画布更亮），凹陷面 bg-200 #181816，
    正文 text-000 #F8F8F6 暖白、次要 #C7C5BC、弱 #97948B；强调色用 Claude 官方陶土橘。 */
 --paper:#1F1F1E;--paper2:#181816;--panel:#2C2C2A;--panel2:#181816;
 --ink:#F8F8F6;--ink2:#C7C5BC;--muted:#97948B;
 --line:#343330;--line2:#403E39;
 --clay:#D97757;--clay-d:#E2906F;--clay-t:#3A2A22;
 --sage:#9DB082;--gold:#D7AC5E;
 --val-bg:#33271E;--val-line:#57442F;
 --warn-bg:#2B2615;--warn-line:#4E4327;--danger:#E08A7D;--danger-bg:#2E1A16;--danger-line:#5A352E;
 --upset:#CE8DA0;--upset-d:#DCA6B5;--upset-t:#2C1D24;--upset-line:#503641;
 --brand-mono:#ECEAE0;
 --shadow:0 1px 2px rgba(0,0,0,.4),0 18px 40px -20px rgba(0,0,0,.7);
 --shadow-s:0 1px 2px rgba(0,0,0,.35);
}
html{-webkit-font-smoothing:antialiased;scroll-behavior:smooth}
body{background:var(--paper);color:var(--ink);
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
 font-feature-settings:"tnum";line-height:1.6;padding:0 0 70px;position:relative;
 transition:padding-left .28s cubic-bezier(.4,0,.2,1)}
.bg{position:fixed;inset:0;z-index:-1;pointer-events:none;
 background:
  radial-gradient(58% 42% at 78% -6%, color-mix(in srgb,var(--clay) 12%,transparent), transparent 70%),
  radial-gradient(46% 38% at -8% 4%, color-mix(in srgb,var(--sage) 10%,transparent), transparent 70%)}
.wrap{max-width:1060px;margin:0 auto;padding:0 28px}
main.wrap{padding-top:26px}
.schedule,.plans-tabs,.upset,.retro{scroll-margin-top:22px}
h1,h2,h3,.serif{font-family:"Fraunces",Georgia,"Songti SC",serif;font-weight:500;letter-spacing:-.012em}
.num,td.num,th.num{font-variant-numeric:tabular-nums;text-align:right}
a{color:inherit}
/* header */
.hero{padding:54px 0 30px;position:relative}
.hero:after{content:"";display:block;height:1px;background:linear-gradient(90deg,transparent,var(--line2) 18%,var(--line2) 82%,transparent);margin-top:30px}
.kicker{display:inline-flex;align-items:center;gap:9px;font-size:11.5px;letter-spacing:.24em;text-transform:uppercase;color:var(--clay-d);font-weight:600;margin-bottom:16px}
.kicker:before{content:"";width:22px;height:1.5px;background:var(--clay)}
.hero h1{font-size:clamp(30px,4.6vw,46px);line-height:1.04;margin-bottom:14px;max-width:18ch}
.sub{color:var(--ink2);font-size:15.5px;max-width:62ch;line-height:1.65}
/* 开头「今日要点」：定调拆成的几条短句，清爽留白、陶土小圆点、加粗领词便于扫读 */
.lede{list-style:none;margin:18px 0 0;padding:0;max-width:66ch;display:flex;flex-direction:column;gap:10px}
.lede li{position:relative;padding-left:21px;font-size:14.5px;line-height:1.6;color:var(--ink2)}
.lede li:before{content:"";position:absolute;left:3px;top:8px;width:6px;height:6px;border-radius:50%;background:var(--clay)}
.lede strong{color:var(--ink);font-weight:600}
.meta-row{display:flex;gap:14px 26px;flex-wrap:wrap;margin-top:22px;font-size:12.5px;color:var(--muted);align-items:center}
.meta-row .mk-l{letter-spacing:.04em}
.meta-row b{color:var(--ink2);font-weight:600}
.agent-tags{display:inline-flex;gap:7px;vertical-align:middle}
.atag{display:inline-flex;align-items:center;gap:5px;background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:2px 10px 2px 4px;font-size:12.5px;font-weight:600;color:var(--ink);box-shadow:var(--shadow-s)}
/* sidebar — 左侧文档大纲目录（宽屏常驻 / 窄屏收成抽屉） */
.sidebar{position:fixed;top:0;left:0;width:248px;height:100vh;z-index:60;display:flex;flex-direction:column;
 background:color-mix(in srgb,var(--paper) 92%,var(--panel));border-right:1px solid var(--line);padding:22px 14px 16px;overflow:hidden;
 transition:transform .28s cubic-bezier(.4,0,.2,1)}
.sb-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;padding:0 4px 14px;margin-bottom:6px;border-bottom:1px solid var(--line)}
.sb-brand{display:flex;flex-direction:column;gap:3px;min-width:0;padding-left:4px}
.sb-collapse{flex:none;width:30px;height:30px;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--line);border-radius:9px;background:var(--panel);color:var(--ink2);cursor:pointer;box-shadow:var(--shadow-s);transition:background .16s,color .16s,border-color .16s,transform .16s}
.sb-collapse:hover{background:var(--paper2);color:var(--clay-d);border-color:var(--clay);transform:translateY(-1px)}
.sb-collapse svg{width:18px;height:18px}
.sb-k{font-size:10px;letter-spacing:.22em;text-transform:uppercase;color:var(--clay-d);font-weight:600}
.sb-t{font-family:"Fraunces",Georgia,serif;font-size:18px;font-weight:600;color:var(--ink)}
.nav-jump{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:2px;padding-right:2px;scrollbar-width:thin}
.nav-jump::-webkit-scrollbar{width:6px}
.nav-jump::-webkit-scrollbar-thumb{background:var(--line2);border-radius:3px}
.nav-jump a{position:relative;display:flex;align-items:baseline;gap:9px;text-decoration:none;color:var(--ink2);font-size:13px;line-height:1.35;padding:7px 10px;border-radius:9px;border-left:2px solid transparent;transition:background .16s,color .16s,border-color .16s}
.nav-jump a:hover{background:var(--paper2);color:var(--ink)}
.nav-jump a.on{background:var(--clay-t);color:var(--clay-d);border-left-color:var(--clay)}
.nj-sec{font-weight:700}
.nj-label{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:700;padding:14px 10px 5px;margin-top:6px;border-top:1px dashed var(--line2)}
.nj-match .nj-ko{flex:none;min-width:38px;font-variant-numeric:tabular-nums;font-size:11.5px;color:var(--muted);font-family:"Fraunces",Georgia,serif}
.nav-jump a.on .nj-ko{color:var(--clay-d)}
.nj-nm{min-width:0;font-weight:600}
.nj-nm i{font-style:normal;color:var(--muted)}
.nav-act{display:flex;gap:8px;padding-top:14px;margin-top:8px;border-top:1px solid var(--line)}
.nav-act .nbtn{flex:1;justify-content:center}
/* 浮动展开钮（收起后出现，左上角；图标式，克制优雅）*/
.toc-toggle{display:none;position:fixed;top:16px;left:16px;z-index:70;width:38px;height:38px;align-items:center;justify-content:center;padding:0;border:1px solid var(--line2);border-radius:11px;background:var(--panel);color:var(--ink2);cursor:pointer;box-shadow:var(--shadow);transition:color .16s,border-color .16s,transform .16s}
.toc-toggle:hover{color:var(--clay-d);border-color:var(--clay);transform:translateY(-1px)}
.toc-toggle svg{width:20px;height:20px}
.toc-scrim{display:none}
/* 宽屏：侧栏常驻、内容右让；收起后侧栏滑出、内容铺满、浮动钮浮现 */
@media(min-width:1101px){
 body{padding-left:248px}
 html.toc-collapsed body{padding-left:0}
 html.toc-collapsed .sidebar{transform:translateX(-100%)}
 html.toc-collapsed .toc-toggle{display:inline-flex}
}
/* 窄屏：侧栏默认收进屏外，☰ 浮动钮唤出抽屉 + 遮罩 */
@media(max-width:1100px){
 .sidebar{transform:translateX(-100%);width:272px}
 html.toc-open .sidebar{transform:none;box-shadow:0 24px 60px -18px rgba(0,0,0,.5)}
 .toc-toggle{display:inline-flex}
 html.toc-open .toc-toggle{display:none}
 .toc-scrim{display:block;position:fixed;inset:0;z-index:55;background:rgba(20,16,10,.42);opacity:0;pointer-events:none;transition:opacity .26s}
 html.toc-open .toc-scrim{opacity:1;pointer-events:auto}
}
.nbtn{display:inline-flex;align-items:center;gap:6px;font:inherit;font-size:12.5px;font-weight:600;cursor:pointer;border:1px solid var(--line2);background:var(--panel);color:var(--ink2);padding:7px 13px;border-radius:10px;transition:.18s;box-shadow:var(--shadow-s)}
.nbtn:hover{border-color:var(--clay);color:var(--clay-d);transform:translateY(-1px)}
.nbtn.primary{background:var(--clay);border-color:var(--clay);color:#fff}
.nbtn.primary:hover{background:var(--clay-d);color:#fff}
[data-theme="dark"] .nbtn.primary{color:#1a140f}
.ti:before{content:"☾";font-size:14px;line-height:1}
[data-theme="dark"] .ti:before{content:"☀"}
/* brand icon */
.bic{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:7px;background:var(--panel);border:1px solid var(--line);box-shadow:var(--shadow-s);flex:none;color:var(--clay);overflow:hidden}
.bic svg{width:62%;height:62%;fill:currentColor;display:block}
.bic.mono{color:var(--brand-mono)}
.bic.gen{font-size:11px;font-weight:800;color:var(--ink2);font-family:"Fraunces",serif}
/* plans — 三档：聚焦切换 Tabs（一次看一档，选中档独占全宽面板） */
.modelbets{margin-bottom:50px}
.mb-head{display:flex;align-items:baseline;gap:12px;margin-bottom:6px}
.mb-k{font-size:12px;font-weight:700;color:var(--clay-d);letter-spacing:.04em}
.mb-title{font-family:"Fraunces",Georgia,serif;font-size:21px;font-weight:600;color:var(--ink)}
.mb-intro{font-size:13px;color:var(--ink2);margin-bottom:16px;line-height:1.6;max-width:75ch}
.mb-tabs .tabs-head{flex-wrap:wrap}
.mb-tab{flex:1 1 auto;min-width:150px;justify-content:center;padding:13px 14px}
.mb-tab .tt{min-width:0}
.mb-tab .tn{font-size:13.5px;font-weight:700;color:var(--ink2);font-family:"Fraunces",Georgia,serif}
.mb-tab.on .tn{color:var(--clay-d)}
.mb-tab .tn i{color:var(--muted);font-style:normal;font-weight:400;margin:0 5px}
.mb-pool{display:inline-block;font-size:12px;font-weight:700;color:var(--ink2);background:var(--paper2);border:1px solid var(--line);border-radius:20px;padding:3px 12px;margin-bottom:16px}
.mb-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.mb-cell{border:1px solid var(--line);border-radius:12px;padding:13px 13px 15px;background:var(--panel2);display:flex;flex-direction:column;gap:10px;min-height:94px}
.mb-cell.hot{border-color:color-mix(in srgb,var(--clay) 45%,var(--line));background:var(--clay-t)}
.mb-opt{display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}
.mb-name{font-weight:700;font-size:13.5px;color:var(--ink)}
.mb-odds{font-variant-numeric:tabular-nums;color:var(--clay-d);font-weight:700;font-size:13px}
.mb-cnt{margin-left:auto;font-size:11px;font-variant-numeric:tabular-nums;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:1px 7px}
.mb-icons{display:flex;flex-wrap:wrap;gap:8px 11px;align-items:center}
.mb-ic{display:inline-flex;align-items:center;gap:5px;font-size:12px;color:var(--ink2)}
.mb-ic i{font-style:normal}
.mb-ic .bic{width:18px;height:18px;flex:none}
.mb-empty{color:var(--muted);font-size:18px;line-height:1}
@media(max-width:640px){.mb-grid{grid-template-columns:1fr}.mb-tab{min-width:0;flex:1 1 42%}}
/* 各模型猜测比分一览 · 共识视角：比分→哪些模型+几个，扎堆者居顶高亮 */
.modelscores{margin-bottom:50px}
.msc-list{display:flex;flex-direction:column;gap:9px}
.msc-row{border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:var(--panel2)}
.msc-row.lead{border-color:color-mix(in srgb,var(--clay) 55%,var(--line));background:var(--clay-t)}
.msc-head{display:flex;align-items:center;gap:13px}
.msc-sc{font-family:"Fraunces",Georgia,serif;font-size:22px;font-weight:600;color:var(--clay-d);font-variant-numeric:tabular-nums;min-width:48px;flex:none}
.msc-bar{flex:1;height:9px;border-radius:6px;background:var(--paper2);overflow:hidden;border:1px solid var(--line);min-width:54px}
.msc-bar span{display:block;height:100%;background:linear-gradient(90deg,color-mix(in srgb,var(--clay) 60%,var(--paper)),var(--clay))}
.msc-cnt{flex:none;min-width:42px;display:inline-flex;align-items:baseline;justify-content:flex-end;gap:2px;white-space:nowrap}
.msc-cnt b{font-family:"Fraunces",Georgia,serif;font-size:19px;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums}
.msc-cnt i{font-style:normal;font-size:12px;color:var(--muted)}
.msc-tag{font-size:10px;font-weight:700;color:#fff;background:var(--clay);border-radius:20px;padding:2px 8px;flex:none;white-space:nowrap}
[data-theme="dark"] .msc-tag{color:#1a140f}
.msc-mk2{font-size:11.5px;color:var(--clay-d);background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:2px 9px;flex:none;white-space:nowrap}
.msc-foot{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:9px;padding-left:61px}
.msc-chips{display:flex;flex-wrap:wrap;gap:6px}
.msc-tags{display:flex;align-items:center;gap:6px;flex:none}
.msc-chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--ink2);background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:3px 10px 3px 7px}
.msc-chip .bic{width:15px;height:15px;flex:none}
.msc-chip i{font-style:normal}
.msc-mktrow{display:flex;align-items:center;gap:12px;margin-top:11px;padding:10px 14px;border:1px dashed var(--line2);border-radius:12px;background:var(--paper2)}
.msc-mkl{font-size:12px;font-weight:700;color:var(--muted);flex:none}
.msc-scs{display:flex;flex-wrap:wrap;gap:8px}
.msc-mk{font-size:12px;background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:3px 9px;font-variant-numeric:tabular-nums;color:var(--ink2)}
.msc-mk i{font-style:normal;color:var(--muted);margin-left:6px}
@media(max-width:640px){.msc-foot{padding-left:0;flex-wrap:wrap;justify-content:flex-start}.msc-sc{min-width:42px;font-size:20px}.msc-mktrow{flex-direction:column;align-items:flex-start;gap:7px}}
/* 上期复盘（报告顶部·只摆事实；沿用赛程卡片 + 市场概率条母题） */
.retro{margin-bottom:50px}
.rt-sub{font-size:11.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:22px 0 12px}
/* 准确率榜：每模型一行，鼠尾草进度条＝方向命中率，数字走 Fraunces */
.rt-board{display:flex;flex-direction:column;gap:8px}
.rt-row{display:grid;grid-template-columns:24px minmax(118px,148px) 1fr auto;align-items:center;gap:14px;
  padding:11px 15px;border:1px solid var(--line);border-radius:12px;background:var(--panel2)}
.rt-row.lead{border-color:color-mix(in srgb,var(--clay) 48%,var(--line));background:var(--clay-t)}
.rt-rank{font-family:"Fraunces",Georgia,serif;font-size:15px;color:var(--muted);text-align:center}
.rt-row.lead .rt-rank{color:var(--clay-d)}
.rt-who{display:inline-flex;align-items:center;gap:8px;font-weight:700;font-size:13.5px;color:var(--ink);min-width:0}
.rt-who .bic{width:19px;height:19px;flex:none}
.rt-who i{font-style:normal;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rt-tag{font-size:10px;font-weight:700;color:#fff;background:var(--clay);border-radius:20px;padding:1px 7px;flex:none}
[data-theme="dark"] .rt-tag{color:#1a140f}
.rt-meter{display:flex;align-items:center;gap:11px;min-width:0}
.rt-track{flex:1;height:7px;border-radius:6px;background:var(--paper2);overflow:hidden;border:1px solid var(--line);min-width:54px}
.rt-track span{display:block;height:100%;background:linear-gradient(90deg,color-mix(in srgb,var(--sage) 78%,var(--paper)),var(--sage))}
.rt-dir{font-family:"Fraunces",Georgia,serif;font-size:16px;font-weight:600;color:var(--sage);font-variant-numeric:tabular-nums;flex:none}
.rt-dir i{font-style:normal;font-size:11px;font-family:-apple-system,sans-serif;color:var(--muted);margin-left:3px;font-weight:400}
.rt-sc{font-size:12px;color:var(--ink2);background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:3px 11px;flex:none;white-space:nowrap}
.rt-sc b{font-family:"Fraunces",Georgia,serif;font-weight:600;color:var(--clay-d);font-variant-numeric:tabular-nums}
.rt-sc.zero b{color:var(--muted)}
/* 逐场卡片：照搬今日赛程卡片骨架，中央换成终场比分（Fraunces），底部列谁押中 */
.rt-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(244px,1fr));gap:13px}
.rt-card{display:flex;flex-direction:column;gap:11px;background:var(--panel);border:1px solid var(--line);
  border-radius:14px;padding:14px 15px;box-shadow:var(--shadow-s)}
.rt-card.up{border-color:var(--upset-line);background:color-mix(in srgb,var(--upset-t) 32%,var(--panel))}
.rt-c-top{display:flex;justify-content:space-between;align-items:center}
.rt-c-stage{font-size:11px;color:var(--muted);letter-spacing:.02em}
.rt-c-res{font-size:11px;font-weight:700;color:var(--clay-d);border:1px solid color-mix(in srgb,var(--clay) 40%,var(--line));
  background:var(--clay-t);border-radius:20px;padding:2px 10px}
.rt-card.up .rt-c-res{color:var(--upset-d);background:var(--upset-t);border-color:var(--upset-line)}
.rt-c-res .up{margin-left:5px;padding-left:6px;border-left:1px solid currentColor;opacity:.85}
.rt-mid{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:8px}
.rt-team{display:flex;flex-direction:column;align-items:center;gap:6px;min-width:0;text-align:center}
.rt-team b{font-size:12.5px;font-weight:600;line-height:1.2;overflow-wrap:anywhere}
.rt-logo{width:36px;height:36px;border-radius:50%;object-fit:cover;background:var(--paper2);border:1px solid var(--line)}
.rt-logo.ph{display:inline-block}
.rt-score{font-family:"Fraunces",Georgia,serif;font-size:23px;font-weight:600;color:var(--clay-d);
  font-variant-numeric:tabular-nums;letter-spacing:.02em;line-height:1;padding:0 4px}
.rt-foot{border-top:1px solid var(--line);padding-top:10px;display:flex;flex-direction:column;gap:8px}
.rt-line{display:flex;align-items:center;gap:9px;font-size:11.5px;min-height:21px}
.rt-line .lab{color:var(--muted);flex:none;width:54px;letter-spacing:.02em}
.rt-hits{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.rt-hits .bic{width:21px;height:21px;flex:none}
.rt-hits.dir .bic{color:var(--sage);border-color:color-mix(in srgb,var(--sage) 45%,var(--line))}
.rt-schit{display:inline-flex;align-items:center;gap:6px;background:var(--panel2);border:1px solid var(--line);border-radius:20px;padding:2px 10px 2px 3px}
.rt-schit .bic{width:19px;height:19px;flex:none}
.rt-schit b{font-family:"Fraunces",Georgia,serif;font-weight:600;color:var(--clay-d);font-variant-numeric:tabular-nums;font-size:13px;letter-spacing:.01em}
.rt-none{color:var(--muted);font-style:italic}
@media(max-width:640px){.rt-row{grid-template-columns:20px 1fr;gap:8px 11px}.rt-meter{grid-column:1/3}}
/* 市场怎么看（单场内） */
.market{margin:2px 0 18px;padding:15px 17px;border:1px solid var(--line);border-radius:14px;background:var(--panel2)}
.market-h{font-size:11.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:9px}
.mkt-judge{font-size:14px;color:var(--ink2);margin-bottom:12px}
.mkt-judge b{color:var(--clay-d);font-weight:700}
.mkt-l{font-size:12px;color:var(--muted);margin-bottom:8px}
.mkt-bars{margin-bottom:13px}
.mkt-bar{display:grid;grid-template-columns:56px 1fr 46px 50px;align-items:center;gap:11px;margin-bottom:9px}
.mkt-nm{font-size:13px;color:var(--ink2);white-space:nowrap}
.mkt-track{height:8px;border-radius:6px;background:var(--paper2);overflow:hidden;border:1px solid var(--line)}
.mkt-track span{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,color-mix(in srgb,var(--clay) 70%,var(--paper)),var(--clay))}
.mkt-pct{font-variant-numeric:tabular-nums;color:var(--ink);font-weight:700;font-size:13.5px;text-align:right}
.mkt-od{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;text-align:right}
.mkt-bar.fav .mkt-track span{background:linear-gradient(90deg,var(--clay),var(--clay-d))}
.mkt-bar.fav .mkt-pct{color:var(--clay-d)}
.mkt-tops{border-top:1px solid var(--line);padding-top:11px}
.mkt-scs{display:flex;flex-wrap:wrap;gap:8px}
.mkt-sc{font-size:13px;background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:3px 10px;font-variant-numeric:tabular-nums;color:var(--ink2)}
.mkt-sc i{font-style:normal;color:var(--muted);margin-left:7px}
/* 嘉豪先疯一句 · 各模型原话 */
.fans{margin:4px 0 6px}
.fans-l{font-size:11.5px;font-weight:700;letter-spacing:.1em;color:var(--muted);margin-bottom:12px}
.fans-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.fan{border:1px solid var(--line);border-radius:14px;background:var(--panel2);padding:14px 16px}
.fan-h{display:flex;align-items:center;gap:9px;margin-bottom:11px;padding-bottom:10px;border-bottom:1px solid var(--line)}
.fan-h .bic{width:20px;height:20px;flex:none}
.fan-h .brand{font-weight:700;color:var(--ink2);font-size:14px}
.fan-h .mname{font-size:11px;color:var(--muted);margin-left:auto;font-variant-numeric:tabular-nums}
.fan-row{display:grid;grid-template-columns:78px minmax(0,1fr);gap:11px;padding:5px 0;font-size:13.5px;line-height:1.6}
.fan-k{color:var(--muted);font-size:12px;font-weight:600}
.fan-v{color:var(--ink);min-width:0}
.fan-score .fan-v{font-family:"Fraunces",Georgia,serif;font-weight:600;color:var(--clay-d);font-size:15px}
.fan-pic{align-items:start}
.fan-pic .fan-v{color:var(--ink2);font-size:12.5px;line-height:1.7}
@media(max-width:640px){.fans-grid{grid-template-columns:1fr}.fan-row{grid-template-columns:64px 1fr}}
.plans-tabs{margin-bottom:50px}
.tabs{--pa:var(--clay);--pa-d:var(--clay-d);--pa-t:var(--clay-t);background:var(--panel);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);overflow:hidden}
.tabs-head{display:flex;background:var(--panel2);border-bottom:1px solid var(--line)}
.tab{flex:1;min-width:0;font:inherit;cursor:pointer;background:none;border:none;border-bottom:2.5px solid transparent;padding:15px 18px;display:flex;align-items:center;gap:11px;color:var(--muted);text-align:left;transition:background .18s,border-color .18s}
.tab:not(:last-child){border-right:1px solid var(--line)}
.tab .tb{width:30px;height:30px;border-radius:9px;background:color-mix(in srgb,var(--pa) 16%,var(--panel));color:var(--pa);display:inline-flex;align-items:center;justify-content:center;flex:none;font-family:"Fraunces",Georgia,serif;font-size:14px;font-weight:600;font-variant-numeric:tabular-nums;transition:.18s}
.tab .tt{min-width:0;line-height:1.3}
.tab .tn{font-size:14.5px;font-weight:700;color:var(--ink2);font-family:"Fraunces",Georgia,serif}
.tab .td{font-size:11px;color:var(--muted);margin-left:6px}
.tab:hover{background:color-mix(in srgb,var(--pa) 7%,var(--panel2))}
.tab.on{background:var(--panel);border-bottom-color:var(--pa)}
.tab.on .tb{background:var(--pa);color:#fff}
[data-theme="dark"] .tab.on .tb{color:#1a140f}
.tab.on .tn{color:var(--pa-d)}
.tab.calm{--pa:var(--sage);--pa-d:var(--sage);--pa-t:color-mix(in srgb,var(--sage) 14%,var(--panel))}
.tab.mid{--pa:var(--gold);--pa-d:var(--gold);--pa-t:color-mix(in srgb,var(--gold) 15%,var(--panel))}
.tab.bold{--pa:var(--clay);--pa-d:var(--clay-d);--pa-t:var(--clay-t)}
.tab-panel{--pa:var(--clay);--pa-d:var(--clay-d);--pa-t:var(--clay-t);padding:26px 28px;display:none}
.tab-panel.on{display:block}
@media(prefers-reduced-motion:no-preference){.tab-panel.on{animation:tfade .3s ease}}
@keyframes tfade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.tab-panel.calm{--pa:var(--sage);--pa-d:var(--sage);--pa-t:color-mix(in srgb,var(--sage) 14%,var(--panel))}
.tab-panel.mid{--pa:var(--gold);--pa-d:var(--gold);--pa-t:color-mix(in srgb,var(--gold) 15%,var(--panel))}
.tab-panel.bold{--pa:var(--clay);--pa-d:var(--clay-d);--pa-t:var(--clay-t)}
.tp-tier{display:none}
.tp-title{font-size:21px;line-height:1.28;margin-bottom:7px;color:var(--ink);text-wrap:balance}
.tp-sub{font-size:13px;color:var(--ink2);margin:0 0 20px;line-height:1.55;max-width:72ch}
.tp-gh{grid-column:1/-1;display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;color:var(--pa-d);margin:12px 0 -2px;letter-spacing:.02em}
.tp-gh:first-child{margin-top:0}
.tp-gh:before{content:"";width:14px;height:2px;border-radius:2px;background:var(--pa);flex:none}
.combo{color:var(--pa-d);background:var(--pa-t);border:1px solid color-mix(in srgb,var(--pa) 26%,transparent);padding:2px 10px;border-radius:20px;font-size:11.5px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:0}
/* 玩法行：玩法独占首行，赔率右对齐；比赛名+信心降到次行。tp-legs 按内容自动铺成多列 */
.tp-legs{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px 26px;align-items:start}
.leg{display:flex;flex-direction:column;gap:3px}
.leg-top{display:flex;align-items:baseline;gap:10px}
.leg-p{font-weight:600;font-size:14px;line-height:1.42;flex:1;min-width:0}
.leg-o{flex:none;font-variant-numeric:tabular-nums;color:var(--pa-d);font-weight:700;font-size:14px}
.leg-meta{display:flex;align-items:center;gap:10px;font-size:11.5px;color:var(--muted)}
.leg-m{min-width:0}
.leg-conf{margin-left:auto;display:inline-flex;align-items:center;flex:none}
.leg-r{font-size:12px;color:var(--muted);line-height:1.55;margin-top:1px}
.dots{color:var(--pa);font-size:10px;letter-spacing:2px}.dots-o{color:var(--line2)}
.tp-note{font-size:12.5px;color:var(--muted);border-top:1px dashed var(--line2);padding-top:14px;margin-top:22px;line-height:1.55}
.tp-pnote{grid-column:1/-1;margin-top:-4px}
/* 今日赛程总览 */
.schedule{margin-bottom:30px}
.sch-h{display:flex;align-items:baseline;gap:12px;margin-bottom:14px;flex-wrap:wrap}
.sch-h h2{font-family:"Fraunces",Georgia,serif;font-size:20px;font-weight:600}
.sch-sub{font-size:12px;color:var(--muted)}
.sch-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(244px,1fr));gap:13px}
.sch-card{display:flex;flex-direction:column;gap:11px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 15px;text-decoration:none;color:inherit;box-shadow:var(--shadow-s);transition:transform .16s,border-color .16s,box-shadow .16s}
.sch-card:hover{transform:translateY(-2px);border-color:var(--clay);box-shadow:var(--shadow)}
.sch-top{display:flex;justify-content:space-between;align-items:center}
.sch-stage{font-size:11px;color:var(--clay-d);font-weight:600;letter-spacing:.02em}
.sch-status{font-size:10.5px;color:var(--muted);border:1px solid var(--line2);border-radius:20px;padding:2px 9px}
.sch-mid{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:8px}
.sch-team{display:flex;flex-direction:column;align-items:center;gap:6px;min-width:0;text-align:center}
.sch-team b{font-size:13px;font-weight:600;line-height:1.2;overflow-wrap:anywhere}
.sch-logo{width:38px;height:38px;border-radius:50%;object-fit:cover;background:var(--paper2);border:1px solid var(--line)}
.sch-logo.ph{display:inline-block}
.sch-ko{font-family:"Fraunces",Georgia,serif;font-size:18px;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums}
.sch-foot{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:11px;color:var(--muted);border-top:1px solid var(--line);padding-top:9px}
.sch-rank{font-variant-numeric:tabular-nums;color:var(--ink2);background:var(--paper2);border:1px solid var(--line);border-radius:20px;padding:1px 8px}
/* match */
.m-logo{width:26px;height:26px;border-radius:50%;object-fit:cover;vertical-align:-6px;background:var(--paper2);border:1px solid var(--line);margin-right:7px}
.m-logo.ph{display:inline-block}
.match{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:28px;margin-bottom:22px;box-shadow:var(--shadow);scroll-margin-top:22px}
.m-top{display:flex;align-items:center;gap:13px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:18px}
.m-id{font-size:11.5px;color:var(--panel);background:var(--ink);padding:4px 10px;border-radius:7px;letter-spacing:.04em;font-weight:600}
.m-top h2{font-size:25px;flex:1;min-width:200px}
.vs{color:var(--muted);font-size:15px;font-style:italic;margin:0 4px}
.m-meta{display:flex;gap:10px;align-items:center;font-size:12.5px;color:var(--muted)}
.rankcmp{display:flex;align-items:center;gap:12px;margin:-4px 0 16px;font-variant-numeric:tabular-nums}
.rankcmp .rk{display:inline-flex;align-items:baseline;gap:6px;padding:4px 13px;border-radius:9px;background:var(--paper2);border:1px solid var(--line);color:var(--muted)}
.rankcmp .rk i{font-style:normal;font-size:10px;letter-spacing:.08em;text-transform:uppercase}
.rankcmp .rk b{font-size:18px;color:var(--ink2);font-family:"Fraunces",Georgia,serif;line-height:1}
.rankcmp .rk.strong{background:var(--clay-t);border-color:var(--clay);color:var(--clay-d)}
.rankcmp .rk.strong b{color:var(--clay-d)}
.rankcmp .rk-gap{flex:1;text-align:center;font-size:11.5px;letter-spacing:.04em;color:var(--muted);position:relative}
.rankcmp .rk-gap:before,.rankcmp .rk-gap:after{content:"";position:absolute;top:50%;width:16%;height:1px;background:var(--line2)}
.rankcmp .rk-gap:before{left:7%}.rankcmp .rk-gap:after{right:7%}
.headline{font-family:"Fraunces",Georgia,serif;font-size:19px;line-height:1.45;margin-bottom:8px;color:var(--ink)}
.consensus{font-size:13.5px;color:var(--ink2);margin-bottom:18px;line-height:1.65;max-width:75ch}
.ml-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.ml-cap{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink2);font-weight:700;margin-right:2px}
.ml-l{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:600}
.ml-l2{margin-left:8px;padding-left:10px;border-left:1px solid var(--line2)}
.ml{font-family:"Fraunces",Georgia,serif;font-size:15px;background:var(--clay-t);color:var(--clay-d);padding:3px 12px;border-radius:7px;font-weight:600}
.ml.mkt{background:var(--paper2);border:1px solid var(--line);color:var(--ink2);font-weight:600}
.ml.mkt i{font-style:normal;font-size:11px;color:var(--muted);margin-left:6px;font-family:system-ui,-apple-system,sans-serif;font-weight:500}
/* value points */
.vps{display:flex;flex-direction:column;gap:9px;margin-bottom:18px}
.vps-l{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--clay-d);font-weight:700}
.vp{border:1px solid var(--val-line);background:var(--val-bg);border-radius:11px;padding:12px 15px;position:relative}
.vp-h{display:flex;align-items:center;gap:9px;flex-wrap:wrap;font-weight:600;font-size:14px}
.vp-play:before{content:"◆";color:var(--clay);font-size:10px;margin-right:6px;vertical-align:1px}
.vp-odds{color:var(--clay-d);font-variant-numeric:tabular-nums;font-weight:700}
.vp-mk{font-size:11.5px;color:var(--muted);font-weight:500;margin-left:auto}
.vp-why{font-size:12.5px;color:var(--ink2);margin-top:5px;line-height:1.55}
/* trap points（陷阱/避雷）：琥珀警示，与价值点的陶土橘形成"机会 vs 风险"对照 */
.traps{display:flex;flex-direction:column;gap:9px;margin-bottom:18px}
.traps-l{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--gold);font-weight:700}
.tp{border:1px solid var(--warn-line);background:var(--warn-bg);border-radius:11px;padding:12px 15px}
.tp-play{font-weight:600;font-size:14px}
.tp-play:before{content:"▲";color:var(--gold);font-size:9px;margin-right:6px;vertical-align:1px}
.tp-odds{color:var(--gold);font-variant-numeric:tabular-nums;font-weight:700}
/* 防一手 · 平局风险（draw_guard）：高=红、中=琥珀 */
.dg{display:flex;flex-direction:column;gap:8px;margin-bottom:18px;border-radius:12px;padding:13px 16px;border:1px solid}
.dg-mid{background:var(--warn-bg);border-color:var(--warn-line)}
.dg-high{background:var(--danger-bg);border-color:var(--danger-line)}
.dg-h{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap}
.dg-t{font-size:13px;font-weight:700;letter-spacing:.02em}
.dg-t:before{content:"⚠ ";font-size:12px}
.dg-mid .dg-t{color:var(--gold)}
.dg-high .dg-t{color:var(--danger)}
.dg-prob{font-size:12px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--ink2)}
.dg-sigs{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:4px}
.dg-sigs li{font-size:12.5px;color:var(--ink2);line-height:1.5}
.dg-hedge{font-size:12.5px;color:var(--ink);line-height:1.55;padding-top:8px;border-top:1px solid color-mix(in srgb,var(--ink) 10%,transparent)}
.dg-hl{display:inline-block;font-size:11px;font-weight:700;color:#fff;border-radius:5px;padding:1px 7px;margin-right:7px;vertical-align:1px}
.dg-mid .dg-hl{background:var(--gold)}
.dg-high .dg-hl{background:var(--danger)}
/* 本届走势 · 真实战况（联网搜到的实际表现，不只比分）：中性纸感 + 墨色左轴，区别于价值/陷阱/防平的彩色块 */
.forms{display:flex;flex-direction:column;gap:8px;margin-bottom:18px}
.forms-l{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink2);font-weight:700}
.fm{border:1px solid var(--line2);background:var(--paper2);border-radius:11px;padding:11px 14px}
.fm-top{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;margin-bottom:3px}
.fm-team{font-weight:700;font-size:13.5px;color:var(--ink)}
.fm-last{font-size:12px;font-variant-numeric:tabular-nums;color:var(--ink2);font-family:"Fraunces",Georgia,serif}
.fm-src{font-size:10.5px;color:var(--muted);margin-left:auto;border:1px solid var(--line);border-radius:20px;padding:1px 8px}
.fm-read{font-size:12.5px;color:var(--ink2);line-height:1.55}
/* 最有可能的爆冷（博冷雷达）：三档下方独立高亮块；酒红/梅子强调色——区别于三档(绿/金/陶土)与红色危险，反共识押冷的调性 */
.upset{--pa:var(--upset);background:var(--panel);border:1px solid var(--upset-line);border-radius:var(--r);box-shadow:var(--shadow);margin:0 0 50px;padding:23px 26px 21px}
.up-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:4px}
.up-k{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--upset-d);background:var(--upset-t);padding:3px 10px;border-radius:7px;font-weight:700;flex:none}
.up-title{font-family:"Fraunces",Georgia,serif;font-size:20px;font-weight:600;color:var(--ink)}
.up-base{font-size:12.5px;color:var(--ink2);line-height:1.6;margin:9px 0 16px;max-width:78ch}
.up-picks{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.up-pick{border:1px solid var(--upset-line);border-radius:12px;padding:15px 17px;background:var(--upset-t)}
.up-alt{background:var(--panel2);border-color:var(--line2)}
.up-pk-top{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:10px}
.up-rank{font-size:10.5px;font-weight:700;letter-spacing:.04em;color:#fff;background:var(--upset);padding:2px 9px;border-radius:6px;flex:none}
[data-theme="dark"] .up-rank{color:#1c1216}
.up-alt .up-rank{background:var(--muted)}
.up-match{font-size:12px;color:var(--ink2);font-weight:600}
.up-type{font-size:10.5px;color:var(--upset-d);border:1px solid var(--upset-line);border-radius:20px;padding:1px 9px;font-weight:600}
.up-alt .up-type{color:var(--muted);border-color:var(--line2)}
.up-conf{margin-left:auto}
.up-play-row{display:flex;align-items:baseline;gap:11px;flex-wrap:wrap;margin-bottom:8px}
.up-play{font-family:"Fraunces",Georgia,serif;font-size:18px;font-weight:600;color:var(--ink);line-height:1.25}
.up-odds{font-variant-numeric:tabular-nums;font-weight:700;font-size:16px;color:var(--upset-d)}
.up-alt .up-odds{color:var(--ink2)}
.up-why{font-size:12.5px;color:var(--ink2);line-height:1.55}
.up-basis{font-size:11.5px;color:var(--muted);margin-top:9px;padding-top:9px;border-top:1px dashed var(--line2);line-height:1.5}
.up-bl{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--upset-d);margin-right:7px}
.up-alt .up-bl{color:var(--muted)}
.up-note{font-size:12.5px;color:var(--ink2);line-height:1.6;margin-top:15px}
.up-disc{font-size:11.5px;color:var(--muted);margin-top:13px;border-top:1px dashed var(--line2);padding-top:11px;line-height:1.5}
@media(max-width:680px){.up-picks{grid-template-columns:1fr}}
/* key market */
.key-mkt{margin-bottom:14px}
.key-mkt .mkt{border-color:var(--line2);box-shadow:var(--shadow-s)}
.key-mkt .mkt-h{background:var(--panel2)}
/* fold (details) */
.fold{border:1px solid var(--line);border-radius:12px;margin-bottom:12px;overflow:hidden;background:var(--panel2)}
.fold>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:10px;padding:13px 16px;user-select:none;transition:.16s}
.fold>summary::-webkit-details-marker{display:none}
.fold>summary:before{content:"";width:8px;height:8px;border-right:1.6px solid var(--clay);border-bottom:1.6px solid var(--clay);transform:rotate(-45deg);transition:transform .2s;flex:none;margin:0 2px}
.fold[open]>summary:before{transform:rotate(45deg)}
.fold>summary:hover{background:var(--paper2)}
.fold-t{font-size:13px;font-weight:600;color:var(--clay-d)}
.fold-s{font-size:11.5px;color:var(--muted);margin-left:auto}
.fold .markets,.fold .disc-body{padding:4px 16px 16px}
.disc-body{padding-top:8px}
/* markets */
.markets{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:6px}
.mkt{border:1px solid var(--line);border-radius:11px;overflow:hidden;background:var(--panel)}
.mkt.wide{grid-column:1/-1;background:var(--panel2)}
.mkt-h{display:flex;justify-content:space-between;align-items:center;background:var(--paper2);padding:9px 14px;font-size:13px;border-bottom:1px solid var(--line)}
.mkt-t{font-weight:600}
.single{font-size:10.5px;font-weight:600;padding:3px 8px;border-radius:20px}
.single.yes{background:color-mix(in srgb,var(--sage) 18%,transparent);color:var(--sage)}
.single.no{background:var(--paper2);color:var(--muted);border:1px solid var(--line)}
.mkt table{width:100%;border-collapse:collapse}
.mkt th{font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);padding:7px 14px;text-align:left;font-weight:600}
.mkt th.num{text-align:right}
.mkt td{padding:7px 14px;font-size:13px;border-top:1px solid var(--line)}
td.lab{font-weight:500}td.soft{color:var(--muted)}
td.od{font-weight:600;color:var(--ink)}
tr.val td{background:var(--val-bg)}tr.val .od{color:var(--clay-d)}
.probc{display:inline-flex;align-items:center;gap:8px;justify-content:flex-end}
.pbar{width:62px;height:7px;border-radius:4px;background:var(--line);overflow:hidden;flex:none}
.pbar i{display:block;height:100%;background:var(--muted);border-radius:4px}
tr.val .pbar i{background:linear-gradient(90deg,var(--clay),var(--clay-d))}
.pn{min-width:30px;text-align:right}
.vmark{font-size:9.5px;color:#fff;background:var(--clay);padding:2px 5px;border-radius:4px;margin-left:6px;vertical-align:1px;font-weight:600}
[data-theme="dark"] .vmark{color:#1a140f}
.top-chips{padding:12px 14px;font-size:12px;color:var(--ink2);display:flex;gap:7px;flex-wrap:wrap;align-items:center}
.tc-l{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600}
.chip{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:4px 11px;font-variant-numeric:tabular-nums}
.chip b{color:var(--clay-d)}.chip i{color:var(--muted);font-style:normal;font-size:11px}
.mkt details{border-top:1px solid var(--line)}
.mkt summary{cursor:pointer;padding:9px 14px;font-size:12px;color:var(--clay-d);font-weight:600;user-select:none}
.sc-full{padding:7px 14px 14px}
.sc-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:7px}
.sc-side{font-size:11px;color:var(--muted);min-width:42px;font-weight:600}
.sc{font-size:12px;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:3px 8px;font-variant-numeric:tabular-nums}
.sc b{color:var(--clay-d);margin-left:4px}.sc.val{background:var(--val-bg);border-color:var(--clay)}
.no-odds{color:var(--gold);font-size:13px;padding:15px;background:var(--clay-t);border-radius:11px}
/* views */
/* 列数随选中 agent 数自适应：1家→整列、2家→两列、3+→自动换行（避免半宽留白或挤压） */
.views{display:grid;grid-template-columns:repeat(auto-fit,minmax(258px,1fr));gap:14px;margin-bottom:14px}
.view{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:16px 17px}
.view-h{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.brand{font-weight:700;font-size:15px}
.mname{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums;margin-left:auto}
.stance{font-size:13px;font-weight:600;color:var(--clay-d);margin-bottom:9px;line-height:1.45}
.view ul{list-style:none;display:flex;flex-direction:column;gap:6px}
.view li{font-size:12.5px;color:var(--ink2);padding-left:15px;position:relative;line-height:1.5}
.view li:before{content:"";position:absolute;left:2px;top:8px;width:5px;height:5px;border-radius:50%;background:var(--clay)}
/* 自我反驳/风险子句（"最易打脸…"）：琥珀⚠ + 弱化文字，让"我可能错在哪"一眼可见 */
.view li .risk-tag{color:var(--muted)}
.view li .risk-tag:before{content:"⚠ ";color:var(--gold);font-size:9.5px;font-weight:600}
.view li.solo-risk:before{display:none}
.foot{display:flex;align-items:flex-start;gap:8px;flex-wrap:wrap}
.foot-l{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:600;padding-top:6px}
.foot-chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--ink2);background:var(--panel);border:1px solid var(--line);padding:5px 11px 5px 6px;border-radius:20px;max-width:100%}
.foot-chip b{color:var(--ink)}.foot-chip i{color:var(--muted)}
/* footer */
footer{margin-top:42px;padding-top:24px;border-top:1px solid var(--line2);color:var(--muted);font-size:12px;line-height:1.7}
.disc{background:var(--clay-t);border:1px solid var(--val-line);border-radius:12px;padding:15px 17px;color:var(--clay-d);margin-bottom:15px;font-size:12.5px;line-height:1.6}
/* reveal */
@media(prefers-reduced-motion:no-preference){
 .reveal{opacity:0;transform:translateY(12px);animation:rise .65s cubic-bezier(.2,.7,.2,1) forwards}
 @keyframes rise{to{opacity:1;transform:none}}
}
@media(max-width:760px){
 .wrap{padding:0 18px}.tab{padding:12px 11px;gap:8px}.tab .td{display:none}.tab-panel{padding:20px 18px}.tp-legs{grid-template-columns:1fr}.views{grid-template-columns:1fr}
 .markets{grid-template-columns:1fr}.hero{padding:38px 0 24px}.match{padding:20px}
 .m-top h2{font-size:22px}.vp-mk{margin-left:0}
}
/* print → PDF */
@media print{
 @page{size:A4;margin:13mm}
 :root,[data-theme="dark"]{
  --paper:#fff;--paper2:#f4efe4;--panel:#fff;--panel2:#faf7f0;
  --ink:#1a1813;--ink2:#534b3d;--muted:#7c7260;
  --line:#e2dac8;--line2:#cfc5af;--clay:#b1542f;--clay-d:#964127;--clay-t:#f4e6da;
  --sage:#566448;--gold:#8c7027;--val-bg:#f6e8db;--val-line:#dcb190;--brand-mono:#26221a;
  --warn-bg:#f6eed4;--warn-line:#d8c184;
  --shadow:none;--shadow-s:none}
 body{background:#fff;padding:0}
 .bg,.sidebar,.toc-toggle,.toc-scrim,.no-print{display:none!important}
 body{padding-left:0!important}
 .hero{padding:0 0 14px}.wrap{max-width:none;padding:0}
 .tabs,.match{box-shadow:none;border-color:#d9cfba}
 .match,.view,.mkt,.vp,.tr,tr{break-inside:avoid}
 .fold>summary,.mkt summary{display:none!important}
 .tabs{border:none}
 .tabs-head{display:none!important}
 .tab-panel{display:block!important;break-inside:avoid;padding:14px 2px;border-top:1px solid #e2dac8}
 .tab-panel:first-of-type{border-top:none}
 .tp-tier{display:flex!important;align-items:center;gap:8px;margin-bottom:8px;font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:13.5px;color:#964127}
 .tp-tier .tb{width:24px;height:24px;border-radius:7px;background:#b1542f;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:12px;flex:none}
 .fold{background:#fff;border-color:#e2dac8}
 .reveal{opacity:1!important;transform:none!important;animation:none!important}
 a[href^="#"]{text-decoration:none}
 .match{margin-bottom:14px}
}
"""

INIT_JS = ('(function(){try{var t=localStorage.getItem("wc-theme");'
           'if(!t)t=(window.matchMedia&&matchMedia("(prefers-color-scheme:dark)").matches)?"dark":"light";'
           'document.documentElement.setAttribute("data-theme",t);'
           'if(localStorage.getItem("wc-toc")==="collapsed")document.documentElement.classList.add("toc-collapsed")}'
           'catch(e){document.documentElement.setAttribute("data-theme","light")}})();')

MAIN_JS = """
(function(){
 var root=document.documentElement,tb=document.getElementById('themeBtn');
 function lbl(){var d=root.getAttribute('data-theme')==='dark',t=tb&&tb.querySelector('.tlabel');if(t)t.textContent=d?'浅色':'深色';}
 lbl();
 if(tb)tb.addEventListener('click',function(){var d=root.getAttribute('data-theme')==='dark',n=d?'light':'dark';
  root.setAttribute('data-theme',n);try{localStorage.setItem('wc-theme',n)}catch(e){}lbl();});
 // Tabs：每个 .tabs 容器内部独立切换（三档方案、各模型下注各一组，互不串台；PDF 导出时由 @media print 全展开）
 [].slice.call(document.querySelectorAll('.tabs')).forEach(function(group){
  var tabs=[].slice.call(group.querySelectorAll('.tab'));
  var panels=[].slice.call(group.querySelectorAll('.tab-panel'));
  tabs.forEach(function(t){t.addEventListener('click',function(){
   var i=t.getAttribute('data-i');
   tabs.forEach(function(x){x.classList.remove('on');});
   panels.forEach(function(x){x.classList.remove('on');});
   t.classList.add('on');
   var p=group.querySelector('.tab-panel[data-i="'+i+'"]');if(p)p.classList.add('on');});});
 });
 var pf=document.getElementById('pdfBtn'),op=[];
 function ex(){op=[];document.querySelectorAll('details').forEach(function(d){if(!d.open){op.push(d);d.open=true;}});}
 function rs(){op.forEach(function(d){d.open=false;});op=[];}
 if(pf)pf.addEventListener('click',function(){ex();setTimeout(function(){window.print();},80);});
 window.addEventListener('beforeprint',ex);window.addEventListener('afterprint',rs);
 var links=[].slice.call(document.querySelectorAll('.nav-jump a')),map={},targets=[];
 links.forEach(function(a){var id=a.getAttribute('href').slice(1);map[id]=a;var el=document.getElementById(id);if(el)targets.push(el);});
 if('IntersectionObserver' in window){
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){
   links.forEach(function(a){a.classList.remove('on');});var a=map[e.target.id];if(a){a.classList.add('on');
   var nv=a.parentNode;nv.scrollTop=Math.max(0,a.offsetTop-nv.offsetTop-nv.clientHeight/2+a.clientHeight/2);}}});},{rootMargin:'-45% 0px -50% 0px',threshold:0});
  targets.forEach(function(s){io.observe(s);});
 }
 // 目录开合：宽屏=折叠/展开（记忆到 localStorage），窄屏=抽屉（遮罩/点链接收起）
 var htmlEl=document.documentElement;
 var col=document.getElementById('tocCollapse'),tg=document.getElementById('tocToggle'),sc=document.getElementById('tocScrim');
 function desktop(){return matchMedia('(min-width:1101px)').matches;}
 function setOpen(o){htmlEl.classList.toggle('toc-open',o);}
 function setCol(c){htmlEl.classList.toggle('toc-collapsed',c);try{localStorage.setItem('wc-toc',c?'collapsed':'open');}catch(e){}}
 if(col)col.addEventListener('click',function(){desktop()?setCol(true):setOpen(false);});
 if(tg)tg.addEventListener('click',function(){desktop()?setCol(false):setOpen(true);});
 if(sc)sc.addEventListener('click',function(){setOpen(false);});
 links.forEach(function(a){a.addEventListener('click',function(){if(!desktop())setOpen(false);});});
})();
"""


def build(merged, analysis, out, retro=None, date_arg=None):
    meta = analysis.get("meta", {}) if analysis else {}
    order = sorted(merged.values(), key=lambda m: m.get("kickoff_at") or "")
    # 纯汇总：每场只渲染市场赔率 + 各模型嘉豪先疯一句原文，无价值标注
    sections = "".join(render_match(i, m, None, set()) for i, m in enumerate(order, 1))

    # 日期：优先 --date / meta.date，否则从最早开赛时间推北京日期（不再依赖 analysis）
    date = date_arg or meta.get("date") or (fmt_kickoff(order[0].get("kickoff_at"), "%Y-%m-%d") if order else "")
    # 采纳模型：取实际出现且有嘉豪先疯一句的品牌（不再靠人工 selected_agents）
    seen, brands = set(), []
    for m in order:
        for mod in m.get("models", []):
            b = mod.get("brand")
            if b and b not in seen and extract_fan_block(mod.get("discussion_md")):
                seen.add(b)
                brands.append(b)
    agent_tags = "".join(f'<span class="atag">{brand_icon(b)}{esc(b)}</span>' for b in brands) or "—"
    disclaimer = (analysis.get("disclaimer") if analysis else None) or \
        "本报告只做汇总呈现：原样搬运各模型在嘉豪平台的公开预测，叠加竞彩实时倍率，不含本站的任何分析、判断或投注建议。博彩有风险，请理性娱乐、量力而行，未满法定年龄者请勿参与。"
    # 先渲染各大块；目录只列"实际渲染出来"的块，避免锚点对不上
    retro_html = render_retro(retro)
    sched_html = render_schedule(order)
    mbets_html = render_model_bets(order)
    mscores_html = render_model_scores(order)
    nav_sections = []
    for present, sid, label in (
        (retro_html, "retro", "上期复盘"),
        (sched_html, "sched", "今日赛程"),
        (mbets_html, "modelbets", "各模型下注"),
        (mscores_html, "modelscores", "各模型比分"),
    ):
        if present:
            nav_sections.append((sid, label))

    doc = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>嘉豪世界杯预测汇总 · {esc(date)}</title>
<script>{INIT_JS}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<div class="bg"></div>
<header class="hero"><div class="wrap">
  <div class="kicker">World Cup 2026 · 嘉豪预测汇总</div>
  <h1>{esc(date)} 各模型下注与猜测比分</h1>
  <p class="sub">原样汇总各模型在嘉豪平台的下注与「最可能比分」，附每场的实时倍率与市场去水概率——只做呈现，不含本站判断。</p>
  <div class="meta-row">
    <span class="mk-l">覆盖模型 <span class="agent-tags">{agent_tags}</span></span>
    <span class="mk-l">覆盖比赛 <b>{len(order)} 场</b></span>
    <span class="mk-l">生成时间 <b>{esc(meta.get("generated_at",""))}</b></span>
  </div>
</div></header>
{render_nav(order, nav_sections)}
<main class="wrap">
  {retro_html}
  {sched_html}
  {mbets_html}
  {mscores_html}
  {sections}
  <footer>
    <div class="disc">{esc(disclaimer)}</div>
    数据来源：worldcup.lyihub.com（模型预测）· 竞彩实时倍率。"去水概率"＝把赔率换算成概率、再扣掉庄家抽水后的结果，代表市场对这个选项实际大概多大可能发生的判断，仅供参考。
  </footer>
</main>
<script>{MAIN_JS}</script>
</body></html>'''
    Path(out).write_text(doc, encoding="utf-8")
    print(f"[report] {len(order)} 场 -> {out}")


def main():
    ap = argparse.ArgumentParser(description="渲染世界杯玩法分析 HTML 报告")
    ap.add_argument("--merged", required=True)
    ap.add_argument("--date", help="报告日期 YYYY-MM-DD（推荐传；缺则从最早开赛时间推北京日期）")
    ap.add_argument("--analysis", help="（已弃用）旧版判断 JSON；现仅可能取 meta.date，纯汇总模式无需传")
    ap.add_argument("--retro", help="上期复盘 JSON（build_retro.py 产物）；传入则在报告顶部渲染'上期复盘'模块")
    ap.add_argument("--out", default="report.html")
    args = ap.parse_args()
    merged = json.loads(Path(args.merged).read_text(encoding="utf-8"))
    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8")) if args.analysis else None
    retro = json.loads(Path(args.retro).read_text(encoding="utf-8")) if args.retro else None
    build(merged, analysis, args.out, retro, date_arg=args.date)


if __name__ == "__main__":
    main()
