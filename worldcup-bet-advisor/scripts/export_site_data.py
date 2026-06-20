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
import re
import sys
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


def settle_ticket(t, idx, date):
    legs, odds_product, have_all_odds = [], 1.0, True
    for leg in t.get("legs", []):
        o = leg.get("odds")
        leg_out = {"text": leg.get("text"), "odds": o, "hit": leg.get("hit")}
        # 票面结构（可选）：主队/客队/赛事编号/玩法类别/选择，有就带上
        for k in ("matchNo", "home", "away", "category", "pick"):
            if leg.get(k) is not None:
                leg_out[k] = leg.get(k)
        legs.append(leg_out)
        if o:
            odds_product *= float(o)
        else:
            have_all_odds = False

    hits = [leg.get("hit") for leg in t.get("legs", [])]
    if any(h is False for h in hits):
        status = "loss"
    elif any(h is None for h in hits):
        status = "pending"
    else:
        status = "win"

    combined = t.get("combined_odds")
    if combined is None and have_all_odds:
        combined = round(odds_product, 2)

    stake = float(t.get("stake", 0) or 0)
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

    index = {
        "updatedAt": None,
        "days": index_days,
        "reportDates": report_dates,
        "cumulativeProfit": cumulative,
        "totalStake": total_stake,
        "totalTickets": total_tickets,
        "winTickets": win_tickets,
        "profitSeries": series,
    }
    dump(out_dir / "index.json", index)
    print(f"[export] index -> {out_dir / 'index.json'}  ({len(days)} 天/{len(report_dates)} 有报告, 累计 {cumulative:+g})")


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
