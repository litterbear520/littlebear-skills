#!/usr/bin/env python3
"""比分归一：把各模型『最可能比分』原话，归一成「主队-客队」朝向的纯比分。

朝向判读是 agent 的活（队名顺序 / 无队名靠看好谁 / 多比分 / 平局都要懂上下文），
脚本只管两头的确定性 IO：

  extract  从 merged.json 抽出每场 team_a/team_b + 各模型 favor/direction/score_line，
           汇成紧凑 JSON 交给 agent（不带冗长 discussion_md，省 token）。
  apply    把 agent 判读好的 {match_id:{brand:"2-1" 或 "2-1 / 2-0" 或 null}} 写回
           merged.json 的 models[].pred_score_norm，供 build_report 渲染。

用法：
  python scripts/normalize_scores.py extract --merged "$WS/merged.json" --out "$WS/norm_in.json"
  # agent 读 norm_in.json，逐条把比分归一到主队-客队，写出 norm_out.json
  python scripts/normalize_scores.py apply --merged "$WS/merged.json" --norm "$WS/norm_out.json"
"""
import argparse
import json
import re
from pathlib import Path

# 四点标签可能各占一行，也可能内联挤在同一行（DeepSeek 偶发）。按标签出现位置切片、
# 不依赖换行——否则行首正则会把同行后面的标签连同比分一起吞进"我更看好"，导致比分抽不到。
_FAN_FINDER = re.compile(r'(我更看好|常规时间方向|最可能比分|我敢押[^：:\n]{0,12})\s*[：:]')


def parse_fan_block(md):
    """把『嘉豪先疯一句』段切成 {标签: 原文值}，兼容标签分行或内联同一行两种排版。"""
    if not md:
        return {}
    mt = re.search(r'##\s*嘉豪先疯一句\s*(.*?)(?:\n\s*---|\n\s*##|\Z)', md, re.S)
    if not mt:
        return {}
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
    return out


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def cmd_extract(args):
    merged = load(args.merged)
    order = sorted(merged.values(), key=lambda m: m.get("kickoff_at") or "")
    out = []
    for m in order:
        models = []
        for mm in m.get("models", []):
            fb = parse_fan_block(mm.get("discussion_md"))
            sl = fb.get("最可能比分", "")
            if not sl:
                continue
            models.append({
                "brand": mm.get("brand"),
                "favor": fb.get("我更看好", ""),
                "direction": fb.get("常规时间方向", ""),
                "score_line": sl,
            })
        if models:
            out.append({
                "match_id": m["match_id"],
                "team_a": m["team_a"],
                "team_b": m["team_b"],
                "models": models,
            })
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(x["models"]) for x in out)
    print(f"[normalize] extract {len(out)} 场 / {n} 条待归一 -> {args.out}")
    print("[normalize] 接下来 agent 读它，按『主队-客队』把每条比分归一，写出 norm_out.json，再跑 apply")


# 归一结果格式："2-1" 或 "2-1 / 1-1"（多比分用 " / " 连接）
_NORM_FMT = re.compile(r'^\d+-\d+(?:\s*/\s*\d+-\d+)*$')
# 原话里的比分对："2-1"、"2:0"、"2比1" 都认
_SCORE_PAIR = re.compile(r'(\d+)\s*[-:：比]\s*(\d+)')


