#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
赛后复盘的【事实层】（确定性）。规律洞察、模型校准、买法调整、经验沉淀全由模型做，本脚本只算事实。

子命令：
  locate  —— 列出"未复盘"的历史场（已踢完 + 有预测 + 不在 manifest）和"待复盘的自有 run"。
  score   —— 给定 match_id，拉终场比分 + result(主/平/客) + 总进球 + 各模型 bet 方向对错（HAD/HHAD）。
  mark    —— 把 match_id / 自有 run 日期写进 manifest（复盘完成后调用，保证踢过的不重复分析）。

manifest: references/reviewed_matches.json
直连失败时各子命令支持 --raw-dir（沿用 fetch_predictions 的 CDP 兜底：目录里放 index.json / {id}.json）。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch_predictions import brand_of, load_index, load_match  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKILL_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = SKILL_ROOT / "references" / "reviewed_matches.json"
RUNS = SKILL_ROOT / "runs"


def load_manifest():
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    else:
        m = {}
    m.setdefault("reviewed_match_ids", [])
    m.setdefault("last_synced", None)
    m.setdefault("own_runs_reviewed", [])
    return m


def save_manifest(m):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


def result_of(score):
    """score={team_a,team_b} -> {a,b,side(主/平/客),total} 或 None（未踢完）"""
    if not score:
        return None
    a, b = score.get("team_a"), score.get("team_b")
    if a is None or b is None:
        return None
    a, b = int(a), int(b)
    side = "主胜" if a > b else ("平局" if a == b else "客胜")
    return {"a": a, "b": b, "side": side, "total": a + b}


def site_hhad_line(match):
    """从站点详情 match.odds 取 HHAD 让球线（home 让球，如 -2）。无则 None。"""
    for o in (match.get("odds") or []):
        if o.get("pool_code") == "HHAD" and o.get("HHAD_line") is not None:
            try:
                return float(o["HHAD_line"])
            except (TypeError, ValueError):
                return None
    return None


def model_right(bet, res, line):
    """bet={pool_code,selection_code} 对照终场判对错。返回 True/False/None(暂无投注或无法判)。"""
    pool, sel = bet.get("pool_code"), bet.get("selection_code")
    if not pool or not sel:
        return None
    if pool == "HAD":
        return sel == {"主胜": "H", "平局": "D", "客胜": "A"}[res["side"]]
    if pool == "HHAD":
        if line is None:
            return None
        adj = res["a"] + line
        cover = "H" if adj > res["b"] else ("D" if adj == res["b"] else "A")
        return sel == cover
    return None


