#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并预测(predictions.json) + 倍率(odds.json) -> 每场统一对象 merged.json。

对每个玩法做"去水"(de-vig)：
  隐含概率 implied = 1/赔率；一场内归一化 fair = implied / Σimplied。
  margin = Σimplied - 1（庄家水位/抽水）。
并从比分市场反推 1X2 概率，与胜平负市场互为校验。
还为每个模型抽取一句"我更看好"，便于报告与脚注。

这一步只做确定性数学；"读讨论下结论"由模型在 analysis.json 里完成。
"""
import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def team_eq(a, b):
    a, b = (a or "").strip(), (b or "").strip()
    return bool(a) and bool(b) and (a == b or a in b or b in a)


def devig(outcomes):
    """就地为 outcomes 添加 implied_prob / fair_prob，返回 (margin, total_implied)。"""
    valid = [o for o in outcomes if o.get("odds")]
    total = sum(1.0 / o["odds"] for o in valid)
    for o in outcomes:
        if o.get("odds"):
            o["implied_prob"] = round(1.0 / o["odds"], 4)
            o["fair_prob"] = round((1.0 / o["odds"]) / total, 4) if total else None
    return (round(total - 1.0, 4) if total else None), round(total, 4) if total else None


def lean_of(discussion_md):
    """从讨论里抽 '我更看好' 那一句。"""
    if not discussion_md:
        return None
    for line in discussion_md.splitlines():
        if "我更看好" in line:
            s = re.sub(r"[*#>\-\s]+", " ", line).strip()
            s = s.split("我更看好", 1)[1].lstrip("：: ").strip()
            return s[:80] if s else None
    return None


def score_implied_1x2(score_market):
    """从比分市场反推 主胜/平/客胜 的公平概率（聚合 side）。"""
    agg = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for o in score_market.get("outcomes", []):
        if o.get("fair_prob") is not None and o.get("side") in agg:
            agg[o["side"]] += o["fair_prob"]
    return {k: round(v, 4) for k, v in agg.items()}


def process_markets(markets):
    summary = {}
    for name in ("spf", "rqspf", "score", "goals", "htft"):
        mk = markets.get(name)
        if not mk:
            continue
        margin, total = devig(mk.get("outcomes", []))
        mk["margin"] = margin
        if name == "score":
            summary["score_implied_1x2"] = score_implied_1x2(mk)
        if name in ("score", "goals", "htft"):
            # 最可能的前几项，便于报告高亮
            ranked = sorted([o for o in mk["outcomes"] if o.get("fair_prob") is not None],
                            key=lambda o: -o["fair_prob"])
            mk["top"] = [{"label": o["label"], "odds": o["odds"], "fair_prob": o["fair_prob"]} for o in ranked[:5]]
    return summary


def cmd(args):
    preds = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    odds = json.loads(Path(args.odds).read_text(encoding="utf-8"))
    merged = {}
    for mid, p in preds.items():
        ta, tb = p["team_a"], p["team_b"]
        key = f"{ta}|{tb}"
        od = odds.get(key)
        if od is None:  # 兜底模糊匹配
            for k, v in odds.items():
                kh, _, ka = k.partition("|")
                if team_eq(kh, ta) and team_eq(ka, tb):
                    od = v
                    break
        models = []
        for m in p["models"]:
            m["lean"] = lean_of(m.get("discussion_md", ""))
            models.append(m)
        entry = {
            "match_id": mid,
            "team_a": ta, "team_b": tb,
            "team_a_id": p.get("team_a_id"), "team_b_id": p.get("team_b_id"),
            "team_a_logo": p.get("team_a_logo"), "team_b_logo": p.get("team_b_logo"),  # base64 徽标(可为 None)
            "kickoff_at": p.get("kickoff_at"),
            "stage": p.get("stage"),
            "models": models,
            "odds_matched": bool(od and od.get("matched")),
        }
        if od and od.get("matched"):
            mk = od["markets"]
            derived = process_markets(mk)
            entry.update({
                "lotteryid": od.get("lotteryid"),
                "homerank": od.get("homerank"),
                "awayrank": od.get("awayrank"),
                "singles": od.get("singles"),
                "markets": mk,
                "derived": derived,
            })
        else:
            entry["odds_note"] = (od or {}).get("reason", "无倍率数据")
        merged[mid] = entry
        nb = sum(1 for m in models if m["has_bet"])
        rk = f"{entry.get('homerank','?')}-{entry.get('awayrank','?')}" if entry["odds_matched"] else "无赔率"
        print(f"[merge] {ta} vs {tb} | 排名{rk} | {len(models)}模型({nb}下注) | 倍率:{'有' if entry['odds_matched'] else '缺'}")

    Path(args.out).write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[merge] {len(merged)} 场 -> {args.out}")


def main():
    ap = argparse.ArgumentParser(description="合并预测与倍率，做去水概率")
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--odds", required=True)
    ap.add_argument("--out", default="merged.json")
    ap.set_defaults(func=cmd)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