def check_norm(merged, norm):
    """归一自洽校验。errors 挡写入（格式非法 / 数字与原话对不上——正文可能已刷新）；
    warns 只提醒（朝向与 favor 疑似矛盾、漏归一、brand/match_id 对不上）。
    只校验确定性事实，朝向本身仍是 agent 的判断、不代判。"""
    errors, warns = [], []
    for mid, mp in norm.items():
        m = merged.get(mid)
        if m is None:
            warns.append(f"match_id {mid} 在 merged 里不存在（写错了？）该场 {len(mp)} 条不会生效")
            continue
        byb = {mm.get("brand"): mm for mm in m.get("models", [])}
        label = f'{m["team_a"]} vs {m["team_b"]}'
        for brand, val in mp.items():
            if val is None:
                continue
            mm = byb.get(brand)
            if mm is None:
                warns.append(f"{label} · {brand}: merged 里没有这个模型（brand 拼写？）该条不会生效")
                continue
            v = str(val).strip()
            if not _NORM_FMT.match(v):
                errors.append(f'{label} · {brand}: 格式非法 "{v}"（应为 "2-1" 或 "2-1 / 1-1"）')
                continue
            norm_items = [(s, tuple(sorted(int(x) for x in s.split("-"))))
                          for s in re.split(r'\s*/\s*', v)]
            fb = parse_fan_block(mm.get("discussion_md"))
            sl = " ".join(fb.get("最可能比分", "").split())  # 折叠换行，便于嵌进消息
            src_pairs = [tuple(sorted((int(a), int(b)))) for a, b in _SCORE_PAIR.findall(sl)]
            if src_pairs:
                for s, np_ in norm_items:
                    if np_ not in src_pairs:
                        errors.append(
                            f'{label} · {brand}: 归一 "{v}" 里的 {s} 在原话「{sl}」找不到对应数字'
                            f'——正文可能已被站点刷新，先跑 fetch_predictions.py verify 再重归一')
                # 漏归一数目只看常规时间部分：淘汰赛原话常带"加时 2-1/点球"比分，按规则本就不归一
                reg = re.split(r'加时|点球', sl)[0]
                reg_pairs = {tuple(sorted((int(a), int(b)))) for a, b in _SCORE_PAIR.findall(reg)}
                if len(norm_items) < len(reg_pairs):
                    warns.append(f'{label} · {brand}: 原话「{sl}」常规时间给了 {len(reg_pairs)} 个比分、归一只有 {len(norm_items)} 个（漏了？）')
            # 朝向自洽：favor/direction 明确点了某队、归一却全是对方赢 → 疑似判反（平局不算矛盾）
            favor = f'{fb.get("我更看好", "")} {fb.get("常规时间方向", "")}'
            ta, tb = m["team_a"], m["team_b"]
            hit_a, hit_b = ta and ta in favor, tb and tb in favor
            if hit_a != hit_b:  # 恰好点名一队才可判
                decisive = [tuple(int(x) for x in s.split("-")) for s in re.split(r'\s*/\s*', v)]
                decisive = [(h, a) for h, a in decisive if h != a]
                if decisive and all((a > h) if hit_a else (h > a) for h, a in decisive):
                    warns.append(
                        f'{label} · {brand}: favor 提到「{ta if hit_a else tb}」但归一 "{v}" 全是对方赢'
                        f'——若原话是"某队踢不赢/会输"类反着点名的可忽略，否则朝向判反了')
        # 漏归一：有最可能比分却没给归一结果
        for mm in m.get("models", []):
            if mm.get("brand") in mp:
                continue
            if parse_fan_block(mm.get("discussion_md")).get("最可能比分"):
                warns.append(f'{label} · {mm.get("brand")}: 原话有最可能比分但 norm_out 里没有这条（漏归一？）')
    return errors, warns


def cmd_apply(args):
    merged = load(args.merged)
    norm = load(args.norm)
    errors, warns = check_norm(merged, norm)
    for w in warns:
        print(f"[normalize] ⚠ {w}")
    if errors:
        for e in errors:
            print(f"[normalize] ✗ {e}")
        print(f"[normalize] 校验不通过（{len(errors)} 处硬伤），未写回。修正 norm_out.json 后重跑 apply")
        raise SystemExit(1)
    applied = 0
    for m in merged.values():
        mp = norm.get(m["match_id"]) or {}
        for mm in m.get("models", []):
            v = mp.get(mm.get("brand"))
            if v:
                mm["pred_score_norm"] = str(v).strip()
                applied += 1
    Path(args.merged).write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
    tail = f"；⚠ {len(warns)} 条提醒请回头复核" if warns else ""
    print(f"[normalize] apply {applied} 条 pred_score_norm 写回 -> {args.merged}{tail}")


def main():
    ap = argparse.ArgumentParser(description="比分归一（主队-客队朝向）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract", help="从 merged.json 抽待归一比分")
    e.add_argument("--merged", required=True)
    e.add_argument("--out", required=True)
    e.set_defaults(func=cmd_extract)
    a = sub.add_parser("apply", help="把归一结果写回 merged.json")
    a.add_argument("--merged", required=True)
    a.add_argument("--norm", required=True)
    a.set_defaults(func=cmd_apply)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
