#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape_zhipin.py — 通过 web-access 的 CDP Proxy(localhost:3456)抓 BOSS直聘 岗位详情。

选择器经真实运行验证(见 references/zhipin-site-notes.md),抓取层确定性、轻量。
输入是 UTF-8 的 config.json(中文经文件读入,避开 Windows 命令行参数编码问题):

    {"keywords": ["AI Agent开发工程师"], "city": "100010000", "count": 35,
     "out": "jobs.json", "delay": 2.5,
     "extra_params": {"experience": "105", "degree": "203"},
     "proxy": "http://localhost:3456", "max_pages": 5}

extra_params: 原样追加到搜索 URL 的额外参数(薪资/经验/学历筛选、精确城市等)。
取值是 BOSS 的内部编码,不要凭记忆猜——在 GUI 里勾好筛选,从地址栏复制真实 URL,
把 query/city 之外的参数搬进来(见 references/zhipin-site-notes.md)。

用法:  python scrape_zhipin.py config.json
前置:  web-access 的 proxy 已 ready(先跑它的 check-deps.mjs),且用户 Chrome 已登录 BOSS。

若列表恒为 0 或详情字段恒空,多半是 BOSS 改版导致选择器失效——
回退到 web-access 自适应驱动(像人一样浏览),并据实更新本脚本与站点笔记。
"""
import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request

PROXY = os.environ.get("WEB_ACCESS_PROXY", "http://localhost:3456")


def api_get(path, timeout=30):
    with urllib.request.urlopen(PROXY + path, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def check_proxy():
    """启动时检查 CDP proxy 是否可达。"""
    try:
        api_get("/targets", timeout=5)
        print("[ok] CDP proxy 已连接", flush=True)
        return True
    except Exception as e:
        print(f"[error] CDP proxy 不可达 ({PROXY}): {e}", flush=True)
        print("  请先用 web-access 的 check-deps.mjs 确认 proxy 已启动。", flush=True)
        return False


def api_eval(target, js):
    data = js.encode("utf-8")
    req = urllib.request.Request(f"{PROXY}/eval?target={target}", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", "replace")
    obj = json.loads(raw)
    if "value" not in obj:
        raise RuntimeError(f"eval error: {raw[:200]}")
    return json.loads(obj["value"]) if obj["value"].strip().startswith(("{", "[")) else obj["value"]


def new_tab(url):
    enc = urllib.parse.quote(url, safe="")
    return json.loads(api_get(f"/new?url={enc}"))["targetId"]


def close_tab(target):
    try:
        api_get(f"/close?target={target}")
    except Exception:
        pass


def job_key(url):
    """去重用的岗位标识:取 /job_detail/<id>。同一岗位经不同入口访问时
    URL 里的 ?securityId= 等会话参数不同,按完整 URL 去重会把同一岗位抓成多条、
    虚增样本。访问时仍用原始完整 URL(带会话参数才稳定打得开)。"""
    m = re.search(r"/job_detail/([^./?#]+)", url or "")
    return m.group(1) if m else (url or "").split("?")[0]


LIST_JS = """
JSON.stringify([...document.querySelectorAll("a[href*=job_detail]")]
  .map(a=>a.href).filter((v,i,arr)=>arr.indexOf(v)===i))
