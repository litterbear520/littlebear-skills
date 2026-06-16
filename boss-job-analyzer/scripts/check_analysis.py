#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_analysis.py — 校验第 2 步产出的 analysis.json 标注质量。

统计质量取决于标注质量:漏标的岗位不计入占比(分布失真),归一化不一致的标签
会被脚本当成不同项(占比被摊薄)。这两类问题人眼很难从最终报告里看出来,
所以在生成报告前用本脚本做一次确定性自检。

用法:  PYTHONUTF8=1 python check_analysis.py jobs.json analysis.json

检查项:
  1. URL 对齐    per_job 里的 detail_url 必须能在 jobs.json 中找到
  2. 覆盖率      jobs.json 里每个岗位都应有对应标注,列出漏标岗位
  3. 归一化疑似  仅大小写/空格/连字符不同的标签视为同一概念的变体(如
                 LangChain / langchain / Lang Chain),应合并为一个写法
  4. 空标注      tech/langs/duties 全空的岗位(可能是漏读了 JD)
  5. insights    条数(建议 6-10)与 pct 取值范围(0-100)

发现问题退出码为 1,全部通过为 0。
"""
import json
import re
import sys
from collections import defaultdict


def norm_key(label):
    """归一化指纹:去空格/连字符/下划线/点 + casefold。指纹相同而写法不同 = 疑似变体。"""
    return re.sub(r"[\s\-_./]+", "", str(label)).casefold()


def canon_url(url):
    """与 build_report.py 一致的 URL 归一:取 /job_detail/<id> 的岗位 ID,
    避免 ?securityId= 等会话参数导致对不上号。"""
    url = (url or "").strip()
    m = re.search(r"/job_detail/([^./?#]+)", url)
    return m.group(1) if m else url.split("?")[0].split("#")[0]


def main():
    if len(sys.argv) != 3:
        sys.exit("用法: python check_analysis.py jobs.json analysis.json")
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        jobs = json.load(f)
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        analysis = json.load(f)

    per_job = analysis.get("per_job", [])
    insights = analysis.get("insights", [])
    job_keys = {canon_url(j.get("detail_url")) for j in jobs if j.get("detail_url")}
    title_by_key = {canon_url(j.get("detail_url")): j.get("title", "?") for j in jobs}
    issues = 0

    # 1. URL 对齐(按岗位 ID 归一,与 build_report.py 同口径)
    tagged_keys = [canon_url(p.get("detail_url")) for p in per_job]
    unknown = [p.get("detail_url", "") for p, k in zip(per_job, tagged_keys)
               if k and k not in job_keys]
    dup = {k for k in tagged_keys if tagged_keys.count(k) > 1}
    if unknown:
        issues += 1
        print(f"[问题] {len(unknown)} 条标注的 detail_url 在 jobs.json 里找不到(对不上号,不会计入统计):")
        for u in unknown[:5]:
            print(f"    {u}")
    if dup:
        issues += 1
        print(f"[问题] {len(dup)} 个岗位被重复标注(后者覆盖前者):")
        for k in list(dup)[:5]:
            print(f"    {title_by_key.get(k, '?')}  {k}")

    # 2. 覆盖率
    covered = {k for k in tagged_keys if k in job_keys}
    missing = [k for k in job_keys if k not in covered]
    cov = len(covered) / len(job_keys) * 100 if job_keys else 0
    print(f"[覆盖] {len(covered)}/{len(job_keys)} 个岗位已标注 ({cov:.0f}%)")
    if missing:
        issues += 1
        print(f"[问题] 以下 {len(missing)} 个岗位漏标(不会计入技能/语言/职责占比,需补标):")
        for k in missing[:10]:
            print(f"    {title_by_key.get(k, '?')}  {k}")
        if len(missing) > 10:
            print(f"    ... 还有 {len(missing) - 10} 个")

    # 3. 归一化疑似变体
    for field in ("tech", "langs", "duties"):
        variants = defaultdict(set)
        for p in per_job:
            for label in p.get(field, []) or []:
                variants[norm_key(label)].add(str(label))
        suspect = {k: v for k, v in variants.items() if len(v) > 1}
        if suspect:
            issues += 1
            print(f"[问题] {field} 存在 {len(suspect)} 组疑似同义变体(会被当成不同项,占比被摊薄,请统一写法):")
            for v in list(suspect.values())[:8]:
                print(f"    {' / '.join(sorted(v))}")

    # 4. 空标注
    empty = [p for p in per_job
             if not (p.get("tech") or p.get("langs") or p.get("duties"))]
    if empty:
        issues += 1
        print(f"[问题] {len(empty)} 个岗位三类标签全空(确认是 JD 真没提,还是漏读了):")
        for p in empty[:5]:
            u = p.get("detail_url", "?")
            print(f"    {title_by_key.get(canon_url(u), '?')}  {u}")

    # 5. insights
    if insights:
        bad_pct = [i for i in insights
                   if not isinstance(i.get("pct"), (int, float)) or not 0 <= i["pct"] <= 100]
        if bad_pct:
            issues += 1
            print(f"[问题] {len(bad_pct)} 条洞察的 pct 缺失或超出 0-100")
        if not 6 <= len(insights) <= 10:
            print(f"[提示] 洞察共 {len(insights)} 条(建议 6-10 条,非硬性)")
    else:
        print("[提示] 没有 insights,报告第 5 维度会退化")

    if issues:
        print(f"\n共发现 {issues} 类问题。修正 analysis.json 后重跑本脚本,干净后再生成报告。")
        sys.exit(1)
    print("\n全部通过,可以生成报告。")


if __name__ == "__main__":
    main()
