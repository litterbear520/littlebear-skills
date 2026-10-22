#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取竞彩"全部玩法实时倍率"（jj.zhenzhunsp.cn 背后的 justpost.haoyun999.cn 接口）。

两个接口：
  GetSimpleMatchsAll  —— 在售赛事列表（胜平负/让球 + 单关标记 + FIFA 排名）
  GetMoreSpInfo?matchId=X —— 单场全玩法倍率（胜平负/让球/比分/总进球/半全场）

主用法：
  python fetch_odds.py fetch --pairs pairs.json --out odds.json
    pairs.json = [["西班牙","佛得角"], ["比利时","埃及"]]（worldcup 侧队名）
    脚本自动用模糊匹配把每对队名对到竞彩 matchId，再抓全玩法，按 "主|客" 键输出。
  python fetch_odds.py list --out odds_list.json
    只抓在售列表（选场阶段用：判断哪些有预测的比赛"在售"）。

接口可直接 curl/urllib（带 Referer）。若被阻断，用 --raw-list / --raw-detail-dir
读取事先用 CDP 抓好的 JSON。字段字典见 references/data-sources.md。
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = "https://justpost.haoyun999.cn/api/Game"
LIST_URL = f"{API}/GetSimpleMatchsAll?dateFormat=&notSingle=false&mKind=0&reqtype=0"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Referer": "https://jj.zhenzhunsp.cn/", "Origin": "https://jj.zhenzhunsp.cn"}

# 比分字段 -> (主队进球, 客队进球)；胜其他/平其他/负其他单列
SCORE_HOME = [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (3, 2), (4, 0), (4, 1), (4, 2), (5, 0), (5, 1), (5, 2)]
SCORE_DRAW = [(0, 0), (1, 1), (2, 2), (3, 3)]
SCORE_AWAY = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3), (0, 4), (1, 4), (2, 4), (0, 5), (1, 5), (2, 5)]
HTFT = [("33", "主/主"), ("31", "主/平"), ("30", "主/负"), ("13", "平/主"), ("11", "平/平"),
        ("10", "平/负"), ("03", "负/主"), ("01", "负/平"), ("00", "负/负")]


def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def norm(s):
    return (s or "").strip()


def team_eq(a, b):
    """模糊队名匹配：去空格后任一方为另一方子串即视为同队（处理 沙特/沙特阿拉伯 这类差异）。"""
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    return a == b or a in b or b in a


# ---------- 列表 ----------
def normalize_list(raw):
    out = []
    for day in raw.get("data", []) or []:
        for m in day.get("list", []) or []:
            out.append({
                "haoyun_match_id": m.get("matchId"),
                "lotteryid": m.get("lotteryId"),
                "league": m.get("leagueChs"),
                "homeChs": m.get("homeChs"),
                "awayChs": m.get("awayChs"),
                "homerank": m.get("homeRank"),
                "awayrank": m.get("awayRank"),
                "matchtime": m.get("matchTime"),
                "dateFormat": day.get("dateFormat"),
                "goalFoot": m.get("goalFoot"),
                "spf": {"win": m.get("spfWinFoot"), "draw": m.get("spfEqualFoot"), "lose": m.get("spfLoseFoot")},
                "rqspf": {"win": m.get("rspfWinFoot"), "draw": m.get("rspfEqualFoot"), "lose": m.get("rspfLoseFoot")},
                "single_spf": m.get("singleSpfFoot"),
                "single_rqspf": m.get("singleRqspfFoot"),
            })
    return out


def fetch_list(args):
    if args.raw_list:
        raw = json.loads(Path(args.raw_list).read_text(encoding="utf-8"))
    else:
        raw = get_json(LIST_URL)
    return normalize_list(raw)


