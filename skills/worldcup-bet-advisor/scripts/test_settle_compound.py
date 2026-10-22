#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复式/系统过关（M场N关）部分中奖结算的单测。无需 pytest：python3 scripts/test_settle_compound.py。

口径：按关数 N 枚举所有 N-注（展开每场复式选项），只累加「全中」注的回款；
每注本金 = 总本金 / 总注数；profit = 回款 - 总本金。
两张真实票（2026-06-27 周六067-072 终场）作为黄金用例。
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_site_data import settle_ticket  # noqa: E402

# 票1：4场2关·复式·9注·18元。终场 067=2:1 068=0:2 069=0:0 071=3:3
TICKET1 = {
    "tier": "自选", "type": "4场2关", "stake": 18, "multiple": 1, "pass": 2,
    "legs": [
        {"matchNo": "周六067", "home": "克罗地亚", "away": "加纳", "category": "比分",
         "pick": "0:0@7.00 / 1:1@5.50", "text": "克罗地亚 vs 加纳 · 比分 0:0/1:1 · 终2:1 未中",
         "options": [{"odds": 7.0, "hit": False}, {"odds": 5.5, "hit": False}]},
        {"matchNo": "周六068", "home": "巴拿马", "away": "英格兰", "category": "比分",
         "pick": "0:2", "odds": 5.8, "text": "巴拿马 vs 英格兰 · 比分 0:2 · 终0:2 中",
         "options": [{"odds": 5.8, "hit": True}]},
        {"matchNo": "周六069", "home": "哥伦比亚", "away": "葡萄牙", "category": "比分",
         "pick": "1:1", "odds": 6.1, "text": "哥伦比亚 vs 葡萄牙 · 比分 1:1 · 终0:0 未中",
         "options": [{"odds": 6.1, "hit": False}]},
        {"matchNo": "周六071", "home": "阿尔及利亚", "away": "奥地利", "category": "胜平负",
         "pick": "平", "odds": 1.94, "text": "阿尔及利亚 vs 奥地利 · 平 · 终3:3(平) 中",
         "options": [{"odds": 1.94, "hit": True}]},
    ],
}

# 票2：6场2关·复式·20注·40元。067=2:1 068=0:2 069=0:0 070=3:1 071=3:3 072=1:3
TICKET2 = {
    "tier": "自选", "type": "6场2关", "stake": 40, "multiple": 1, "pass": 2,
    "legs": [
        {"matchNo": "周六067", "home": "克罗地亚", "away": "加纳", "category": "胜平负",
         "pick": "胜", "odds": 1.66, "text": "克罗地亚 vs 加纳 · 胜 · 终2:1(主胜) 中",
         "options": [{"odds": 1.66, "hit": True}]},
        {"matchNo": "周六068", "home": "巴拿马", "away": "英格兰", "category": "让球·受让2球",
         "pick": "负", "odds": 1.94, "text": "巴拿马 vs 英格兰 · 受让2球 负 · 终0:2→让2:2(平) 未中",
         "options": [{"odds": 1.94, "hit": False}]},
        {"matchNo": "周六069", "home": "哥伦比亚", "away": "葡萄牙", "category": "胜平负",
         "pick": "负", "odds": 1.75, "text": "哥伦比亚 vs 葡萄牙 · 负 · 终0:0(平) 未中",
         "options": [{"odds": 1.75, "hit": False}]},
        {"matchNo": "周六070", "home": "刚果（金）", "away": "乌兹别克斯坦", "category": "胜平负",
         "pick": "胜", "odds": 1.46, "text": "刚果（金） vs 乌兹别克斯坦 · 胜 · 终3:1(主胜) 中",
         "options": [{"odds": 1.46, "hit": True}]},
        {"matchNo": "周六071", "home": "阿尔及利亚", "away": "奥地利", "category": "胜平负",
         "pick": "负", "odds": 2.77, "text": "阿尔及利亚 vs 奥地利 · 负 · 终3:3(平) 未中",
         "options": [{"odds": 2.77, "hit": False}]},
        {"matchNo": "周六072", "home": "约旦", "away": "阿根廷", "category": "让球·受让2球",
         "pick": "平@3.92 / 负@2.02 → 让平中", "text": "约旦 vs 阿根廷 · 受让2球 平/负 · 终1:3→让3:3(平) 中",
         "options": [{"odds": 3.92, "hit": True}, {"odds": 2.02, "hit": False}]},
    ],
}


def approx(a, b, tol=0.01):
    return abs(a - b) <= tol


def main():
    fails = []

    t1 = settle_ticket(TICKET1, 0, "2026-06-27")
    # 9 注，仅 (068 0:2)×(071 平) 全中 = 2 × 5.8 × 1.94 = 22.504
    if t1.get("combos") != 9:
        fails.append(f"票1 combos 应为 9，实际 {t1.get('combos')}")
    if not approx(t1["payout"], 22.5):
        fails.append(f"票1 payout 应 ≈22.50，实际 {t1['payout']}")
    if not approx(t1["profit"], 4.5):
        fails.append(f"票1 profit 应 ≈+4.50，实际 {t1['profit']}")
    if t1["status"] != "win":
        fails.append(f"票1 status 应 win，实际 {t1['status']}")
    hit1 = sum(1 for l in t1["legs"] if l.get("hit") is True)
    if hit1 != 2:
        fails.append(f"票1 命中场数应 2，实际 {hit1}")

    t2 = settle_ticket(TICKET2, 1, "2026-06-27")
    # 20 注，中 (067胜×070胜)=4.8472 + (067胜×072平)=13.0144 + (070胜×072平)=11.4464 = 29.308
    if t2.get("combos") != 20:
        fails.append(f"票2 combos 应为 20，实际 {t2.get('combos')}")
    if not approx(t2["payout"], 29.31):
        fails.append(f"票2 payout 应 ≈29.31，实际 {t2['payout']}")
    if not approx(t2["profit"], -10.69):
        fails.append(f"票2 profit 应 ≈-10.69，实际 {t2['profit']}")
    if t2["status"] != "loss":
        fails.append(f"票2 status 应 loss，实际 {t2['status']}")
    hit2 = sum(1 for l in t2["legs"] if l.get("hit") is True)
    if hit2 != 3:
        fails.append(f"票2 命中场数应 3，实际 {hit2}")

    # 合计：本金 58、回款 51.81、净 -6.19
    total_profit = round(t1["profit"] + t2["profit"], 2)
    if not approx(total_profit, -6.19):
        fails.append(f"两票合计净应 ≈-6.19，实际 {total_profit}")

    # 脏数据防御：关数 pass 必须 1<=pass<=场数，否则报错而不是静默把脏票当全输
    for bad_pass, why in [(9, "pass>场数"), (0, "pass=0"), (-1, "pass<0")]:
        bad = copy.deepcopy(TICKET1)
        bad["pass"] = bad_pass  # TICKET1 只有 4 场
        try:
            settle_ticket(bad, 99, "2026-06-27")
            fails.append(f"{why} 应抛 ValueError，却被静默接受")
        except ValueError:
            pass
        except Exception as e:  # noqa: BLE001
            fails.append(f"{why} 应抛 ValueError，却抛了 {type(e).__name__}")

    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("PASS  票1 +4.50 / 票2 -10.69 / 合计 -6.19")
    print(f"      票1: combos={t1['combos']} payout={t1['payout']} profit={t1['profit']} status={t1['status']}")
    print(f"      票2: combos={t2['combos']} payout={t2['payout']} profit={t2['profit']} status={t2['status']}")


if __name__ == "__main__":
    main()
