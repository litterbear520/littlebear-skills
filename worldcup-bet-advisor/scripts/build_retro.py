#!/usr/bin/env python3
"""上期复盘事实层：把上一期各模型的下注 + 最可能比分，对照终场结果判对错。

纯确定性、零判断：方向＝该模型实际下注（含让球结算）是否中；比分＝其『最可能比分』
（已在第3步归一到主客朝向，多个比分命中任一即算中）是否完全命中终场。产物 retro.json
只摆事实，渲染进下一期报告顶部的"上期复盘"模块（见 build_report.render_retro）。

输入：
  --prev-merged  上一期的 merged.json（含各模型 bet / pred_score_norm / 让球线 markets.rqspf.line）
  --finals       含终场比分的赛程索引（fetch_predictions.py index --include-finished 的产物）
  --out          retro.json 输出路径（默认 <prev-merged 同目录>/retro.json）

只复盘"终场已出"的场；未踢完的自动跳过。没有可复盘的场 → 不写文件、返回码 0（上层据此略过模块）。
"""
import argparse
import json
import re
from pathlib import Path

# 下注池 + 选项 → 中文方向标签（仅用于 cell 的 hover 提示，判中靠 settle()）
SEL_LABEL = {
    "HAD": {"H": "主胜", "D": "平", "A": "客胜"},
    "HHAD": {"H": "让胜", "D": "让平", "A": "让负"},
}


def parse_final(finals_path):
    """读终场索引 → {match_id: (team_a_goals, team_b_goals)}，只收 finished + 有 score 的。"""
    raw = json.loads(Path(finals_path).read_text(encoding="utf-8"))
    matches = raw.get("matches", raw) if isinstance(raw, dict) else raw
    out = {}
    for m in matches:
        sc = m.get("score")
        if m.get("finished") and isinstance(sc, dict) and sc.get("team_a") is not None:
            out[str(m.get("match_id"))] = (int(sc["team_a"]), int(sc["team_b"]))
    return out


def result_side(a, b):
    """终场比分 → 胜平负代码 + 中文。"""
    if a > b:
        return "H", "主胜"
    if a < b:
        return "A", "客胜"
    return "D", "平"


def settle(pool, sel, a, b, line):
    """判一注是否命中。HAD 直接对胜平负；HHAD 按 adjusted_home = 主队进球 + 让球线 再比。
    让球线带符号：'+2' = 主队受让 2 球、'-1' = 主队让出 1 球。line 缺失则该注无法判（None）。"""
    if not pool or not sel:
        return None
    if pool == "HAD":
        return sel == result_side(a, b)[0]
    if pool == "HHAD":
        if line is None:
            return None
        adj = a + line
        side = "H" if adj > b else ("A" if adj < b else "D")
        return sel == side
    return None  # 其它玩法（比分/总进球/半全场单关）本模块不判方向


def parse_line(raw):
    """'+2' / '-1' / 2 → float；解析不了返回 None。"""
    if raw is None:
        return None
    try:
        return float(str(raw).replace("＋", "+").strip())
    except ValueError:
        return None


def score_components(norm):
    """'1-1 / 1-0' → ['1-1','1-0']；统一连字符，去空。"""
    if not norm:
        return []
    parts = re.split(r"[/、]", str(norm))
    return [p.strip().replace("：", "-").replace(":", "-") for p in parts if p.strip()]


def detect_upset(match, rcode):
    """终场是否爆冷：市场（score 隐含的胜平负概率）最看好的一方没赢、且其概率不低（≥0.45）。
    spf 常不可用，这里用 derived.score_implied_1x2，缺失则保守判不冷。"""
    imp = (match.get("derived") or {}).get("score_implied_1x2") or {}
    probs = {"H": imp.get("home"), "D": imp.get("draw"), "A": imp.get("away")}
    probs = {k: v for k, v in probs.items() if isinstance(v, (int, float))}
    if not probs:
        return False
    fav = max(probs, key=probs.get)
    return rcode != fav and probs[fav] >= 0.45


