#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取 worldcup.lyihub.com 的"嘉豪世界杯预测"数据。

两个子命令：
  index   —— 抓 data/index.json，输出"未开赛 + 有预测"的近几场，供用户勾选。
  matches —— 抓 data/matches/{id}.json，抽取每个 agent 的 bet + 讨论正文。

数据是纯静态 JSON，默认用 urllib 直接拉；若被网络环境阻断，可用 --raw-dir 读取
事先用 CDP/浏览器抓好的同名 JSON 文件（{id}.json / index.json）。

字段细节见 references/data-sources.md。
"""
import argparse
import base64
import json
import sys
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SITE = "https://worldcup.lyihub.com"
BASE = f"{SITE}/data"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# index 短键 / model_name 关键词 -> 统一厂牌
BRAND_RULES = [
    ("deepseek", "DeepSeek"),
    ("claude", "Claude"),
    ("gpt", "GPT"),
    ("openai", "GPT"),
    ("gemini", "Gemini"),
    ("glm", "GLM"),
    ("kimi", "Kimi"),
]


def brand_of(name: str) -> str:
    low = (name or "").lower()
    for kw, brand in BRAND_RULES:
        if kw in low:
            return brand
    return name or "未知"


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://worldcup.lyihub.com/"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def load_index(raw_dir):
    if raw_dir:
        return json.loads((Path(raw_dir) / "index.json").read_text(encoding="utf-8"))
    return get_json(f"{BASE}/index.json")


def load_match(mid, raw_dir):
    if raw_dir:
        return json.loads((Path(raw_dir) / f"{mid}.json").read_text(encoding="utf-8"))
    return get_json(f"{BASE}/matches/{mid}.json")


_logo_cache = {}


def fetch_logo_b64(team_id, enable=True):
    """下载球队圆形徽标 assets/teams/{id}-logo-120.png 并转 base64 data URI（内联进报告，
    保持离线+单文件）。失败或 enable=False（CDP 兜底/离线）时返回 None，报告降级为纯文字卡。
    按 team_id 缓存，避免一次 run 内重复下载同一队。"""
    if not enable or not team_id:
        return None
    tid = str(team_id)
    if tid in _logo_cache:
        return _logo_cache[tid]
    data = None
    try:
        req = urllib.request.Request(f"{SITE}/assets/teams/{tid}-logo-120.png",
                                     headers={"User-Agent": UA, "Referer": "https://worldcup.lyihub.com/"})
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read()
        if raw:
            data = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    except Exception as e:
        print(f"[logo] {tid} 徽标抓取失败(降级纯文字): {e}", file=sys.stderr)
    _logo_cache[tid] = data
    return data


# ---------- index 子命令 ----------
def cmd_index(args):
    idx = load_index(args.raw_dir)
    matches = idx.get("matches", [])
    out = []
    for m in matches:
        if not m.get("has_predict"):
            continue
        # 已经踢完的(有比分)默认跳过，除非 --include-finished
        finished = m.get("score") is not None
        if finished and not args.include_finished:
            continue
        bets = m.get("bets") or {}
        agents = sorted({a for lst in bets.values() for a in (lst or [])})
        out.append({
            "match_id": str(m.get("match_id")),
            "team_a": m.get("team_a"),
            "team_b": m.get("team_b"),
            "kickoff_at": m.get("kickoff_at"),   # UTC ISO
            "stage": m.get("stage"),
            "finished": finished,
            "score": m.get("score"),
            "agents_with_bet": [brand_of(a) for a in agents],
            "bets": bets,
            "comment": m.get("comment") or {},
        })
    result = {
        "generated_at": idx.get("generated_at"),
        "server_now": idx.get("server_now"),
        "competition_name": idx.get("competition_name"),
        "count": len(out),
        "matches": out,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[index] {len(out)} 场有预测的比赛 -> {args.out}")
    for m in out:
        flag = "（已赛）" if m["finished"] else ""
        print(f"  {m['match_id']}  {m['kickoff_at']}  {m['team_a']} vs {m['team_b']} {flag}  预测:{','.join(m['agents_with_bet'])}")


# ---------- matches 子命令 ----------
def extract_model(p, team_a, team_b):
    """从单个 llm_predict 条目抽取我们关心的信息。"""
    name = p.get("model_name", "")
    bet = p.get("bet") or {}
    pool = bet.get("pool_code")
    sel = bet.get("selection_code")
    if pool == "HAD":
        dir_label = {"H": f"{team_a}胜", "D": "平局", "A": f"{team_b}胜"}.get(sel, f"{pool}/{sel}")
    elif pool == "HHAD":
        dir_label = {"H": f"{team_a}让球赢盘", "D": "让球走盘(平)", "A": f"{team_b}让球赢盘"}.get(sel, f"{pool}/{sel}")
    else:
        dir_label = None
    return {
        "brand": brand_of(name),
        "model_name": name,
        "status": p.get("status"),
        "has_bet": bool(bet),
        "bet": bet,
        "bet_direction": dir_label,        # 结构化投注方向（可能为空=暂无投注）
        "discussion_md": p.get("fan_subjective_prediction_md", ""),  # 这就是"讨论"正文
    }


def cmd_matches(args):
    ids = [s.strip() for s in args.ids.split(",") if s.strip()]
    result = {}
    for mid in ids:
        try:
            j = load_match(mid, args.raw_dir)
        except Exception as e:
            print(f"[warn] 抓取 {mid} 失败: {e}", file=sys.stderr)
            continue
        match = j.get("match", {})
        team_a = match.get("team_a")
        team_b = match.get("team_b")
        models = [extract_model(p, team_a, team_b) for p in j.get("llm_predict", [])]
        net = not args.raw_dir  # CDP 兜底/离线时不走网络抓徽标，降级纯文字
        # 站点自带的简版赔率（仅 HHAD 一条），仅作参考；真实全玩法倍率来自 odds 侧
        result[mid] = {
            "match_id": mid,
            "team_a": team_a,
            "team_b": team_b,
            "team_a_id": match.get("team_a_id"),
            "team_b_id": match.get("team_b_id"),
            "team_a_logo": fetch_logo_b64(match.get("team_a_id"), enable=net),  # base64 圆形徽标
            "team_b_logo": fetch_logo_b64(match.get("team_b_id"), enable=net),
            "kickoff_at": match.get("kickoff_at"),
            "stage": match.get("stage"),
            "venue": match.get("venue"),
            "weather": match.get("weather"),
            "site_odds": match.get("odds"),
            "models": models,
        }
        brands = ", ".join(f"{m['brand']}({m['bet_direction'] or '暂无投注'})" for m in models)
        print(f"[match] {mid} {team_a} vs {team_b} | {brands}")
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[matches] {len(result)} 场 -> {args.out}")


def main():
    ap = argparse.ArgumentParser(description="抓取 worldcup.lyihub.com 预测数据")
    ap.add_argument("--raw-dir", help="改为从本地目录读取事先抓好的 JSON（CDP 兜底用）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("index", help="抓赛程，列出有预测的近几场")
    pi.add_argument("--out", default="preds_index.json")
    pi.add_argument("--include-finished", action="store_true", help="也包含已踢完的比赛")
    pi.set_defaults(func=cmd_index)

    pm = sub.add_parser("matches", help="抓指定比赛的逐 agent 预测与讨论")
    pm.add_argument("--ids", required=True, help="逗号分隔的 match_id，如 54329959,54329974")
    pm.add_argument("--out", default="predictions.json")
    pm.set_defaults(func=cmd_matches)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