# ---------- locate ----------
def cmd_locate(args):
    man = load_manifest()
    reviewed = set(man["reviewed_match_ids"])
    idx = load_index(args.raw_dir)
    by_id = {str(m.get("match_id")): m for m in idx.get("matches", [])}

    historical = []
    for m in idx.get("matches", []):
        mid = str(m.get("match_id"))
        if not m.get("has_predict") or m.get("score") is None or mid in reviewed:
            continue
        historical.append({
            "match_id": mid, "team_a": m.get("team_a"), "team_b": m.get("team_b"),
            "kickoff_at": m.get("kickoff_at"), "score": m.get("score"),
        })

    # 与 Track 1 对称：列出【所有】未复盘的自有 run（不只最近一个），Track 2 逐个补买法复盘。
    # 已复盘的 run（在 own_runs_reviewed 里）跳过；全 pending 的 run（如今天刚出、还没踢）不列。
    owns = []
    reviewed_runs = set(man["own_runs_reviewed"])
    if RUNS.exists():
        cand = sorted((d for d in RUNS.iterdir() if d.is_dir() and (d / "analysis.json").exists()),
                      key=lambda d: d.name)  # 旧→新
        for d in cand:
            if d.name in reviewed_runs:
                continue
            try:
                merged = json.loads((d / "merged.json").read_text(encoding="utf-8"))
                mids = [str(k) for k in merged.keys()]
            except (OSError, ValueError):
                mids = []
            done = [mid for mid in mids if (by_id.get(mid) or {}).get("score") is not None]
            if done:  # 至少一场已踢完才可买法复盘
                owns.append({"date": d.name, "dir": str(d), "match_ids": mids,
                             "finished_ids": done, "pending_ids": [x for x in mids if x not in done]})

    # 标注重合：哪些"未复盘历史场"同时也落在【任一】未复盘自有 run 里（昨天下注、今天踢完）。
    # 这类场既要 Track 1 建库（各模型嘉豪预测 vs 终场 → 经验），又要 Track 2 买法对账，
    # 别把前者塌缩进后者——in_own_run 让模型在数据层就看到这一点。
    own_ids = set().union(*[set(o["match_ids"]) for o in owns]) if owns else set()
    for h in historical:
        h["in_own_run"] = h["match_id"] in own_ids
    overlap = [h for h in historical if h["in_own_run"]]

    out = {"reviewed_count": len(reviewed), "historical_unreviewed": historical,
           "own_runs_to_review": owns,
           "own_run_to_review": owns[-1] if owns else None}  # 兼容：最近一个，供报告 --retro 渲染
    if args.out:
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    run_dates = [o["date"] for o in owns]
    print(f"[locate] 未复盘历史场 {len(historical)} | 待复盘自有 run {len(owns)} 个: {run_dates or '无'}")
    if overlap:
        names = "、".join(f'{h["team_a"]}vs{h["team_b"]}' for h in overlap)
        print(f"[locate] ⚠ {len(overlap)} 场重合：既要 Track1 建库嘉豪复盘、又要 Track2 买法对账，别只做后者 → {names}")
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ---------- score ----------
def cmd_score(args):
    ids = [s.strip() for s in args.ids.split(",") if s.strip()]
    out = []
    for mid in ids:
        try:
            j = load_match(mid, args.raw_dir)
        except Exception as e:
            print(f"[warn] {mid} 抓取失败: {e}", file=sys.stderr)
            continue
        match = j.get("match", {})
        res = result_of(match.get("score"))
        if not res:
            out.append({"match_id": mid, "team_a": match.get("team_a"),
                        "team_b": match.get("team_b"), "finished": False})
            continue
        line = site_hhad_line(match)
        models = []
        for p in j.get("llm_predict", []):
            bet = p.get("bet") or {}
            models.append({"brand": brand_of(p.get("model_name", "")),
                           "model_name": p.get("model_name", ""),
                           "bet": bet, "right": model_right(bet, res, line)})
        out.append({
            "match_id": mid, "team_a": match.get("team_a"), "team_b": match.get("team_b"),
            "finished": True, "final_score": f'{res["a"]}:{res["b"]}',
            "result_side": res["side"], "total_goals": res["total"],
            "hhad_line": line, "models": models,
        })
    if args.out:
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for m in out:
        if m.get("finished"):
            tag = " ".join(f'{x["brand"]}{"✓" if x["right"] else ("✗" if x["right"] is False else "·")}'
                           for x in m["models"])
            print(f'  {m["match_id"]} {m["team_a"]} {m["final_score"]} {m["team_b"]} [{m["result_side"]}]  {tag}')
        else:
            print(f'  {m["match_id"]} {m.get("team_a")} vs {m.get("team_b")}  未踢完')
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ---------- mark ----------
def cmd_mark(args):
    man = load_manifest()
    ids = set(man["reviewed_match_ids"])
    if args.ids:
        ids.update(s.strip() for s in args.ids.split(",") if s.strip())
    man["reviewed_match_ids"] = sorted(ids)
    if args.run:
        runs = set(man["own_runs_reviewed"])
        runs.add(args.run)
        man["own_runs_reviewed"] = sorted(runs)
    if args.synced:
        man["last_synced"] = args.synced
    save_manifest(man)
    print(f"[mark] reviewed_match_ids={len(man['reviewed_match_ids'])} own_runs_reviewed={man['own_runs_reviewed']}")


def main():
    ap = argparse.ArgumentParser(description="赛后复盘事实层（locate / score / mark）")
    ap.add_argument("--raw-dir", help="改为从本地目录读取事先抓好的 index.json / {id}.json（CDP 兜底）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("locate", help="列出未复盘历史场 + 待复盘自有 run")
    pl.add_argument("--out")
    pl.set_defaults(func=cmd_locate)

    ps = sub.add_parser("score", help="拉终场比分 + 各模型方向对错")
    ps.add_argument("--ids", required=True, help="逗号分隔 match_id")
    ps.add_argument("--out")
    ps.set_defaults(func=cmd_score)

    pm = sub.add_parser("mark", help="把 match_id / 自有 run 写进 manifest")
    pm.add_argument("--ids", help="逗号分隔 match_id")
    pm.add_argument("--run", help="自有 run 日期，如 2026-06-15")
    pm.add_argument("--synced", help="last_synced 日期")
    pm.set_defaults(func=cmd_mark)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