"""

# 详情页提取。公司名/行业取自 .sider-company(本岗位真实公司);
# 注意:页面右侧"相似职位"也有 .company-name,不能用它,否则抓错公司。
DETAIL_JS = r"""
(()=>{const t=s=>{const e=document.querySelector(s);return e?e.innerText.trim():""};
const jd=(document.querySelector(".job-sec-text")||{}).innerText||"";
let cname="",cinfo="";
const sc=document.querySelector(".sider-company");
if(sc){
  const ci=sc.querySelector(".company-info");
  cname=ci?ci.innerText.trim():"";
  let raw=sc.innerText.replace(/\s+/g," ").trim()
    .replace("公司基本信息","").replace("查看全部职位","");
  cinfo=raw.split(" ").filter(x=>x&&x!==cname).join(" · ");
}
const uniq=sel=>[...new Set([...document.querySelectorAll(sel)]
  .map(e=>e.innerText.trim()).filter(Boolean))].slice(0,15);
return JSON.stringify({
  name:t("h1").replace(/\s+\d.*$/,"").trim(),
  salary:(t(".salary")||t(".job-banner .salary")),
  city:t(".text-city"), exp:t(".text-experiece"), degree:t(".text-degree"),
  company:cname,
  company_info:cinfo,
  benefits:uniq(".job-tags span"),
  skills:uniq(".job-keyword-list li"),
  hr_active:t(".boss-active-time"),
  jd:jd,
  sec:/安全验证|验证码|滑块/.test(document.body.innerText.slice(0,3000))
});})()
"""

REQ_MARKERS = ["任职资格", "任职要求", "岗位要求", "任职条件", "职位要求", "我们希望你"]
BONUS_MARKERS = ["加分项", "以下条件优先", "具备以下", "满足以下", "优先考虑"]
# 加分项之后常跟"福利/我们提供"等非要求内容,截断掉
BENEFIT_MARKERS = ["我们提供", "我们能提供", "我们将提供", "我们为你提供", "我们的福利",
                   "福利待遇", "薪资福利", "公司福利", "福利:", "福利：", "加入我们",
                   "工作地点", "上班时间", "办公地点"]


def split_jd(jd):
    """把 BOSS 详情里"职责+要求"合并的一段切成 (responsibilities, requirements, bonus)。"""
    req_idx = min([jd.find(m) for m in REQ_MARKERS if jd.find(m) >= 0] or [-1])
    if req_idx < 0:
        return jd.strip(), "", ""
    resp = jd[:req_idx]
    rest = jd[req_idx:]
    # 去职责标题(兼容 "岗位职责："、"【岗位职责】"、"一、岗位职责" 等)
    resp = re.sub(r"^.*?[【\[]?岗位职责[】\]：:]*\s*", "", resp, count=1, flags=re.S).strip() or resp.strip()
    # 去切分点前残留的不完整行(如末尾单独的 "[" "【" "二、" "2." 等)
    resp = re.sub(r'\n\s*[\[【]?\s*[一二三四五六七八九十\d]*[、.]*\s*$', '', resp).strip()
    # 去要求标题(如 "[任职要求]"、"任职要求："、"【岗位要求】" 等)
    _req_hdr = '|'.join(re.escape(m) for m in REQ_MARKERS)
    rest = re.sub(rf'^[【\[]*(?:{_req_hdr})[】\]：:]*\s*', '', rest, count=1)
    bonus_idx = min([rest.find(m) for m in BONUS_MARKERS if rest.find(m) > 0] or [-1])
    if bonus_idx > 0:
        req, bonus = rest[:bonus_idx].strip(), rest[bonus_idx:].strip()
    else:
        req, bonus = rest.strip(), ""
    if bonus:
        cut = min([bonus.find(m) for m in BENEFIT_MARKERS if bonus.find(m) > 0] or [-1])
        if cut > 0:
            bonus = bonus[:cut].strip()
    return resp, req, bonus


SEC_CHECK_JS = r"""
/安全验证|验证码|滑块/.test(document.body.innerText.slice(0,3000)) ? "SEC" : "OK"
"""


def collect_hrefs_page(stid):
    """从当前已打开的搜索结果页提取详情链接,轮询等待渲染。"""
    for attempt in range(8):
        time.sleep(2.5)
        try:
            sec = api_eval(stid, SEC_CHECK_JS)
            if sec == "SEC":
                print("  !! 搜索页命中安全验证,请在 Chrome 中手动通过后重跑。", flush=True)
                return "SEC"
        except Exception:
            pass
        api_get(f"/scroll?target={stid}&y=1200")
        try:
            hrefs = api_eval(stid, LIST_JS)
        except Exception:
            hrefs = []
        if hrefs:
            return hrefs
        if attempt >= 3:
            print(f"    渲染等待中... (第{attempt+1}次)", flush=True)
    return []


def scrape_keyword(keyword, city, count, delay, seen_urls=None, out_path=None,
                   existing_jobs=None, extra_params=None, max_pages=5):
    """抓单个关键词,返回 (job 列表, 是否命中安全验证)。支持翻页、断点续抓、增量保存。"""
    if seen_urls is None:
        seen_urls = set()
    if existing_jobs is None:
        existing_jobs = []
    params = {"query": keyword, "city": str(city)}
    if extra_params:
        params.update({k: str(v) for k, v in extra_params.items()})
    base_url = ("https://www.zhipin.com/web/geek/jobs?"
                + urllib.parse.urlencode(params, quote_via=urllib.parse.quote))

    all_hrefs = []
    hit_sec = False
    for page in range(1, max_pages + 1):
        search_url = base_url if page == 1 else f"{base_url}&page={page}"
        print(f"[search] {keyword} @ {city} 第{page}页", flush=True)
        try:
            stid = new_tab(search_url)
        except Exception as e:
            print(f"  打开搜索页失败: {e}", flush=True)
            break
        hrefs = collect_hrefs_page(stid)
        close_tab(stid)
        if hrefs == "SEC":
            hit_sec = True
            break
        if not hrefs:
            print(f"  第{page}页无结果,停止翻页", flush=True)
            break
        new_hrefs = [h for h in hrefs if job_key(h) not in seen_urls]
        all_hrefs.extend(new_hrefs)
        print(f"  第{page}页拿到 {len(hrefs)} 个链接,去重后新增 {len(new_hrefs)} 个", flush=True)
        if len(all_hrefs) >= count:
            break
        if len(new_hrefs) == 0:
            print(f"  本页全部重复,停止翻页", flush=True)
            break
        time.sleep(delay)

    if hit_sec:
        return [], True

    all_hrefs = all_hrefs[:count]
    print(f"  共收集 {len(all_hrefs)} 个待抓详情链接", flush=True)
    if not all_hrefs:
        return [], False

    jobs = []
    skip_count = 0
    for i, href in enumerate(all_hrefs):
        if job_key(href) in seen_urls:
            continue
        print(f"  ({i+1}/{len(all_hrefs)}) {href}", flush=True)
        try:
            dtid = new_tab(href)
        except Exception as e:
            print(f"    打开详情页失败: {e}", flush=True)
            skip_count += 1
            continue
        time.sleep(delay)
        d = None
        for attempt in range(3):
            try:
                d = api_eval(dtid, DETAIL_JS)
                break
            except Exception as e:
                if attempt < 2:
                    print(f"    第{attempt+1}次提取失败,重试中: {e}", flush=True)
                    time.sleep(delay)
                else:
                    print(f"    跳过(3次重试均失败): {e}", flush=True)
        if d is None:
            close_tab(dtid)
            skip_count += 1
            continue
        if d.get("sec"):
            print("    !! 命中安全验证,请在 Chrome 中手动通过后重跑。已抓到的先保存。", flush=True)
            close_tab(dtid)
            hit_sec = True
            break
        if not d.get("jd"):
            print("    跳过(无职责正文)", flush=True)
            close_tab(dtid)
            skip_count += 1
            continue
        resp, req, bonus = split_jd(d["jd"])
        jobs.append({
            "keyword": keyword,
            "title": d.get("name") or keyword,
            "company": d.get("company", ""),
            "company_info": d.get("company_info", ""),
            "city": d.get("city", ""),
            "salary_raw": d.get("salary", ""),
            "experience": d.get("exp", ""),
            "education": d.get("degree", ""),
            "tags": d.get("skills", []),
            "benefits": d.get("benefits", []),
            "hr_active": d.get("hr_active", ""),
            "responsibilities_raw": resp,
            "requirements_raw": req,
            "bonus_raw": bonus,
            "detail_url": href,
        })
        seen_urls.add(job_key(href))
        close_tab(dtid)
        if out_path and len(jobs) % 5 == 0:
            _incremental_save(out_path, existing_jobs + jobs)
            print(f"    [save] 增量保存 {len(existing_jobs) + len(jobs)} 个岗位", flush=True)
    if skip_count:
        print(f"  本轮跳过 {skip_count} 个详情页", flush=True)
    return jobs, hit_sec


def _incremental_save(path, all_jobs):
    """增量保存到磁盘,中途崩溃也不丢数据。按岗位 ID 去重。"""
    deduped = []
    keys_seen = set()
    for j in all_jobs:
        k = job_key(j.get("detail_url", ""))
        if k and k in keys_seen:
            continue
        keys_seen.add(k)
        deduped.append(j)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", help="UTF-8 的 config.json: {keywords:[...], city, count, out}")
    args = ap.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    keywords = cfg["keywords"]
    city = str(cfg.get("city", "100010000"))
    count = int(cfg.get("count", 35))
    out = cfg.get("out", "jobs.json")
    delay = float(cfg.get("delay", 2.5))
    resume = cfg.get("resume", True)
    extra_params = cfg.get("extra_params") or {}
    max_pages = int(cfg.get("max_pages", 5))
    if cfg.get("proxy"):
        global PROXY
        PROXY = cfg["proxy"]

    if not check_proxy():
        return

    existing_jobs = []
    seen_urls = set()
    if resume and os.path.exists(out):
        try:
            with open(out, "r", encoding="utf-8") as f:
                existing_jobs = json.load(f)
            seen_urls = {job_key(j["detail_url"]) for j in existing_jobs if j.get("detail_url")}
            print(f"[resume] 已有 {len(existing_jobs)} 个岗位({len(seen_urls)} 个唯一ID),增量抓取", flush=True)
        except Exception:
            existing_jobs = []

    all_jobs = list(existing_jobs)
    for kw in keywords:
        new_jobs, hit_sec = scrape_keyword(kw, city, count, delay, seen_urls,
                                           out_path=out, existing_jobs=all_jobs,
                                           extra_params=extra_params, max_pages=max_pages)
        all_jobs.extend(new_jobs)
        for j in new_jobs:
            seen_urls.add(job_key(j.get("detail_url", "")))
        if hit_sec:
            # 风控是账号/IP 级的,换关键词硬试只会越触发越严。停下保数据,等用户过验证后重跑续抓。
            print("[abort] 命中安全验证,停止剩余关键词。请在 Chrome 手动通过验证后重跑(已抓数据会自动续上)。", flush=True)
            break

    deduped = []
    keys_seen = set()
    for j in all_jobs:
        k = job_key(j.get("detail_url", ""))
        if k and k in keys_seen:
            continue
        keys_seen.add(k)
        deduped.append(j)
    all_jobs = deduped

    if not all_jobs:
        print(f"[warn] 未抓到任何岗位,保留原 {out} 不覆盖。可能加载慢或被风控,稍后重试。", flush=True)
        return
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)
    n_new = len(all_jobs) - len(existing_jobs)
    print(f"[done] 共 {len(all_jobs)} 个岗位(本次新增 {n_new}) -> {out}", flush=True)


if __name__ == "__main__":
    main()
