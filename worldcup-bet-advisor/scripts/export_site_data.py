#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把一次 run 的数据导出成收益仪表盘要的 data/<日期>.json + data/index.json。

报告本体（三档/逐场/爆冷）仍由 build_report.py 生成的 report.html 提供，站点原样嵌入；
这里只产出**收益仪表盘**需要的最小数据：每天有没有报告、我买的票、当日/累计盈亏。

子命令：
  day     登记当天有报告（status=open，比赛未结算）。可选 --analysis 带上一句总基调。
  settle  次日复盘后，用 retro.json 回填那天「我买的票 + 真实盈亏」（status=settled）。
  reindex 扫所有 data/<日期>.json 重建 index.json（day/settle 后自动调用）。

盈亏口径（settle）：每注 combined_odds = 各腿赔率连乘；
  全中→payout=本金×combined_odds、profit=payout-本金；任一腿不中→profit=-本金；有腿未结算→pending。
"""
import argparse
import datetime
import json
import math
import re
import sys
from itertools import combinations, product
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def weekday_of(ymd):
    try:
        return WEEKDAYS[datetime.date.fromisoformat(ymd).weekday()]
    except ValueError:
        return ""


def resolve_date(meta_date, override):
    for cand in (override, meta_date):
        if cand:
            m = re.match(r"(\d{4}-\d{2}-\d{2})(?:\s+(\S+))?", str(cand).strip())
            if m:
                return m.group(1), m.group(2) or weekday_of(m.group(1))
    raise SystemExit("[export] 无法确定日期：传 --date YYYY-MM-DD（或让 analysis.meta.date 带上）")


def read_existing(target):
    return load(target) if target.exists() else {}


def cmd_day(args):
    summary = None
    meta_date = None
    if args.analysis:
        analysis = load(args.analysis)
        meta = analysis.get("meta", {})
        meta_date = meta.get("date")
        summary = meta.get("risk_note")
    date, weekday = resolve_date(meta_date, args.date)

    out_dir = Path(args.site_data)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{date}.json"
    report = read_existing(target)

    report.update({
        "date": date,
        "weekday": weekday,
        "hasReport": True,
    })
    report.setdefault("status", "open")
    report.setdefault("tickets", [])
    report.setdefault("dayProfit", None)
    report.setdefault("dayStake", None)
    if summary:
        report["summary"] = summary

    dump(target, report)
    print(f"[export] day  {date} -> {target}  (有报告)")
    reindex(out_dir)


def _leg_options(leg):
    """一场比赛的选项列表 [{odds,hit}]。复式腿带 `options`（多比分/多让球选择）；
    单选腿回退到该腿自己的 odds/hit。"""
    opts = leg.get("options")
    if opts:
        return [{"odds": o.get("odds"), "hit": o.get("hit")} for o in opts]
    return [{"odds": leg.get("odds"), "hit": leg.get("hit")}]


def settle_compound(t, idx, date):
    """复式 / 系统过关（M场N关，带 "pass": N）的部分中奖结算。

    按关数 N 枚举所有「N-注」：先从 M 场里选 N 场，再对这 N 场各取一个选项做
    笛卡尔积——这就是一张复式票真实的注数（如 4场2关 + 一场复式2选 = 9 注）。
    每注本金 = 总本金 / 总注数；一注「全中」才回款（各腿赔率连乘），
    payout = Σ(命中注 每注本金 × 连乘)，profit = payout − 总本金。
    全有或全无的普通 N 串 1 不会走这里（无 `pass` 字段）。
    """
    raw_legs = t.get("legs", [])
    stake = float(t.get("stake", 0) or 0)
    npass = int(t.get("pass"))
    matches = [_leg_options(leg) for leg in raw_legs]

    # 关数必须 1≤pass≤场数；否则是录入错误（如 pass 写大于场数会枚举出 0 注、
    # pass=0 会把空组合当成全中），直接报错而不是静默把脏票算成全输/全中。
    if not (1 <= npass <= len(matches)):
        raise ValueError(
            f"复式过关票 {t.get('id') or idx} 的关数 pass={npass} 非法："
            f"必须 1≤pass≤场数({len(matches)})。请检查 settle.json。"
        )

    notes = []  # 所有「注」：每注是被选 N 场各取一个选项的元组
    for chosen in combinations(range(len(matches)), npass):
        for picks in product(*(matches[i] for i in chosen)):
            notes.append(picks)
    total_combos = len(notes)
    per_stake = stake / total_combos if total_combos else 0.0

    pending = any(o.get("hit") is None for m in matches for o in m)
    payout = 0.0
    for picks in notes:
        if all(p.get("hit") is True for p in picks):
            prod = 1.0
            for p in picks:
                prod *= float(p.get("odds") or 0)
            payout += per_stake * prod

    if pending:
        status, payout_out, profit = "pending", 0.0, 0.0
    else:
        payout_out = round(payout, 2)
        profit = round(payout_out - stake, 2)
        status = "win" if profit > 0 else "loss"

    # 每场一腿（match-level hit = 该场任一选项命中），供票卡逐场展示 ✓/✗ 与「命中X场」
    legs = []
    for leg, opts in zip(raw_legs, matches):
        hits = [o.get("hit") for o in opts]
        mhit = None if any(h is None for h in hits) else any(h is True for h in hits)
        leg_out = {"text": leg.get("text"), "odds": leg.get("odds"), "hit": mhit}
        for k in ("matchNo", "home", "away", "category", "pick"):
            if leg.get(k) is not None:
                leg_out[k] = leg.get(k)
        legs.append(leg_out)

    out = {
        "id": t.get("id") or f"{date}-{idx}",
        "tier": t.get("tier", "自选"),
        "type": t.get("type") or f"{len(raw_legs)}场{npass}关",
        "legs": legs,
        "stake": stake,
        "combinedOdds": 0,
        "status": status,
        "payout": payout_out,
        "profit": profit,
        "combos": total_combos,
    }
    if t.get("multiple") is not None:
        out["multiple"] = t.get("multiple")
    if t.get("martingale"):
        out["martingale"] = True
    return out


def settle_ticket(t, idx, date):
    # 复式 / 系统过关（带关数 "pass"）走部分中奖结算，不是全有或全无
    if t.get("pass") is not None:
        return settle_compound(t, idx, date)
    raw_legs = t.get("legs", [])
    stake = float(t.get("stake", 0) or 0)
    # 独立多注票（如「单场固定」一张票选多场多个比分）：每注各自单关、独立结算，
    # 盈亏 = Σ(命中注 本金×赔率 − 本金)，不连乘。每注本金缺省按 总本金/注数 均摊。
    independent = t.get("mode") == "independent"

    legs, odds_product, have_all_odds = [], 1.0, True
    per_default = round(stake / len(raw_legs), 2) if independent and raw_legs else None
    indep_payout, indep_profit, indep_pending = 0.0, 0.0, False
    for leg in raw_legs:
        o = leg.get("odds")
        leg_out = {"text": leg.get("text"), "odds": o, "hit": leg.get("hit")}
        # 票面结构（可选）：主队/客队/赛事编号/玩法类别/选择，有就带上
        for k in ("matchNo", "home", "away", "category", "pick"):
            if leg.get(k) is not None:
                leg_out[k] = leg.get(k)
        if independent:
            ls = float(leg.get("stake", per_default) or 0)
            leg_out["stake"] = ls
            if leg.get("hit") is True and o:
                leg_out["payout"] = round(ls * float(o), 2)
                indep_payout += ls * float(o)
                indep_profit += ls * float(o) - ls
            elif leg.get("hit") is False:
                indep_profit -= ls
            elif leg.get("hit") is None:
                indep_pending = True
        legs.append(leg_out)
        if o:
            odds_product *= float(o)
        else:
            have_all_odds = False

    if independent:
        if indep_pending:
            status = "pending"
            payout, profit = 0.0, 0.0
        else:
            payout = round(indep_payout, 2)
            profit = round(indep_profit, 2)
            status = "win" if profit > 0 else "loss"
        out = {
            "id": t.get("id") or f"{date}-{idx}",
            "tier": t.get("tier", "自选"),
            "type": t.get("type") or "单场固定",
            "mode": "independent",
            "legs": legs,
            "stake": stake,
            "combinedOdds": 0,
            "status": status,
            "payout": payout,
            "profit": profit,
        }
        if t.get("multiple") is not None:
            out["multiple"] = t.get("multiple")
        if t.get("martingale"):
            out["martingale"] = True
        return out

    hits = [leg.get("hit") for leg in raw_legs]
    if any(h is False for h in hits):
        status = "loss"
    elif any(h is None for h in hits):
        status = "pending"
    else:
        status = "win"

    combined = t.get("combined_odds")
    if combined is None and have_all_odds:
        combined = round(odds_product, 2)

    if status == "win" and combined:
        payout = round(stake * float(combined), 2)
        profit = round(payout - stake, 2)
    elif status == "loss":
        payout, profit = 0.0, round(-stake, 2)
    else:
        payout, profit = 0.0, 0.0

    n = len(legs)
    ttype = t.get("type") or ("单关" if n == 1 else f"{n}串1")
    out = {
        "id": t.get("id") or f"{date}-{idx}",
        "tier": t.get("tier", "自选"),
        "type": ttype,
        "legs": legs,
        "stake": stake,
        "combinedOdds": combined if combined is not None else (legs[0]["odds"] if legs and legs[0].get("odds") else 0),
        "status": status,
        "payout": payout,
        "profit": profit,
    }
    # 倍数（如 5 倍）：有就带上，缺省由前端按 本金/2 推（竞彩 2 元/注）
    if t.get("multiple") is not None:
        out["multiple"] = t.get("multiple")
    # 复式/系统过关注数（如 5场4关 = 28 注）：前端据此显示「N注·命中X场」而非单一连乘赔率
    if t.get("combos") is not None:
        out["combos"] = t.get("combos")
    if t.get("martingale"):
        out["martingale"] = True
    return out


def cmd_settle(args):
    retro = load(args.retro)
    date = (args.date or retro.get("reviewed_run") or "").strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise SystemExit("[export] settle 需要 retro.reviewed_run 是 YYYY-MM-DD（或用 --date 指定）")

    bought = retro.get("user_bought", {}) or {}
    tickets = [settle_ticket(t, i, date) for i, t in enumerate(bought.get("tickets", []))]
    resolved = [t for t in tickets if t["status"] != "pending"]
    day_profit = round(sum(t["profit"] for t in resolved), 2) if tickets else 0.0
    day_stake = round(sum(t["stake"] for t in tickets), 2)

    out_dir = Path(args.site_data)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{date}.json"
    report = read_existing(target)

    report.update({
        "date": date,
        "weekday": report.get("weekday") or weekday_of(date),
        "status": "settled",
        "tickets": tickets,
        "dayProfit": day_profit,
        "dayStake": day_stake,
    })
    report.setdefault("hasReport", False)
    if bought.get("summary") and not report.get("summary"):
        report["summary"] = bought["summary"]

    dump(target, report)
    wins = sum(1 for t in tickets if t["status"] == "win")
    print(f"[export] settle {date} -> {target}  ({len(tickets)} 注/命中 {wins}, 当日 {day_profit:+g})")
    reindex(out_dir)


# ---------- 叠层（比分翻倍 / 马丁格尔）核算 ----------
# 玩法：每轮买 scores_per_round 个候选比分、每比分本金翻倍（base→2·base→4·base…），
# 中一个就收官、从底注重开。第 k 层每比分押 base·2^(k-1)、整轮 base·2^k、累计已投
# base·scores·(2^k − 1)。只要比分赔率 O>4，命中即净赚 base·2^(k-1)·(O−4)+base>0。
# 只认带 "martingale": true 的比分独立票；用其 multiple(=每比分本金/base) 反推层数，
# 累计/下一注一律按翻倍口径推（早期没单独记票的底层也能正确还原）。
MART_BASE = 2.0          # 元/比分
MART_SCORES = 2          # 每轮候选比分数
MART_ODDS = 6.0          # 估算「命中可赚」用的比分赔率（你实际多在 5.7~17）


def _mart_layer(multiple):
    """multiple(每比分本金/base): 1→第1层, 2→第2层, 4→第3层 …（层=log2(倍数)+1）。"""
    m = multiple or 1
    return int(round(math.log2(m))) + 1 if m > 0 else 1


def _mart_cost(layer):
    """翻倍口径下，叠到第 layer 层累计已投 = base·scores·(2^layer − 1)。"""
    return MART_BASE * MART_SCORES * (2 ** layer - 1)


def compute_martingale(settled):
    """从已结算各天的 martingale 比分票，按日序还原叠层：history(已命中收官轮) + current(进行中)。"""
    rounds = []
    for r in sorted(settled, key=lambda r: r["date"]):
        for t in (r.get("tickets") or []):
            if not t.get("martingale"):
                continue
            mult = t.get("multiple") or 1
            hit_pick, hit_odds = None, None
            for leg in (t.get("legs") or []):
                if leg.get("hit") is True:
                    pk = leg.get("pick") or leg.get("text") or ""
                    home, away = leg.get("home"), leg.get("away")
                    # pick 可能是纯比分("3:2")也可能已含队名("挪威 3:2 塞内加尔")；
                    # 只有纯比分时才补主客队名，避免重复。
                    if home and away and re.match(r"^\s*\d+\s*:\s*\d+\s*$", str(pk)):
                        hit_pick = f"{home} {pk} {away}"
                    else:
                        hit_pick = pk
                    hit_odds = leg.get("odds")
                    break
            rounds.append({
                "date": r["date"],
                "multiple": mult,
                "perScore": round(MART_BASE * mult, 2),
                "total": round(float(t.get("stake") or 0), 2),
                "status": t.get("status"),
                "profit": round(float(t.get("profit") or 0), 2),
                "won": t.get("status") == "win",
                "hitPick": hit_pick,
                "hitOdds": hit_odds,
                "payout": round(float(t.get("payout") or 0), 2),
            })
    if not rounds:
        return None

    history, cur = [], []
    for rd in rounds:
        cur.append(rd)
        if rd["won"]:
            k = _mart_layer(rd["multiple"])
            cost = _mart_cost(k)
            history.append({
                "wonDate": rd["date"],
                "layers": k,
                "multiple": rd["multiple"],
                "hitPick": rd["hitPick"],
                "hitOdds": rd["hitOdds"],
                "payout": rd["payout"],
                "cost": round(cost, 2),
                "net": round(rd["payout"] - cost, 2),
            })
            cur = []
    history.reverse()  # 新→旧

    current = None
    if cur:
        last = cur[-1]
        k = _mart_layer(last["multiple"])
        nk = k + 1
        next_mult = last["multiple"] * 2
        next_per = MART_BASE * next_mult
        next_total = next_per * MART_SCORES
        next_net = round(next_per * MART_ODDS - _mart_cost(nk), 2)
        current = {
            "layer": k,
            "multiple": last["multiple"],
            "cumLoss": round(_mart_cost(k), 2),
            "rounds": cur,
            "nextLayer": nk,
            "nextMultiple": next_mult,
            "nextPerScore": round(next_per, 2),
            "nextTotal": round(next_total, 2),
            "nextNetIfHit": next_net,
        }
    return {
        "baseUnit": MART_BASE,
        "scoresPerRound": MART_SCORES,
        "assumedOdds": MART_ODDS,
        "current": current,
        "history": history,
    }


def reindex(out_dir):
    out_dir = Path(out_dir)
    days = []
    for f in out_dir.glob("*.json"):
        if f.name == "index.json":
            continue
        try:
            r = load(f)
        except Exception:
            continue
        if not r.get("date"):
            continue
        days.append(r)

    days.sort(key=lambda r: r["date"], reverse=True)

    index_days = [{
        "date": r["date"],
        "weekday": r.get("weekday"),
        "status": r.get("status", "open"),
        "hasReport": bool(r.get("hasReport")),
        "dayProfit": r.get("dayProfit"),
    } for r in days]

    report_dates = [r["date"] for r in days if r.get("hasReport")]

    settled = sorted([r for r in days if r.get("status") == "settled"], key=lambda r: r["date"])
    series = [{"date": r["date"], "profit": r.get("dayProfit") or 0} for r in settled]
    cumulative = round(sum(s["profit"] for s in series), 2)

    total_stake = round(sum(float(r.get("dayStake") or 0) for r in settled), 2)
    all_tickets = [t for r in settled for t in (r.get("tickets") or [])]
    total_tickets = len(all_tickets)
    win_tickets = sum(1 for t in all_tickets if t.get("status") == "win")

    martingale = compute_martingale(settled)

    index = {
        "updatedAt": None,
        "days": index_days,
        "reportDates": report_dates,
        "cumulativeProfit": cumulative,
        "totalStake": total_stake,
        "totalTickets": total_tickets,
        "winTickets": win_tickets,
        "profitSeries": series,
        "martingale": martingale,
    }
    dump(out_dir / "index.json", index)
    mtxt = ""
    if martingale:
        cur = martingale.get("current")
        nh = len(martingale.get("history") or [])
        mtxt = f", 叠层 往期{nh}轮" + (f"/进行中第{cur['layer']}层(已亏{cur['cumLoss']:g}, 下一层{cur['nextTotal']:g})" if cur else "")
    print(f"[export] index -> {out_dir / 'index.json'}  ({len(days)} 天/{len(report_dates)} 有报告, 累计 {cumulative:+g}{mtxt})")


def cmd_reindex(args):
    reindex(Path(args.site_data))


def main():
    ap = argparse.ArgumentParser(description="导出收益仪表盘数据 data/<日期>.json + index.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("day", help="登记当天有报告(open)")
    p.add_argument("--analysis", help="可选，取 meta.date / risk_note")
    p.add_argument("--date", help="日期 YYYY-MM-DD（无 analysis 时必填）")
    p.add_argument("--site-data", required=True)
    p.set_defaults(func=cmd_day)

    p = sub.add_parser("settle", help="retro.json -> 我买的票 + 盈亏(settled)")
    p.add_argument("--retro", required=True)
    p.add_argument("--date", help="覆盖被结算日期（默认读 retro.reviewed_run）")
    p.add_argument("--site-data", required=True)
    p.set_defaults(func=cmd_settle)

    p = sub.add_parser("reindex", help="重建 index.json")
    p.add_argument("--site-data", required=True)
    p.set_defaults(func=cmd_reindex)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