def build_retro(prev_merged, finals, reviewed_date=None):
    finals_map = parse_final(finals)
    order = sorted(prev_merged.values(), key=lambda m: m.get("kickoff_at") or "")

    matches_out = []
    # 每模型累计：方向命中/参与、比分命中/给出
    agg = {}  # brand -> {dh, dt, sh, st, marks:[...]}

    def slot(brand):
        return agg.setdefault(brand, {"brand": brand, "dir_hit": 0, "dir_total": 0,
                                      "score_hit": 0, "score_total": 0})

    for m in order:
        mid = str(m.get("match_id"))
        if mid not in finals_map:
            continue  # 未踢完 / 拿不到终场 → 跳过
        a, b = finals_map[mid]
        rcode, rlabel = result_side(a, b)
        line = parse_line(((m.get("markets") or {}).get("rqspf") or {}).get("line"))
        upset = detect_upset(m, rcode)

        cells = {}
        for mod in m.get("models", []):
            brand = mod.get("brand")
            if not brand:
                continue
            bet = mod.get("bet") or {}
            pool, sel = bet.get("pool_code"), bet.get("selection_code")
            dir_right = settle(pool, sel, a, b, line)
            dir_given = dir_right is not None

            comps = score_components(mod.get("pred_score_norm"))
            score_given = bool(comps)
            score_hit = score_given and (f"{a}-{b}" in comps)

            s = slot(brand)
            if dir_given:
                s["dir_total"] += 1
                if dir_right:
                    s["dir_hit"] += 1
            if score_given:
                s["score_total"] += 1
                if score_hit:
                    s["score_hit"] += 1

            cells[brand] = {
                "dir": bool(dir_right), "dir_given": dir_given,
                "score": bool(score_hit), "score_given": score_given,
                "bet": (mod.get("bet_direction") or SEL_LABEL.get(pool, {}).get(sel, "")) if dir_given else "",
                "pred": " / ".join(comps),
            }

        matches_out.append({
            "match_id": mid, "team_a": m.get("team_a"), "team_b": m.get("team_b"),
            "team_a_logo": m.get("team_a_logo"), "team_b_logo": m.get("team_b_logo"),
            "final": f"{a}:{b}", "result": rlabel, "upset": upset, "cells": cells,
        })

    if not matches_out:
        return None

    # 排名：方向命中数 → 比分命中数 → 方向命中率 → 名字
    summary = sorted(agg.values(),
                     key=lambda s: (s["dir_hit"], s["score_hit"],
                                    s["dir_hit"] / s["dir_total"] if s["dir_total"] else 0, s["brand"]),
                     reverse=True)
    return {
        "reviewed_date": reviewed_date or "",
        "n_matches": len(matches_out),
        "summary": summary,
        "matches": matches_out,
    }


def main():
    ap = argparse.ArgumentParser(description="生成上期复盘事实 JSON（各模型方向/比分对错）")
    ap.add_argument("--prev-merged", required=True, help="上一期 merged.json")
    ap.add_argument("--finals", required=True, help="含终场比分的赛程索引 JSON")
    ap.add_argument("--date", help="被复盘那期的日期 YYYY-MM-DD（写入 reviewed_date）")
    ap.add_argument("--out", help="输出 retro.json（默认 prev-merged 同目录/retro.json）")
    args = ap.parse_args()

    prev_merged = json.loads(Path(args.prev_merged).read_text(encoding="utf-8"))
    finals = args.finals
    retro = build_retro(prev_merged, finals, reviewed_date=args.date)
    if retro is None:
        print("[retro] 上期没有已踢完的可复盘场次 —— 跳过，不写文件")
        return
    out = args.out or str(Path(args.prev_merged).with_name("retro.json"))
    Path(out).write_text(json.dumps(retro, ensure_ascii=False, indent=2), encoding="utf-8")
    nm = len(retro["summary"])
    top = retro["summary"][0]
    print(f"[retro] {retro['n_matches']} 场 × {nm} 模型 -> {out}"
          f"（上期最准 {top['brand']} 方向 {top['dir_hit']}/{top['dir_total']}）")


if __name__ == "__main__":
    main()
