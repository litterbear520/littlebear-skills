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


def cmd_apply(args):
    merged = load(args.merged)
    norm = load(args.norm)
    applied = 0
    for m in merged.values():
        mp = norm.get(m["match_id"]) or {}
        for mm in m.get("models", []):
            v = mp.get(mm.get("brand"))
            if v:
                mm["pred_score_norm"] = str(v).strip()
                applied += 1
    Path(args.merged).write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
    print(f"[normalize] apply {applied} 条 pred_score_norm 写回 -> {args.merged}")


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