# ---------- 单场全玩法 ----------
def normalize_detail(f, home, away):
    def grp(pairs, side, prefix):
        outs = []
        for h, a in pairs:
            v = f.get(f"{prefix}{h}{a}")
            if v:
                outs.append({"label": f"{h}:{a}", "side": side, "odds": v})
        return outs

    score = grp(SCORE_HOME, "home", "sw") + grp(SCORE_DRAW, "draw", "sd") + grp(SCORE_AWAY, "away", "sl")
    for code, side, lab in [("sw5", "home", "胜其他"), ("sd4", "draw", "平其他"), ("sl5", "away", "负其他")]:
        if f.get(code):
            score.append({"label": lab, "side": side, "odds": f.get(code)})

    goals = []
    for i in range(8):
        v = f.get(f"t{i}")
        if v:
            goals.append({"label": ("7+" if i == 7 else str(i)), "odds": v})

    htft = [{"label": lab, "odds": f.get(f"ht{code}")} for code, lab in HTFT if f.get(f"ht{code}")]

    spf_outs = []
    for sel, key, lab in [("胜", "spf_win", f"{home}胜"), ("平", "spf_draw", "平局"), ("负", "spf_lost", f"{away}胜")]:
        if f.get(key):
            spf_outs.append({"sel": sel, "label": lab, "odds": f.get(key)})

    line = f.get("rfspf_goal")
    rq_outs = []
    for sel, key in [("让胜", "rfspf_win"), ("让平", "rfspf_draw"), ("让负", "rfspf_lost")]:
        if f.get(key):
            rq_outs.append({"sel": sel, "odds": f.get(key)})

    return {
        "haoyun_match_id": f.get("matchId"),
        "lotteryid": f.get("lotteryid"),
        "homeChs": home, "awayChs": away,
        "homerank": f.get("homerank"), "awayrank": f.get("awayrank"),
        "matchtime": f.get("matchtime"),
        "singles": {
            "spf": f.get("singlespf"), "rqspf": f.get("singlerqspf"),
            "score": f.get("singlebf"), "goals": f.get("singlejq"), "htft": f.get("singlebqc"),
        },
        "markets": {
            "spf": {"available": bool(spf_outs), "outcomes": spf_outs},
            "rqspf": {"line": line, "outcomes": rq_outs},
            "score": {"outcomes": score},
            "goals": {"outcomes": goals},
            "htft": {"outcomes": htft},
        },
    }


def fetch_detail(mid, home, away, raw_dir):
    if raw_dir:
        raw = json.loads((Path(raw_dir) / f"{mid}.json").read_text(encoding="utf-8"))
    else:
        raw = get_json(f"{API}/GetMoreSpInfo?matchId={mid}&mKind=0")
    f = (raw.get("data") or {}).get("footballMoreSpInfo")
    if not f:
        return None
    return normalize_detail(f, home, away)


# ---------- 子命令 ----------
def cmd_list(args):
    lst = fetch_list(args)
    Path(args.out).write_text(json.dumps(lst, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[list] 在售 {len(lst)} 场 -> {args.out}")
    for m in lst:
        print(f"  {m['lotteryid']}  {m['homeChs']}({m['homerank']}) vs {m['awayChs']}({m['awayrank']})  haoyunId={m['haoyun_match_id']}")


def cmd_fetch(args):
    pairs = json.loads(Path(args.pairs).read_text(encoding="utf-8"))
    lst = fetch_list(args)
    result = {}
    for ta, tb in pairs:
        hit = next((m for m in lst if team_eq(m["homeChs"], ta) and team_eq(m["awayChs"], tb)), None)
        key = f"{ta}|{tb}"
        if not hit:
            result[key] = {"matched": False, "reason": "未在在售列表中找到（可能未开售/已封盘）"}
            print(f"[miss] {ta} vs {tb} —— 不在在售列表")
            continue
        det = fetch_detail(hit["haoyun_match_id"], hit["homeChs"], hit["awayChs"],
                           args.raw_detail_dir)
        if not det:
            result[key] = {"matched": False, "reason": "全玩法接口无数据"}
            print(f"[miss] {ta} vs {tb} —— 全玩法无数据")
            continue
        det["matched"] = True
        det["list_info"] = hit
        result[key] = det
        mk = det["markets"]
        print(f"[ok] {ta} vs {tb} (haoyunId={hit['haoyun_match_id']}) "
              f"比分{len(mk['score']['outcomes'])}项/总进球{len(mk['goals']['outcomes'])}项/"
              f"半全场{len(mk['htft']['outcomes'])}项 单关:{det['singles']}")
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fetch] {sum(1 for v in result.values() if v.get('matched'))}/{len(pairs)} 场命中 -> {args.out}")


def main():
    ap = argparse.ArgumentParser(description="抓取竞彩全玩法实时倍率")
    ap.add_argument("--raw-list", help="改读事先抓好的列表 JSON（CDP 兜底）")
    ap.add_argument("--raw-detail-dir", help="改读事先抓好的单场详情目录，文件名 {haoyunId}.json（CDP 兜底）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="只抓在售赛事列表")
    pl.add_argument("--out", default="odds_list.json")
    pl.set_defaults(func=cmd_list)

    pf = sub.add_parser("fetch", help="按队名对抓全玩法倍率")
    pf.add_argument("--pairs", required=True, help='JSON 文件: [["西班牙","佛得角"], ...]')
    pf.add_argument("--out", default="odds.json")
    pf.set_defaults(func=cmd_fetch)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
