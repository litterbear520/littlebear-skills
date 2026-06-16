#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_report.py — 把抓取到的 BOSS直聘 岗位数据(jobs.json)分析成一个自包含 HTML 报告。

纯标准库,无三方依赖。所有统计都在这里确定性完成,保证可复现。
用法:
    python build_report.py path/to/jobs.json --out path/to/report.html

jobs.json 的字段约定见技能 SKILL.md。要扩展识别的词,改下面三张词典即可。
"""

import argparse
import datetime
import html
import json
import math
import re
import statistics
import sys
from collections import Counter, OrderedDict

# ---------------------------------------------------------------------------
# 词典:canonical 展示名 -> 匹配用的正则别名列表(大小写不敏感)。
# 想识别更多技术,往这里加就行,不用动后面的逻辑。
# ---------------------------------------------------------------------------
TECH_TERMS = OrderedDict([
    # --- AI Agent / 智能体框架 ---
    ("LangChain",        [r"langchain"]),
    ("LangGraph",        [r"langgraph"]),
    ("LlamaIndex",       [r"llama[\s_-]?index"]),
    ("AutoGen",          [r"autogen"]),
    ("CrewAI",           [r"crew\s?ai"]),
    ("Semantic Kernel",  [r"semantic kernel"]),
    ("Dify",             [r"\bdify\b"]),
    ("Coze/扣子",         [r"\bcoze\b", r"扣子"]),
    ("FastGPT",          [r"fastgpt"]),
    ("n8n/工作流",        [r"\bn8n\b", r"工作流编排", r"workflow"]),
    # --- 核心 AI 概念 ---
    ("RAG",              [r"\brag\b", r"检索增强", r"graphrag"]),
    ("Agent/智能体",      [r"\bagent\b", r"智能体", r"多智能体", r"multi[\s-]?agent", r"agentic"]),
    ("MCP",              [r"\bmcp\b", r"model context protocol"]),
    ("A2A",              [r"\ba2a\b", r"agent[\s-]?to[\s-]?agent"]),
    ("Function Calling", [r"function[\s-]?call", r"工具调用", r"tool[\s-]?use", r"structured[\s-]?output"]),
    ("Prompt工程",        [r"prompt", r"提示词"]),
    ("微调/Fine-tune",    [r"fine[\s-]?tun", r"微调", r"\bsft\b", r"\blora\b", r"\bqlora\b",
                          r"\brlhf\b", r"\bdpo\b", r"\bgrpo\b", r"\bppo\b"]),
    ("模型评估/对齐",      [r"模型评估", r"评测", r"\beval\b", r"alignment", r"对齐", r"安全护栏", r"guardrail"]),
    # --- 向量 / 检索 ---
    ("向量数据库",         [r"向量数据库", r"向量库", r"\bmilvus\b", r"\bfaiss\b", r"\bpinecone\b",
                          r"\bchroma\b", r"\bqdrant\b", r"pgvector", r"\bweaviate\b"]),
    ("Embedding",        [r"embedding", r"向量化", r"文本向量"]),
    ("Elasticsearch",    [r"elasticsearch", r"\bes\b.*搜索", r"\belastic\b"]),
    # --- 模型 / 推理 ---
    ("Transformer",      [r"transformer"]),
    ("vLLM",             [r"\bvllm\b"]),
    ("Ollama",           [r"ollama"]),
    ("TensorRT",         [r"tensorrt", r"\btrt\b"]),
    ("ONNX",             [r"\bonnx\b"]),
    ("大模型/LLM",        [r"\bllm\b", r"大模型", r"大语言模型", r"\bgpt\b", r"通义", r"文心", r"\bqwen\b",
                          r"\bclaude\b", r"deepseek", r"\bglm\b", r"gemini", r"llama"]),
    ("多模态",            [r"多模态", r"multi[\s-]?modal", r"\bvlm\b"]),
    ("知识图谱",          [r"知识图谱", r"knowledge graph", r"\bneo4j\b"]),
    # --- 深度学习框架 ---
    ("PyTorch",          [r"pytorch", r"\btorch\b"]),
    ("TensorFlow",       [r"tensorflow"]),
    ("HuggingFace",      [r"hugging\s?face", r"\bhf\b.*模型", r"transformers库"]),
    # --- MLOps / 工程化 ---
    ("MLOps",            [r"mlops", r"\bmlflow\b", r"\bwandb\b", r"模型上线", r"模型服务化"]),
    ("Ray",              [r"\bray\b.*分布", r"ray\s?serve"]),
    # --- 基础设施 ---
    ("微服务",            [r"微服务", r"micro\s?service", r"spring\s?cloud"]),
    ("Docker/K8s",       [r"docker", r"kubernetes", r"\bk8s\b", r"容器化"]),
    ("Redis",            [r"\bredis\b"]),
    ("Kafka",            [r"\bkafka\b", r"\brabbitmq\b", r"消息队列"]),
    ("MySQL",            [r"\bmysql\b"]),
    ("PostgreSQL",       [r"postgres", r"\bpg\b.*数据库"]),
    ("MongoDB",          [r"mongodb", r"\bmongo\b"]),
    ("Spark/Flink",      [r"\bspark\b", r"\bflink\b", r"大数据"]),
    # --- 前端 ---
    ("React",            [r"\breact\b"]),
    ("Vue",              [r"\bvue\b"]),
    ("Next.js",          [r"next\.?js", r"\bnuxt\b"]),
])

# 编程语言:短名字容易误伤,统一加非字母边界;C/R 只认带"语言"或明确写法。
LANG_TERMS = OrderedDict([
    ("Python",     [r"(?<![A-Za-z])python(?![A-Za-z])"]),
    ("Java",       [r"(?<![A-Za-z])java(?!script)(?![A-Za-z])"]),
    ("Go",         [r"(?<![A-Za-z])go(?:lang)?(?![A-Za-z])", r"go语言"]),
    ("C++",        [r"c\+\+"]),
    ("C#",         [r"c#"]),
    ("JavaScript", [r"javascript", r"(?<![A-Za-z])js(?![A-Za-z])"]),
    ("TypeScript", [r"typescript", r"(?<![A-Za-z])ts(?![A-Za-z])"]),
    ("Rust",       [r"(?<![A-Za-z])rust(?![A-Za-z])"]),
    ("C语言",       [r"c语言", r"(?<![A-Za-z+#])c\s*/\s*c\+\+"]),
    ("PHP",        [r"(?<![A-Za-z])php(?![A-Za-z])"]),
    ("Scala",      [r"(?<![A-Za-z])scala(?![A-Za-z])"]),
    ("Kotlin",     [r"kotlin"]),
    ("Swift",      [r"(?<![A-Za-z])swift(?![A-Za-z])"]),
    ("Dart",       [r"(?<![A-Za-z])dart(?![A-Za-z])", r"flutter"]),
    ("Ruby",       [r"(?<![A-Za-z])ruby(?![A-Za-z])"]),
    ("Shell",      [r"(?<![A-Za-z])shell(?![A-Za-z])", r"\bbash\b"]),
    ("SQL",        [r"(?<![A-Za-z])sql(?![A-Za-z])"]),
])

# 职责高频任务词(主要在 responsibilities 段里数)
DUTY_TERMS = [
    "设计", "开发", "部署", "优化", "调优", "微调", "训练", "搭建", "落地", "评测",
    "测试", "维护", "数据处理", "数据清洗", "架构", "调研", "工程化", "迭代",
    "需求分析", "性能优化", "模型部署", "Prompt设计", "RAG", "Agent", "工作流编排",
    "对接", "集成", "上线", "产品化", "知识库", "数据标注", "模型评估", "安全",
    "API", "SDK", "文档", "Code Review",
]

# 加分项小标题的常见写法
BONUS_MARKERS = ["加分项", "加分", "优先", "以下条件优先", "nice to have", "bonus", "更佳", "者优先"]

# 洞察检测:细分词典,用于挖掘跨岗位共性规律(比 TECH_TERMS 更聚焦特定维度)
INSIGHT_GROUPS = OrderedDict([
    ("Agent 开发框架", OrderedDict([
        ("LangChain",        [r"langchain"]),
        ("LangGraph",        [r"langgraph"]),
        ("LlamaIndex",       [r"llama[\s_-]?index"]),
        ("AutoGen",          [r"autogen"]),
        ("CrewAI",           [r"crew\s?ai"]),
        ("Semantic Kernel",  [r"semantic kernel"]),
        ("Dify",             [r"\bdify\b"]),
    ])),
    ("AI 编程工具", OrderedDict([
        ("Claude Code",    [r"claude\s*code"]),
        ("Cursor",         [r"\bcursor\b"]),
        ("GitHub Copilot", [r"copilot"]),
        ("Windsurf",       [r"windsurf"]),
        ("Cline/Aider",    [r"\bcline\b", r"\baider\b"]),
    ])),
    ("大模型品牌偏好", OrderedDict([
        ("GPT/OpenAI",     [r"\bgpt\b", r"openai", r"chatgpt"]),
        ("Claude",         [r"\bclaude\b", r"anthropic"]),
        ("通义千问/Qwen",   [r"通义", r"千问", r"\bqwen\b"]),
        ("DeepSeek",       [r"deepseek"]),
        ("文心一言",        [r"文心"]),
        ("GLM/智谱",        [r"\bglm\b", r"chatglm", r"智谱"]),
        ("LLaMA",          [r"\bllama\b"]),
        ("Gemini",         [r"gemini"]),
    ])),
    ("实战经验信号", OrderedDict([
        ("落地/实战经验",    [r"落地经验", r"实际项目", r"项目落地", r"实战经验", r"工程化经验"]),
        ("生产环境上线",     [r"生产环境", r"上线经验"]),
        ("从0到1搭建",       [r"从0到1", r"从零到一"]),
        ("商业化/产品化",    [r"商业化", r"产品化", r"规模化"]),
    ])),
    ("热门应用场景", OrderedDict([
        ("智能客服/对话",    [r"客服", r"对话.*系统", r"聊天机器人", r"\bchatbot\b"]),
        ("知识库/问答",      [r"知识库", r"问答系统"]),
        ("搜索/推荐",        [r"搜索", r"推荐"]),
        ("金融",             [r"金融"]),
        ("数据分析/BI",      [r"数据分析", r"text2sql"]),
        ("医疗/健康",        [r"医疗", r"健康"]),
        ("电商",             [r"电商"]),
        ("办公自动化",       [r"办公.*自动", r"\brpa\b"]),
    ])),
    ("软技能要求", OrderedDict([
        ("跨团队协作",       [r"跨团队", r"跨部门", r"与产品.*协", r"与.*团队.*配合"]),
        ("学习能力",         [r"学习能力", r"快速学习", r"持续学习"]),
        ("沟通/表达",        [r"沟通能力", r"表达能力", r"沟通协调"]),
        ("自驱/主动性",      [r"自驱", r"自我驱动", r"主动性"]),
    ])),
])

# 对比系列(罕用,多关键词时)的暖色调色板
PALETTE = ["#C15F3C", "#7D7A5C", "#CC9B7A", "#9C6B4F", "#A8704F", "#6E6A50"]


# ---------------------------------------------------------------------------
# 解析辅助
# ---------------------------------------------------------------------------
def job_text(job):
    """一个岗位用于词频识别的全部文本。"""
    parts = [
        job.get("title", ""),
        job.get("responsibilities_raw", ""),
        job.get("requirements_raw", ""),
        job.get("bonus_raw", ""),
        " ".join(job.get("tags", []) or []),
    ]
    return "\n".join(p for p in parts if p)


def match_any(text, patterns):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def parse_salary(raw):
    """把 '25-45K·14薪' 解析成 (月薪中点(单位K), 年薪(万)). 解析不了返回 (None, None)."""
    if not raw:
        return None, None
    s = raw.replace("k", "K").replace("Ｋ", "K")
    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*K", s)
    if not m:
        single = re.search(r"(\d+(?:\.\d+)?)\s*K", s)
        if not single:
            return None, None
        lo = hi = float(single.group(1))
    else:
        lo, hi = float(m.group(1)), float(m.group(2))
    months_m = re.search(r"·?\s*(\d+(?:\.\d+)?)\s*薪", s)
    months = float(months_m.group(1)) if months_m else 12.0
    mid_monthly = (lo + hi) / 2.0          # 单位 K
    annual_wan = mid_monthly * months / 10.0   # 万元/年
    return round(mid_monthly, 1), round(annual_wan, 1)


def norm_education(raw):
    if not raw:
        return "未标注"
    for key in ["博士", "硕士", "本科", "大专", "高中", "中专"]:
        if key in raw:
            return key
    if "不限" in raw:
        return "学历不限"
    return raw.strip()[:6] or "未标注"


def norm_experience(raw):
    if not raw:
        return "未标注"
    raw = raw.strip()
    if "不限" in raw:
        return "经验不限"
    if "应届" in raw or "在校" in raw or "实习" in raw:
        return "应届/实习"
    for key in ["1年以内", "1-3年", "3-5年", "5-10年", "10年以上"]:
        if key in raw:
            return key
    return raw[:8]


EDU_ORDER = ["学历不限", "大专", "本科", "硕士", "博士", "中专", "高中", "未标注"]
EXP_ORDER = ["应届/实习", "经验不限", "1年以内", "1-3年", "3-5年", "5-10年", "10年以上", "未标注"]


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------
def doc_freq(jobs, term_dict_or_list, is_dict=True):
    """返回 Counter: term -> 提到该 term 的岗位数(文档频率)。"""
    c = Counter()
    for job in jobs:
        text = job_text(job)
        if is_dict:
            for name, pats in term_dict_or_list.items():
                if match_any(text, pats):
                    c[name] += 1
        else:
            for name in term_dict_or_list:
                if re.search(re.escape(name), text, re.IGNORECASE):
                    c[name] += 1
    return c


def cooccurrence(jobs, term_dict, top_n=10):
    """返回技术共现对 [(('A','B'), 共现岗位数, 占比)]，按频率降序。"""
    per_job = []
    for job in jobs:
        text = job_text(job)
        hits = [name for name, pats in term_dict.items() if match_any(text, pats)]
        per_job.append(set(hits))
    pairs = Counter()
    for hits in per_job:
        for a in hits:
            for b in hits:
                if a < b:
                    pairs[(a, b)] += 1
    total = len(jobs) or 1
    return [((a, b), cnt, cnt / total) for (a, b), cnt in pairs.most_common(top_n) if cnt >= 2]


def duty_freq(jobs):
    c = Counter()
    for job in jobs:
        text = (job.get("responsibilities_raw") or "") + "\n" + (job.get("title") or "")
        for name in DUTY_TERMS:
            if name in text:
                c[name] += 1
    return c


def collect_bonus(jobs):
    """汇总加分项原文条目(按行/分号切),返回 [(条目, 出现岗位数)] 粗略聚合。"""
    lines = []
    for job in jobs:
        b = (job.get("bonus_raw") or "").strip()
        if not b:
            continue
        for piece in re.split(r"[\n;；。]", b):
            piece = piece.strip(" ·•-、,，:：")
            if len(piece) >= 4:
                lines.append(piece)
    return Counter(lines)


def dist(jobs, fn, order):
    c = Counter(fn(j) for j in jobs)
    return [(k, c.get(k, 0)) for k in order if c.get(k, 0)] + \
           [(k, v) for k, v in c.items() if k not in order]


def salary_stats(jobs):
    monthly, annual = [], []
    for j in jobs:
        mm, aw = parse_salary(j.get("salary_raw", ""))
        if mm is not None:
            monthly.append(mm)
            annual.append(aw)
    if not monthly:
        return None
    return {
        "n": len(monthly),
        "median_monthly": round(statistics.median(monthly), 1),
        "median_annual": round(statistics.median(annual), 1),
        "min_monthly": min(monthly),
        "max_monthly": max(monthly),
        "monthly_values": monthly,
    }


def salary_histogram(values):
    names = ["<10K", "10-20K", "20-30K", "30-40K", "40-50K", "≥50K"]
    buckets = Counter()
    for v in values:
        if v < 10: buckets["<10K"] += 1
        elif v < 20: buckets["10-20K"] += 1
        elif v < 30: buckets["20-30K"] += 1
        elif v < 40: buckets["30-40K"] += 1
        elif v < 50: buckets["40-50K"] += 1
        else: buckets["≥50K"] += 1
    return [(n, buckets[n]) for n in names]


def salary_by_experience(jobs):
    """返回 [(经验档, 月薪中位K, 样本数)],按经验从浅到深。"""
    buckets = {}
    for j in jobs:
        mm, _ = parse_salary(j.get("salary_raw", ""))
        if mm is not None:
            buckets.setdefault(norm_experience(j.get("experience")), []).append(mm)
    rows = []
    for exp in EXP_ORDER:
        if exp in buckets:
            rows.append((exp, round(statistics.median(buckets[exp]), 1), len(buckets[exp])))
    return rows


def load_insights(path):
    """从外部 insights.json 加载 Claude 预生成的洞察。格式:
    [{"title": "...", "body": "...(可含<b>标签)", "pct": 数字}, ...]
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        result = []
        for item in items:
            if isinstance(item, dict) and "title" in item and "body" in item:
                result.append((
                    str(item["title"]),
                    str(item["body"]),
                    float(item.get("pct", 0)),
                ))
        if result:
            print(f"[insight] 已加载 {len(result)} 条 Claude 洞察 <- {path}", flush=True)
            return result
    except Exception as e:
        print(f"[warn] 加载 insights.json 失败: {e}", flush=True)
    return None


def regex_insights(jobs):
    """正则兜底:当 Claude 不可用时,用预定义词典做基础统计。"""
    total = len(jobs) or 1
    insights = []

    def count_per_term(term_dict):
        c = Counter()
        for j in jobs:
            text = job_text(j)
            for name, pats in term_dict.items():
                if match_any(text, pats):
                    c[name] += 1
        return c

    def group_hit_count(term_dict):
        return sum(1 for j in jobs
                   if any(match_any(job_text(j), pats) for pats in term_dict.values()))

    for group_name, term_dict in INSIGHT_GROUPS.items():
        gt = group_hit_count(term_dict)
        if gt < max(2, int(total * 0.05)):
            continue
        detail = count_per_term(term_dict)
        top = [(n, c) for n, c in detail.most_common(4) if c >= 2]
        if not top:
            continue
        pct_val = gt / total * 100
        parts = [f"<b>{esc(n)}</b>({c}岗, {c * 100 // total}%)" for n, c in top]
        body = (f"共 <b>{gt}</b> 个岗位({pct_val:.0f}%)涉及此类要求,"
                f"其中 {'、'.join(parts)}。")
        insights.append((group_name, body, pct_val))

    agent_fw_pats = INSIGHT_GROUPS.get("Agent 开发框架", OrderedDict())
    multi_fw = 0
    for j in jobs:
        text = job_text(j)
        hits = sum(1 for pats in agent_fw_pats.values() if match_any(text, pats))
        if hits >= 2:
            multi_fw += 1
    if multi_fw >= 2:
        pct_val = multi_fw / total * 100
        body = (f"<b>{multi_fw}</b> 个岗位({pct_val:.0f}%)要求掌握"
                f" <b>2 种以上</b> Agent 开发框架,"
                f"单一框架经验已不够,需要横向对比能力。")
        insights.append(("多框架复合要求", body, pct_val))

    insights.sort(key=lambda x: x[2], reverse=True)
    return insights


def mine_insights(jobs, insights_path=None):
    """提炼跨岗位规律:有 insights.json 就用,没有就正则兜底。"""
    if insights_path:
        result = load_insights(insights_path)
        if result:
            return result
    return regex_insights(jobs)


# ---------------------------------------------------------------------------
# Claude 标注(主路径):技能/语言/职责的"理解判断"由 Claude 在第 2 步完成,
# 写进 analysis.json,本脚本只做确定性的计数/占比/共现。
# 正则词典(TECH_TERMS 等)退居兜底,仅在没有 analysis.json 时启用。
# ---------------------------------------------------------------------------
def canon_url(url):
    """对齐用的 URL 归一:取 /job_detail/<id> 里的岗位 ID。
    jobs.json 里的 URL 常带 ?securityId= 等会话参数,而标注时往往写干净 URL——
    严格字符串相等会让这些岗位的标注静默对不上号、被排除出统计。"""
    url = (url or "").strip()
    m = re.search(r"/job_detail/([^./?#]+)", url)
    return m.group(1) if m else url.split("?")[0].split("#")[0]


def load_analysis(path):
    """加载 Claude 第 2 步生成的 analysis.json。结构:
    {
      "per_job": [{"detail_url": "...", "tech": [...], "langs": [...], "duties": [...]}, ...],
      "insights": [{"title": "...", "body": "...", "pct": 数字}, ...]  # 可选
    }
    返回 (by_url, insights):
      by_url    : dict[detail_url -> {"tech":[],"langs":[],"duties":[]}]
      insights  : [(title, body, pct), ...] 或 None
    岗位靠 detail_url 对齐,标签为 Claude 归一化后的展示名(如 "LangChain"、"Python"、"模型微调")。
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[warn] 加载 analysis.json 失败: {e}", flush=True)
        return None, None
    by_url = {}
    for row in data.get("per_job", []) or []:
        url = canon_url(row.get("detail_url"))
        if not url:
            continue
        by_url[url] = {
            "tech":   [str(x).strip() for x in (row.get("tech") or []) if str(x).strip()],
            "langs":  [str(x).strip() for x in (row.get("langs") or []) if str(x).strip()],
            "duties": [str(x).strip() for x in (row.get("duties") or []) if str(x).strip()],
        }
    if not by_url:
        print(f"[warn] analysis.json 里没有可用的 per_job 标注,回退正则", flush=True)
        return None, None
    insights = None
    raw_ins = data.get("insights")
    if raw_ins:
        tmp = []
        for item in raw_ins:
            if isinstance(item, dict) and "title" in item and "body" in item:
                tmp.append((str(item["title"]), str(item["body"]), float(item.get("pct", 0))))
        insights = tmp or None
    print(f"[analysis] 已加载 {len(by_url)} 个岗位的 Claude 标注 <- {path}", flush=True)
    return by_url, insights


def tag_doc_freq(jobs, by_url, field):
    """文档频率:多少个岗位的该字段标注里出现了某标签。同岗位内去重,避免重复计数。"""
    c = Counter()
    for job in jobs:
        tags = (by_url.get(canon_url(job.get("detail_url"))) or {}).get(field) or []
        for name in dict.fromkeys(tags):
            c[name] += 1
    return c


def tag_cooccurrence(jobs, by_url, field="tech", top_n=10):
    """从 Claude 标注算技能共现对,接口与 cooccurrence() 一致。"""
    per_job = []
    for job in jobs:
        tags = (by_url.get(canon_url(job.get("detail_url"))) or {}).get(field) or []
        per_job.append(set(tags))
    pairs = Counter()
    for hits in per_job:
        hl = sorted(hits)
        for i, a in enumerate(hl):
            for b in hl[i + 1:]:
                pairs[(a, b)] += 1
    total = len(jobs) or 1
    return [((a, b), cnt, cnt / total) for (a, b), cnt in pairs.most_common(top_n) if cnt >= 2]


# ---------------------------------------------------------------------------
# HTML 渲染(纯 CSS 图表,无 JS;卡片用 <details> 折叠)
# ---------------------------------------------------------------------------
def esc(s):
    return html.escape(str(s) if s is not None else "")


def nl2br(s):
    return esc(s).replace("\n", "<br>")


def color(i):
    return PALETTE[i % len(PALETTE)]


def bar_rows(items, total, rank=False):
    """单系列横向条形图。items=[(label, count)]。rank=True 时高亮数值最大的一行。"""
    if not items:
        return "<p class='muted'>无数据</p>"
    mx = max(v for _, v in items) or 1
    out = []
    for i, (label, v) in enumerate(items):
        pct = v / total * 100 if total else 0
        w = v / mx * 100
        cls = "bar top" if (rank and v == mx) else "bar"
        delay = 0.15 + i * 0.06
        tip = f"{label}: {v}/{total} 个岗位 ({pct:.1f}%)"
        out.append(
            f"<div class='{cls}' data-tip='{esc(tip)}'>"
            f"<span class='bar-label'>{esc(label)}</span>"
            f"<span class='bar-track'><span class='bar-fill' style='--w:{w:.1f}%;animation-delay:{delay:.2f}s'></span></span>"
            f"<span class='bar-num'>{v}<i>{pct:.0f}%</i></span>"
            f"</div>"
        )
    return "<div class='bars'>" + "".join(out) + "</div>"


def value_bars(items, unit=""):
    """按数值(非计数)画条形图,items=[(label, value)]。用于薪资×经验这种。"""
    if not items:
        return "<p class='muted'>无数据</p>"
    mx = max(v for _, v in items) or 1
    out = []
    for i, (label, v) in enumerate(items):
        w = v / mx * 100
        delay = 0.15 + i * 0.06
        out.append(
            f"<div class='bar' data-tip='{esc(label)}: {v:g}{unit}'>"
            f"<span class='bar-label'>{esc(label)}</span>"
            f"<span class='bar-track'><span class='bar-fill' style='--w:{w:.1f}%;animation-delay:{delay:.2f}s'></span></span>"
            f"<span class='bar-num'>{v:g}{unit}</span></div>"
        )
    return "<div class='bars'>" + "".join(out) + "</div>"


def callout(html_text):
    """一句话关键结论高亮条。"""
    return f"<div class='callout'><span class='callout-dot'></span><p>{html_text}</p></div>"


def pct(v, total):
    return f"{v / total * 100:.0f}%" if total else "0%"


def grouped_bar_rows(labels, groups, data, totals):
    """对比横向条形图。
    labels: [term...]; groups: [keyword...]; data[term][group]=count; totals[group]=该组岗位数。
    每个 term 一行,行内每个 group 一根小条,显示占比。"""
    out = []
    for term in labels:
        sub = []
        for gi, g in enumerate(groups):
            cnt = data.get(term, {}).get(g, 0)
            tot = totals.get(g, 0) or 1
            pct = cnt / tot * 100
            sub.append(
                f"<span class='gb-item'><span class='gb-track'>"
                f"<span class='gb-fill' style='--w:{pct:.1f}%;background:{color(gi)}'></span></span>"
                f"<span class='gb-val' style='color:{color(gi)}'>{pct:.0f}%</span></span>"
            )
        out.append(
            f"<div class='gb-row'><span class='bar-label'>{esc(term)}</span>"
            f"<span class='gb-bars'>{''.join(sub)}</span></div>"
        )
    return "<div class='bars'>" + "".join(out) + "</div>"


def legend(groups, totals):
    items = []
    for gi, g in enumerate(groups):
        items.append(
            f"<span class='lg'><i style='background:{color(gi)}'></i>{esc(g)} "
            f"<span class='muted'>n={totals.get(g,0)}</span></span>"
        )
    return "<div class='legend'>" + "".join(items) + "</div>"


def wordcloud(counter):
    if not counter:
        return "<p class='muted'>无数据</p>"
    mx = max(counter.values())
    spans = []
    for name, v in counter.most_common(30):
        r = v / mx
        size = 15 + r * 27
        opacity = 0.5 + r * 0.5
        weight = 600 if r > 0.5 else 500
        spans.append(
            f"<span class='w' style='font-size:{size:.0f}px;opacity:{opacity:.2f};font-weight:{weight}' "
            f"data-tip='{v} 个岗位'>{esc(name)}</span>"
        )
    return "<div class='cloud'>" + " ".join(spans) + "</div>"


def donut_chart(items, total, center_label="岗位"):
    if not items or not total:
        return "<p class='muted'>无数据</p>"
    colors = ["#C15F3C", "#7D7A5C", "#CC9B7A", "#9C6B4F", "#A8704F",
              "#6E6A50", "#B8856A", "#8A8570", "#D4A88C", "#7A7568"]
    items = items[:8]
    shown = sum(v for _, v in items)
    # 多标签数据(如一岗多语言)的岗位占比和会超 100%,conic-gradient 超出 100% 的段
    # 会被整段截掉(图例有、轮盘没有)。超界时轮盘改按"提及份额"画,图例仍标岗位占比。
    base = shown if shown > total else total
    segments, legs = [], []
    acc = 0
    for i, (label, v) in enumerate(items):
        p_wheel = v / base * 100
        p_jobs = v / total * 100
        c = colors[i % len(colors)]
        segments.append(f"{c} {acc:.1f}% {acc + p_wheel:.1f}%")
        acc += p_wheel
        legs.append(
            f"<div class='donut-leg'><i style='background:{c}'></i>"
            f"<span class='donut-name'>{esc(label)}</span>"
            f"<span class='donut-val'>{v} <em>{p_jobs:.0f}%</em></span></div>")
    if acc < 100:
        segments.append(f"var(--well) {acc:.1f}% 100%")
    grad = ",".join(segments)
    return (
        f"<div class='donut-wrap'>"
        f"<div class='donut' style='background:conic-gradient({grad})'>"
        f"<div class='donut-hole'><span class='donut-total'>{total}</span>"
        f"<span class='donut-cap'>{esc(center_label)}</span></div></div>"
        f"<div class='donut-legend'>{''.join(legs)}</div></div>")


def column_chart(items, unit="", total=0):
    if not items:
        return "<p class='muted'>无数据</p>"
    mx = max(v for _, v in items) or 1
    cols = []
    for i, (label, v) in enumerate(items):
        h = max(v / mx * 100, 2)
        pct_s = f" ({v/total*100:.0f}%)" if total else ""
        delay = 0.15 + i * 0.06
        cols.append(
            f"<div class='col' data-tip='{esc(label)}: {v}{unit}{pct_s}'>"
            f"<span class='col-val'>{v}{unit}</span>"
            f"<div class='col-track'><div class='col-fill' style='--h:{h:.1f}%;animation-delay:{delay:.2f}s'></div></div>"
            f"<span class='col-label'>{esc(label)}</span></div>")
    return "<div class='columns'>" + "".join(cols) + "</div>"


def radar_chart(items, total, size=280):
    items = items[:6]
    if len(items) < 3:
        return ""
    n = len(items)
    cx, cy = size / 2, size / 2
    r = size * 0.34
    angles = [i * 2 * math.pi / n - math.pi / 2 for i in range(n)]
    rings_html = ""
    for frac in [0.25, 0.5, 0.75, 1.0]:
        pts = " ".join(f"{cx + r * frac * math.cos(a):.1f},{cy + r * frac * math.sin(a):.1f}" for a in angles)
        rings_html += f"<polygon points='{pts}' class='radar-ring'/>"
    axes_html = "".join(
        f"<line x1='{cx}' y1='{cy}' x2='{cx + r * math.cos(a):.1f}' y2='{cy + r * math.sin(a):.1f}' class='radar-axis'/>"
        for a in angles)
    data_pts = []
    for i, (_, v) in enumerate(items):
        ratio = min(v / total, 1.0) if total else 0
        data_pts.append(f"{cx + r * ratio * math.cos(angles[i]):.1f},{cy + r * ratio * math.sin(angles[i]):.1f}")
    dots = "".join(f"<circle cx='{p.split(',')[0]}' cy='{p.split(',')[1]}' r='4' class='radar-dot'/>" for p in data_pts)
    labels_html = ""
    for i, (label, v) in enumerate(items):
        lx = cx + (r + 30) * math.cos(angles[i])
        ly = cy + (r + 30) * math.sin(angles[i])
        anchor = "middle"
        if math.cos(angles[i]) > 0.3: anchor = "start"
        elif math.cos(angles[i]) < -0.3: anchor = "end"
        pct_v = v / total * 100 if total else 0
        labels_html += (
            f"<text x='{lx:.1f}' y='{ly:.1f}' text-anchor='{anchor}' "
            f"dominant-baseline='central' class='radar-label'>"
            f"{esc(label)} <tspan class='radar-pct'>{pct_v:.0f}%</tspan></text>")
    pts_str = " ".join(data_pts)
    return (
        f"<div class='radar-wrap'>"
        f"<svg class='radar-svg' viewBox='0 0 {size} {size}'>"
        f"{rings_html}{axes_html}"
        f"<polygon points='{pts_str}' class='radar-fill'/>"
        f"<polygon points='{pts_str}' class='radar-stroke'/>"
        f"{dots}{labels_html}</svg></div>")


def pill_cloud(items, total):
    if not items:
        return "<p class='muted'>无数据</p>"
    mx = max(v for _, v in items) or 1
    pills = []
    for label, v in items[:15]:
        ratio = v / mx
        opacity = 0.4 + ratio * 0.6
        p = v / total * 100 if total else 0
        pills.append(
            f"<span class='pill' style='opacity:{opacity:.2f}'>"
            f"<b>{esc(label)}</b><em>{v} ({p:.0f}%)</em></span>")
    return "<div class='pill-cloud'>" + "".join(pills) + "</div>"


def cooccur_grid(pairs):
    """渲染技能共现对为连接卡片。pairs = [((a, b), count, ratio)]。"""
    if not pairs:
        return "<p class='muted'>共现数据不足</p>"
    cards = []
    for (a, b), cnt, ratio in pairs:
        pct = ratio * 100
        w = min(pct / (pairs[0][2] * 100) * 100, 100) if pairs[0][2] else 0
        cards.append(
            f"<div class='copair' data-tip='{cnt} 个岗位同时要求这两项'>"
            f"<span class='copair-names'>"
            f"<b>{esc(a)}</b><span class='copair-link'>+</span><b>{esc(b)}</b></span>"
            f"<span class='copair-bar'><span class='copair-fill' style='--w:{w:.0f}%'></span></span>"
            f"<span class='copair-pct'>{pct:.0f}%</span>"
            f"</div>")
    return "<div class='copairs'>" + "".join(cards) + "</div>"


def bonus_grid(items):
    """Renders bonus items as a card grid with frequency badges."""
    if not items:
        return "<p class='muted'>无数据</p>"
    cards = []
    for text, count in items:
        cls = "bonus-card hot" if count >= 2 else "bonus-card"
        # strip leading number prefixes (e.g. "1、" "2." "3，") from JD formatting
        clean = re.sub(r"^[0-9]+[、.．,，:：)\]】]\s*", "", text)
        badge = f"<span class='bonus-cnt'>{count}岗</span>"
        cards.append(
            f"<div class='{cls}'>{badge}"
            f"<span class='bonus-text'>{esc(clean)}</span></div>")
    return "<div class='bonus-grid'>" + "".join(cards) + "</div>"


def insight_cards(insights):
    """渲染洞察规律为编号卡片列表。insights = [(title, body_html, pct)]。"""
    if not insights:
        return "<p class='muted'>样本量不足,暂无显著规律</p>"
    cards = []
    for i, (title, body, pct_val) in enumerate(insights):
        cards.append(
            f"<div class='insight-card'>"
            f"<div class='insight-head'>"
            f"<span class='insight-idx'>{i + 1:02d}</span>"
            f"<span class='insight-title'>{esc(title)}</span>"
            f"<span class='insight-pct'>{pct_val:.0f}%</span>"
            f"</div>"
            f"<p class='insight-body'>{body}</p>"
            f"</div>")
    return "<div class='insight-list'>" + "".join(cards) + "</div>"


def card(job):
    tags = "".join(f"<span class='tag'>{esc(t)}</span>" for t in (job.get("tags") or []))
    salary = esc(job.get("salary_raw") or "面议")
    meta = " · ".join(filter(None, [
        esc(job.get("city") or ""),
        esc(job.get("experience") or ""),
        esc(job.get("education") or ""),
    ]))
    co_info = esc(job.get("company_info") or "")
    co_html = f" <span class='muted'>{co_info}</span>" if co_info else ""
    hr = esc(job.get("hr_active") or "")
    hr_html = f"<span class='hr'>● {hr}</span>" if hr else ""
    bens = job.get("benefits") or []
    ben_html = ("<div class='job-benefits'>" +
                "".join(f"<span class='ben'>{esc(b)}</span>" for b in bens[:8]) +
                "</div>") if bens else ""
    url = job.get("detail_url") or ""
    link = (f"<a class='job-link' href='{esc(url)}' target='_blank' rel='noopener'>"
            f"在 BOSS 查看原页 ↗</a>") if url else ""

    mm, _ = parse_salary(job.get("salary_raw", ""))
    data_salary = f"{mm:g}" if mm is not None else "0"
    data_exp = esc(norm_experience(job.get("experience")))
    data_edu = esc(norm_education(job.get("education")))

    def section(title, body):
        if not body:
            return ""
        return f"<div class='jd-sec'><h4>{title}</h4><p>{nl2br(body)}</p></div>"

    detail = (
        section("岗位职责", job.get("responsibilities_raw")) +
        section("任职要求", job.get("requirements_raw")) +
        section("加分项", job.get("bonus_raw"))
    ) or "<p class='muted'>未抓到职责/要求原文</p>"

    return (
        f"<details class='job' data-salary='{data_salary}' data-exp='{data_exp}' data-edu='{data_edu}'>"
        f"<summary>"
        f"<div class='job-top'>"
        f"<span class='job-title'>{esc(job.get('title') or '未知岗位')}</span>"
        f"<span class='job-pay'>{salary}</span></div>"
        f"<div class='job-co'>{esc(job.get('company') or '')}{co_html}</div>"
        f"<div class='job-metaline'>{meta}{hr_html}</div>"
        f"<div class='job-tags'>{tags}</div>"
        f"{ben_html}"
        f"<span class='job-cue'>展开 BOSS 原文 ↓</span>"
        f"</summary>"
        f"<div class='job-body'>{detail}{link}</div>"
        f"</details>"
    )


def section_block(num, title, subtitle, inner, idx):
    over = f"<span class='block-num'>{esc(num)}</span>" if num else ""
    sub = f"<p class='block-sub'>{esc(subtitle)}</p>" if subtitle else ""
    return (f"<section class='block' id='sec-{idx}' style='--i:{idx}'>"
            f"<div class='block-head'>{over}<h2>{esc(title)}</h2></div>{sub}{inner}</section>")


def build_html(jobs, analysis_path=None, insights_path=None):
    groups = list(OrderedDict.fromkeys(j.get("keyword", "未分组") for j in jobs))
    by_group = {g: [j for j in jobs if j.get("keyword", "未分组") == g] for g in groups}
    totals = {g: len(by_group[g]) for g in groups}
    total = len(jobs)
    multi = len(groups) > 1

    # 数据源:有 analysis.json(Claude 标注)走主路径,否则正则词典兜底。
    by_url, analysis_insights = (None, None)
    if analysis_path:
        by_url, analysis_insights = load_analysis(analysis_path)
    use_claude = bool(by_url)

    def tech_freq(subset):
        return tag_doc_freq(subset, by_url, "tech") if use_claude else doc_freq(subset, TECH_TERMS)

    def lang_freq(subset):
        return tag_doc_freq(subset, by_url, "langs") if use_claude else doc_freq(subset, LANG_TERMS)

    # 全局词频:技能/语言/职责由 Claude 标注计数(兜底走正则);加分项始终按原文聚合。
    tech_all = tech_freq(jobs)
    lang_all = lang_freq(jobs)
    duty_all = tag_doc_freq(jobs, by_url, "duties") if use_claude else duty_freq(jobs)
    bonus_all = collect_bonus(jobs)

    sstat = salary_stats(jobs)
    fmt = lambda x: f"{x:g}"
    sections = []  # (num, title, subtitle, inner)

    # ---- 概览 ----
    figs = [f"<div class='figure'><div class='num'>{total}</div><div class='cap'>在招岗位</div></div>"]
    if multi:
        figs.append(f"<div class='figure'><div class='num'>{len(groups)}</div>"
                    f"<div class='cap'>岗位类别</div></div>")
    if sstat:
        figs.append(f"<div class='figure'><div class='num'>{fmt(sstat['median_monthly'])}<em>K</em></div>"
                    f"<div class='cap'>月薪中位数</div></div>")
        figs.append(f"<div class='figure'><div class='num'>{fmt(sstat['median_annual'])}<em>万</em></div>"
                    f"<div class='cap'>年薪中位数</div></div>")
        figs.append(f"<div class='figure'><div class='num'>{fmt(sstat['min_monthly'])}"
                    f"<em>–{fmt(sstat['max_monthly'])}K</em></div>"
                    f"<div class='cap'>月薪区间</div></div>")
    overview = "<div class='stats'>" + "".join(figs) + "</div>"
    overview += "<div class='chips'>" + "".join(
        f"<span class='chip'>{esc(g)} <b>{totals[g]}</b></span>" for g in groups) + "</div>"
    sections.append(("", "概览", None, overview))

    # ---- 总结分析 ----
    sum_items = []
    advice = []
    top5 = tech_all.most_common(5)
    if top5:
        sum_items.append(("核心技术栈",
            "、".join(f"<b>{esc(n)}</b>({pct(v, total)})" for n, v in top5)))
        must = [esc(n) for n, v in top5[:3] if v / total > 0.3]
        if must:
            advice.append("优先掌握 " + "、".join(f"<b>{m}</b>" for m in must))
    top_lang = lang_all.most_common(3)
    if top_lang:
        sum_items.append(("主流语言",
            "、".join(f"<b>{esc(n)}</b>({pct(v, total)})" for n, v in top_lang)))
        advice.append(f"语言首选 <b>{esc(top_lang[0][0])}</b>")
    s_exp = dist(jobs, lambda j: norm_experience(j.get("experience")), EXP_ORDER)
    s_edu = dist(jobs, lambda j: norm_education(j.get("education")), EDU_ORDER)
    if s_exp:
        te = max(s_exp, key=lambda x: x[1])
        sum_items.append(("经验门槛", f"<b>{esc(te[0])}</b> 为主({pct(te[1], total)})"))
    if s_edu:
        td = max(s_edu, key=lambda x: x[1])
        sum_items.append(("学历要求", f"<b>{esc(td[0])}</b> 为主({pct(td[1], total)})"))
    if sstat:
        sum_items.append(("薪资水平",
            f"月薪 <b>{fmt(sstat['min_monthly'])}–{fmt(sstat['max_monthly'])}K</b>"
            f",中位 <b>{fmt(sstat['median_monthly'])}K</b>"))
    top_bonus = bonus_all.most_common(3)
    if top_bonus:
        sum_items.append(("差异化加分",
            "、".join(f"<b>{esc(n)}</b>" for n, _ in top_bonus)))
        advice.append(f"差异化方向关注「{esc(top_bonus[0][0])}」")
    sum_inner = ""
    if advice:
        sum_inner += callout("学习建议：" + "；".join(advice) + "。")
    sum_inner += "<div class='sum-grid'>" + "".join(
        f"<div class='sum-row'><div class='sum-label'>{k}</div>"
        f"<div class='sum-val'>{v}</div></div>"
        for k, v in sum_items) + "</div>"
    sections.append(("✦", "总结分析", "从招聘数据中提炼的市场洞察与学习方向", sum_inner))

    # ---- 维度1:技术栈 ----
    top3 = tech_all.most_common(3)
    if top3:
        items = "、".join(f"<b>{esc(n)}</b>({pct(v, total)})" for n, v in top3)
        tip = callout(f"{total} 个岗位里,被点名最多的是 {items}。这些是该岗位的核心技术底色。")
    else:
        tip = ""
    radar_html = radar_chart(tech_all.most_common(6), total)
    if multi:
        data = {}
        union = [name for name, _ in tech_all.most_common(18)]
        for g in groups:
            gc = tech_freq(by_group[g])
            for name in union:
                data.setdefault(name, {})[g] = gc.get(name, 0)
        inner = tip + radar_html + legend(groups, totals) + grouped_bar_rows(union, groups, data, totals)
    else:
        inner = tip + radar_html + "<h3>完整技术栈排名</h3>" + bar_rows(tech_all.most_common(18), total, rank=True)
    inner += "<h3>技术词云</h3>" + wordcloud(tech_all)
    co_pairs = tag_cooccurrence(jobs, by_url) if use_claude else cooccurrence(jobs, TECH_TERMS)
    if co_pairs:
        inner += "<h3>常见技能组合</h3>" + cooccur_grid(co_pairs)
    sections.append(("01", "技术栈 / 智能体框架",
                     "数值 = 提到该技术的岗位占比(文档频率)", inner))

    # ---- 维度2:编程语言 ----
    lang_items = lang_all.most_common(8)
    lang_donut = donut_chart(lang_items, total, center_label="岗位")
    if multi:
        data = {}
        union = [name for name, _ in lang_all.most_common(12)]
        for g in groups:
            gc = lang_freq(by_group[g])
            for name in union:
                data.setdefault(name, {})[g] = gc.get(name, 0)
        inner = lang_donut + "<h3>分关键词对比</h3>" + legend(groups, totals) + grouped_bar_rows(union, groups, data, totals)
    else:
        topl = lang_all.most_common(1)
        ltip = callout(f"<b>{esc(topl[0][0])}</b> 是硬通货,{pct(topl[0][1], total)} 的岗位都要求。") if topl else ""
        inner = ltip + lang_donut
    sections.append(("02", "编程语言要求占比", None, inner))

    # ---- 维度3:硬性要求 + 薪资 ----
    edu_dist = dist(jobs, lambda j: norm_education(j.get("education")), EDU_ORDER)
    exp_dist = dist(jobs, lambda j: norm_experience(j.get("experience")), EXP_ORDER)
    bits = []
    if edu_dist:
        te = max(edu_dist, key=lambda x: x[1])
        bits.append(f"学历以 <b>{esc(te[0])}</b> 为主({pct(te[1], total)})")
    if exp_dist:
        tx = max(exp_dist, key=lambda x: x[1])
        bits.append(f"经验多要求 <b>{esc(tx[0])}</b>")
    if sstat:
        hist = salary_histogram(sstat["monthly_values"])
        tb = max(hist, key=lambda x: x[1])
        bits.append(f"月薪集中在 <b>{tb[0]}</b>,中位 <b>{sstat['median_monthly']:g}K</b>")
    hard_tip = callout("、".join(bits) + "。") if bits else ""
    edu_html = "<h3>学历要求</h3>" + donut_chart(edu_dist, total, center_label="岗位")
    exp_html = "<h3>工作年限</h3>" + bar_rows(exp_dist, total)
    if sstat:
        hist = salary_histogram(sstat["monthly_values"])
        sal_html = "<h3>薪资分布(按月薪中点)</h3>" + column_chart(hist, total=sstat["n"])
        sal_html += (f"<p class='muted'>月薪中位 {fmt(sstat['median_monthly'])}K,"
                     f"区间 {fmt(sstat['min_monthly'])}–{fmt(sstat['max_monthly'])}K,"
                     f"可解析样本 {sstat['n']}/{total}</p>")
        if multi:
            rows = []
            for g in groups:
                gs = salary_stats(by_group[g])
                if gs:
                    rows.append(f"<tr><td>{esc(g)}</td><td>{gs['median_monthly']}K</td>"
                                f"<td>{gs['median_annual']}万</td><td>{gs['n']}</td></tr>")
            if rows:
                sal_html += ("<h3>各岗位薪资中位数对比</h3>"
                             "<table class='cmp'><tr><th>岗位</th><th>月薪中位</th>"
                             "<th>年薪中位</th><th>样本</th></tr>" + "".join(rows) + "</table>")
    else:
        sal_html = "<h3>薪资分布</h3><p class='muted'>无可解析薪资</p>"
    sxp = salary_by_experience(jobs)
    sxp_html = ("<h3>薪资 × 经验(各档月薪中位)</h3>" +
                value_bars([(e, m) for e, m, _ in sxp], "K")) if len(sxp) >= 2 else ""
    sections.append(("03", "硬性要求 + 薪资分布", None,
                     hard_tip + edu_html + exp_html + sal_html + sxp_html))

    # ---- 维度4:加分项 + 职责高频词 ----
    n_bonus = sum(1 for j in jobs if (j.get("bonus_raw") or "").strip())
    td = duty_all.most_common(3)
    dbits = []
    if td:
        dbits.append("职责高频词是 " + "、".join(f"<b>{esc(n)}</b>" for n, _ in td))
    if n_bonus:
        dbits.append(f"{n_bonus}/{total} 个岗位写明了加分项")
    duty_tip = callout("、".join(dbits) + "。") if dbits else ""
    duty_html = "<h3>高频职责关键词</h3>" + pill_cloud(duty_all.most_common(15), total)
    if bonus_all:
        bonus_html = "<h3>高频加分项 / 优先项</h3>" + bonus_grid(bonus_all.most_common(20))
    else:
        bonus_html = "<h3>加分项</h3><p class='muted'>未抓到明确的加分项</p>"
    sections.append(("04", "加分项 + 高频职责关键词", None, duty_tip + duty_html + bonus_html))

    # ---- 维度5:市场规律洞察 ----
    insights = analysis_insights or mine_insights(jobs, insights_path=insights_path)
    if insights:
        top_ins = insights[0]
        ins_tip = callout(
            f"最显著的规律:<b>{esc(top_ins[0])}</b> — "
            f"{top_ins[2]:.0f}% 的岗位涉及。以下洞察按覆盖率降序排列。")
        ins_html = ins_tip + insight_cards(insights)
    else:
        ins_html = "<p class='muted'>样本量不足,暂无显著规律</p>"
    sections.append(("05", "市场规律洞察",
                     f"从 {total} 个岗位 JD 中自动提炼的跨岗位共性模式", ins_html))

    # ---- 岗位卡片墙 ----
    n_active = sum(1 for j in jobs if re.search(r"活跃|回复|在线|刚刚|今日|本周|分钟|小时",
                                                j.get("hr_active") or ""))

    edu_set = sorted({norm_education(j.get("education")) for j in jobs})
    exp_set = sorted({norm_experience(j.get("experience")) for j in jobs},
                     key=lambda x: EXP_ORDER.index(x) if x in EXP_ORDER else 99)
    edu_opts = "".join(f"<option value='{esc(e)}'>{esc(e)}</option>" for e in edu_set)
    exp_opts = "".join(f"<option value='{esc(e)}'>{esc(e)}</option>" for e in exp_set)

    controls = (
        "<div class='wall-controls'>"
        "<input type='text' class='wall-search' id='wallSearch' placeholder='搜索岗位名/公司/技能...'>"
        "<select id='filterExp' class='wall-select'><option value=''>经验不限</option>" + exp_opts + "</select>"
        "<select id='filterEdu' class='wall-select'><option value=''>学历不限</option>" + edu_opts + "</select>"
        "<select id='sortBy' class='wall-select'>"
        "<option value='default'>默认排序</option>"
        "<option value='salary-desc'>薪资从高到低</option>"
        "<option value='salary-asc'>薪资从低到高</option>"
        "</select>"
        "<span class='wall-count' id='wallCount'></span>"
        "</div>"
    )

    wall = [controls]
    if n_active:
        wall.append(callout(f"<b>{n_active}/{total}</b> 个岗位的 HR 近期活跃(卡片上有 ● 标记),投递优先看这些。"))
    for g in groups:
        if multi:
            wall.append(f"<h3 class='wall-group'>{esc(g)} <span class='muted'>{totals[g]} 个</span></h3>")
        wall.append("<div class='cards'>")
        for job in by_group[g]:
            wall.append(card(job))
        wall.append("</div>")
    num_wall = f"{sum(s[0][:1].isdigit() for s in sections) + 1:02d}"
    sections.append((num_wall, "岗位卡片墙",
                     "点击任意卡片展开该岗位在 BOSS 上的原始职责与要求", "".join(wall)))

    # ---- 组装 ----
    body = "".join(section_block(num, t, sub, inner, i)
                   for i, (num, t, sub, inner) in enumerate(sections))

    toc_items = "".join(
        f"<a class='toc-item' href='#sec-{i}'>"
        f"<span class='toc-num'>{esc(num)}</span>{esc(t)}</a>"
        for i, (num, t, _, _) in enumerate(sections) if num
    )
    toc = (f"<nav class='toc' id='toc'>"
           f"<div class='toc-title'>目录</div>{toc_items}</nav>")

    toolbar = (
        "<div class='toolbar' id='toolbar'>"
        "<button class='tb-btn' id='themeToggle' title='切换深色模式'>"
        "<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' "
        "stroke-width='2'><circle cx='12' cy='12' r='5'/>"
        "<path d='M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42"
        "M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42'/></svg></button>"
        "<button class='tb-btn' id='pdfExport' title='导出 PDF'>"
        "<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' "
        "stroke-width='2'><path d='M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 "
        "002-2V8z'/><path d='M14 2v6h6M16 13H8M16 17H8M10 9H8'/></svg></button>"
        "</div>"
    )

    backtop = ("<button class='backtop' id='backtop' title='回到顶部'>"
               "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' "
               "stroke-width='2.5'><path d='M18 15l-6-6-6 6'/></svg></button>")

    kw_label = " · ".join(groups)
    today = datetime.date.today().isoformat()
    masthead = (
        "<header class='masthead'>"
        "<div class='kicker'>人才市场需求分析</div>"
        f"<h1 class='headline'>{esc(kw_label)}</h1>"
        f"<p class='standfirst'>基于 {total} 个真实在招岗位,拆解技术栈、薪资与硬性要求。</p>"
        f"<p class='standfirst' style='font-size:14px;color:var(--muted);margin-top:-12px'>数据来源：BOSS直聘</p>"
        f"<div class='byline'>{today} · 数据源 jobs.json · 样本 {total} 个</div>"
        "</header>"
    )
    title = "人才市场需求分析 · " + kw_label
    footnote = ("技能/语言/职责由 Claude 阅读 JD 原文判定,占比与共现为脚本确定性计数"
                if use_claude else
                "词频与分布由内置词典正则匹配(降级模式,建议提供 Claude 标注的 analysis.json)")
    return (HTML_SHELL
            .replace("__TITLE__", esc(title))
            .replace("__MASTHEAD__", masthead)
            .replace("__BODY__", body)
            .replace("__TOC__", toc)
            .replace("__TOOLBAR__", toolbar)
            .replace("__BACKTOP__", backtop)
            .replace("__FOOTNOTE__", footnote))


HTML_SHELL = r"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="preconnect" href="https://gstatic.loli.net" crossorigin>
<link rel="stylesheet" href="https://fonts.loli.net/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap">
<style>
:root,[data-theme="light"]{
  --paper:#F0EEE6;--surface:#F6F4ED;--well:#E6E2D5;
  --ink:#1A1813;--ink-2:#46423A;--muted:#8C867A;
  --line:#DDD8CB;--line-2:#C8C2B2;
  --clay:#C15F3C;--clay-deep:#A8492B;--clay-2:#D98E6A;--clay-soft:#E2BBA6;
  --callout-bg:linear-gradient(180deg,#FBF3EC,var(--surface));
  --job-open-bg:#FBFAF5;--shadow-card:rgba(80,45,25,.45);
  --sans:"Inter",-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Noto Sans SC","HarmonyOS Sans SC","Microsoft YaHei",Arial,sans-serif;
  --num:"Inter",-apple-system,"SF Pro Display","PingFang SC","Helvetica Neue",Arial,sans-serif;
}
[data-theme="dark"]{
  --paper:#1A1A1F;--surface:#232328;--well:#2E2E35;
  --ink:#E8E6E0;--ink-2:#B8B5AC;--muted:#76736A;
  --line:#3A3A42;--line-2:#4A4A52;
  --clay:#E07850;--clay-deep:#F09070;--clay-2:#C06840;--clay-soft:rgba(224,120,80,.2);
  --callout-bg:linear-gradient(180deg,#2A2420,var(--surface));
  --job-open-bg:#28282E;--shadow-card:rgba(0,0,0,.6);
}
*{box-sizing:border-box}
html{-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;scroll-behavior:smooth}
body{margin:0;color:var(--ink);background:var(--paper);font-family:var(--sans);font-size:16px;line-height:1.65;transition:background .3s,color .3s}
.grain{position:fixed;inset:0;z-index:1;pointer-events:none;opacity:.05;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
[data-theme="dark"] .grain{opacity:.02}
.page{position:relative;z-index:2;max-width:880px;margin:0 auto;padding:74px 28px 100px}
.masthead{animation:rise .8s cubic-bezier(.2,.7,.2,1) both}
.kicker{font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--clay-deep);font-weight:600;margin-bottom:20px}
.headline{font-family:var(--sans);font-weight:700;font-size:clamp(34px,6vw,52px);line-height:1.12;letter-spacing:-.01em;margin:0 0 20px}
.standfirst{font-family:var(--sans);font-weight:300;font-size:20px;line-height:1.55;color:var(--ink-2);margin:0 0 22px;max-width:48ch}
.byline{font-size:13px;color:var(--muted);letter-spacing:.02em;padding-bottom:30px;border-bottom:1px solid var(--line-2)}
.block{padding:48px 0 6px;border-bottom:1px solid var(--line);animation:rise .8s cubic-bezier(.2,.7,.2,1) both;animation-delay:calc(var(--i,0)*70ms + 60ms)}
.block:last-of-type{border-bottom:none;padding-bottom:0}
.block-head{display:flex;align-items:baseline;gap:14px;margin-bottom:7px}
.block-num{font-family:var(--num);font-size:15px;color:var(--clay);font-weight:600;font-feature-settings:"tnum"}
.block h2{font-family:var(--sans);font-weight:600;font-size:25px;letter-spacing:0;margin:0;color:var(--ink)}
.block-sub{color:var(--muted);font-size:14px;margin:0 0 24px}
.sum-grid{margin:8px 0 0}
.sum-row{display:flex;gap:16px;padding:13px 0;border-bottom:1px solid var(--line)}
.sum-row:last-child{border-bottom:none}
.sum-label{flex:0 0 100px;font-size:13px;color:var(--muted);font-weight:600;letter-spacing:.03em;padding-top:1px}
.sum-val{flex:1;font-size:14.5px;color:var(--ink-2);line-height:1.7}
.sum-val b{color:var(--clay-deep);font-weight:600}
.block h3{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--clay-deep);font-weight:600;margin:30px 0 15px}
.muted{color:var(--muted)}
.callout{display:flex;gap:12px;align-items:flex-start;background:var(--callout-bg);border:1px solid var(--clay-soft);border-left:3px solid var(--clay);border-radius:12px;padding:15px 18px;margin:0 0 24px}
.callout p{margin:0;font-size:15px;line-height:1.62;color:var(--ink)}
.callout b{color:var(--clay-deep);font-weight:600;font-feature-settings:"tnum"}
.callout-dot{flex:0 0 auto;width:8px;height:8px;border-radius:50%;background:var(--clay);margin-top:8px;box-shadow:0 0 0 4px rgba(193,95,60,.14)}
.stats{display:flex;flex-wrap:wrap;gap:0;margin:22px 0 24px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--surface)}
.figure{flex:1;min-width:128px;padding:22px 24px;border-right:1px solid var(--line)}
.figure:last-child{border-right:none}
.figure .num{font-family:var(--num);font-size:38px;line-height:1;color:var(--ink);font-weight:600;letter-spacing:-.02em;font-feature-settings:"tnum"}
.figure .num em{font-style:normal;font-size:16px;font-weight:500;color:var(--clay);letter-spacing:0}
.figure .cap{margin-top:9px;font-size:12.5px;color:var(--muted);letter-spacing:.03em}
.chips{display:flex;flex-wrap:wrap;gap:9px}
.chip{font-size:13px;padding:5px 14px;border:1px solid var(--line-2);border-radius:999px;color:var(--ink-2);background:var(--surface)}
.chip b{color:var(--clay);font-feature-settings:"tnum"}
.bars{display:flex;flex-direction:column;gap:9px;margin:4px 0}
.bar{display:flex;align-items:center;gap:14px;padding:3px 6px;margin:-3px -6px;border-radius:8px;transition:background .15s;cursor:default}
.bar:hover{background:var(--well)}
.bar:hover .bar-label{color:var(--ink)}
.bar:hover .bar-fill{filter:brightness(1.12)}
.bar-label{flex:0 0 156px;width:156px;text-align:right;font-size:13.5px;color:var(--ink-2);transition:color .15s}
.bar-track{flex:1;height:10px;background:var(--well);border-radius:999px;overflow:hidden;transition:height .15s}
.bar:hover .bar-track{height:13px}
.bar-fill{display:block;height:100%;width:0;border-radius:999px;background:linear-gradient(90deg,var(--clay),var(--clay-2));animation:grow 1.1s cubic-bezier(.2,.8,.2,1) both;transition:filter .15s}
.bar-num{flex:0 0 84px;width:84px;font-size:13px;color:var(--ink);font-feature-settings:"tnum"}
.bar-num i{font-style:normal;color:var(--muted);margin-left:6px}
.bar.top .bar-label{color:var(--ink);font-weight:600}
.bar.top .bar-fill{background:linear-gradient(90deg,var(--clay-deep),var(--clay))}
.bar.top .bar-track{box-shadow:0 0 0 1px var(--clay-soft)}
.gb-row{display:flex;align-items:flex-start;gap:14px;margin:11px 0}
.gb-bars{flex:1;display:flex;flex-direction:column;gap:6px}
.gb-item{display:flex;align-items:center;gap:10px}
.gb-track{flex:1;height:9px;background:var(--well);border-radius:999px;overflow:hidden}
.gb-fill{display:block;height:100%;width:0;border-radius:999px;animation:grow 1.1s cubic-bezier(.2,.8,.2,1) both;animation-delay:.3s}
.gb-val{flex:0 0 40px;width:40px;font-size:12px;text-align:right;font-feature-settings:"tnum"}
.legend{display:flex;flex-wrap:wrap;gap:18px;margin:4px 0 18px}
.lg{font-size:13px;color:var(--ink-2)}
.lg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:middle}
.cloud{line-height:2.5;margin-top:4px}
.w{display:inline-block;margin:3px 14px 3px 0;color:var(--clay);font-family:var(--sans);vertical-align:middle}
.bonus{list-style:none;margin:4px 0 0;padding:0;columns:2;column-gap:36px}
.bonus li{break-inside:avoid;padding:8px 0 8px 18px;position:relative;font-size:14px;color:var(--ink-2);border-bottom:1px solid var(--line)}
.bonus li::before{content:"";position:absolute;left:0;top:16px;width:6px;height:6px;border-radius:50%;background:var(--clay-soft)}
.bonus li span{color:var(--muted);font-size:12px}
.bonus-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px;margin-top:8px}
.bonus-card{display:flex;align-items:baseline;gap:10px;padding:10px 14px;border-radius:8px;background:var(--well);border:1px solid var(--line);font-size:13.5px;color:var(--ink-2);border-left:3px solid transparent;transition:border-color .2s}
.bonus-card.hot{border-left-color:var(--clay);background:var(--paper)}
.bonus-cnt{flex-shrink:0;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:700;font-feature-settings:"tnum";background:var(--line);color:var(--muted);white-space:nowrap}
.bonus-card.hot .bonus-cnt{background:var(--clay);color:#fff}
.bonus-text{line-height:1.5}
table.cmp{border-collapse:collapse;width:100%;margin-top:8px;font-size:14px}
table.cmp th,table.cmp td{border-bottom:1px solid var(--line);padding:9px 12px;text-align:left;font-feature-settings:"tnum"}
table.cmp th{color:var(--muted);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.07em}
.wall-group{font-size:18px;color:var(--ink);margin:26px 0 12px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(248px,1fr));gap:14px;margin-top:6px}
.job{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px 20px;transition:border-color .25s,box-shadow .25s,transform .25s}
.job:hover{border-color:var(--clay-soft);box-shadow:0 12px 32px -20px var(--shadow-card);transform:translateY(-2px)}
.job[open]{grid-column:1/-1;background:var(--job-open-bg);transform:none}
.job summary{cursor:pointer;list-style:none;outline:none}
.job summary::-webkit-details-marker{display:none}
.job-top{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.job-title{font-family:var(--sans);font-size:17px;font-weight:600;color:var(--ink);line-height:1.3}
.job-pay{color:var(--clay-deep);font-weight:600;white-space:nowrap;font-size:15px;font-feature-settings:"tnum"}
.job-co{font-size:13.5px;color:var(--ink-2);margin-top:8px}
.job-metaline{font-size:12.5px;color:var(--muted);margin-top:6px;letter-spacing:.02em}
.job-tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:11px}
.tag{font-size:11.5px;color:var(--clay-deep);background:rgba(193,95,60,.08);border:1px solid var(--clay-soft);padding:2px 9px;border-radius:6px}
.job-benefits{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.ben{font-size:11px;color:var(--ink-2);background:var(--well);padding:2px 8px;border-radius:6px}
.hr{margin-left:9px;color:#3f7d5a;font-size:12px;font-weight:500;white-space:nowrap}
[data-theme="dark"] .hr{color:#6cc090}
.job-cue{display:inline-block;margin-top:13px;font-size:12px;color:var(--clay);letter-spacing:.04em}
.job[open] .job-cue{display:none}
.job-body{margin-top:16px;padding-top:16px;border-top:1px solid var(--line)}
.jd-sec{margin-bottom:15px}
.jd-sec h4{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--clay-deep);margin:0 0 7px;font-weight:600}
.jd-sec p{margin:0;font-family:var(--sans);font-weight:400;font-size:14px;line-height:1.78;color:var(--ink-2)}
.job-link{display:inline-block;margin-top:4px;color:var(--clay);font-size:13px;text-decoration:none;border-bottom:1px solid var(--clay-soft)}
.job.hidden{display:none}
footer{margin-top:46px;font-size:12.5px;color:var(--muted)}
footer b{color:var(--clay-deep);font-weight:600}
.toolbar{position:fixed;top:20px;right:20px;z-index:100;display:flex;gap:8px}
.tb-btn{width:40px;height:40px;border:1px solid var(--line-2);border-radius:10px;background:var(--surface);color:var(--ink-2);cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .2s;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.tb-btn:hover{border-color:var(--clay);color:var(--clay);transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.12)}
.toc{position:fixed;top:80px;left:20px;z-index:90;width:180px;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 0;box-shadow:0 4px 16px rgba(0,0,0,.06);max-height:calc(100vh - 120px);overflow-y:auto}
.toc-title{font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--muted);font-weight:600;padding:0 16px 10px;border-bottom:1px solid var(--line)}
.toc-item{display:block;padding:8px 16px;font-size:13px;color:var(--ink-2);text-decoration:none;transition:all .15s;border-left:2px solid transparent}
.toc-item:hover{color:var(--clay);background:var(--well);border-left-color:var(--clay)}
.toc-item.active{color:var(--clay-deep);font-weight:600;border-left-color:var(--clay)}
.toc-num{display:inline-block;width:26px;color:var(--clay);font-size:12px;font-weight:600;font-feature-settings:"tnum"}
.wall-controls{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px;align-items:center}
.wall-search{flex:1;min-width:200px;padding:9px 14px;border:1px solid var(--line-2);border-radius:10px;background:var(--surface);color:var(--ink);font-size:14px;font-family:var(--sans);outline:none;transition:border-color .2s}
.wall-search:focus{border-color:var(--clay)}
.wall-search::placeholder{color:var(--muted)}
.wall-select{padding:9px 12px;border:1px solid var(--line-2);border-radius:10px;background:var(--surface);color:var(--ink);font-size:13px;font-family:var(--sans);cursor:pointer;outline:none}
.wall-select:focus{border-color:var(--clay)}
.wall-count{font-size:13px;color:var(--muted);margin-left:auto;white-space:nowrap}
.backtop{position:fixed;bottom:28px;right:24px;z-index:100;width:42px;height:42px;border:1px solid var(--line-2);border-radius:50%;background:var(--surface);color:var(--ink-2);cursor:pointer;display:flex;align-items:center;justify-content:center;opacity:0;transform:translateY(10px);transition:all .3s;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.backtop.show{opacity:1;transform:none}
.backtop:hover{border-color:var(--clay);color:var(--clay);transform:translateY(-2px)}
.donut-wrap{display:flex;align-items:center;gap:32px;margin:16px 0 24px;flex-wrap:wrap}
.donut{width:180px;height:180px;border-radius:50%;position:relative;flex-shrink:0;animation:donut-spin .8s cubic-bezier(.2,.8,.2,1) both;animation-delay:.3s}
.donut-hole{position:absolute;inset:25%;border-radius:50%;background:var(--surface);display:flex;flex-direction:column;align-items:center;justify-content:center;transition:background .3s}
.donut-total{font-family:var(--num);font-size:32px;font-weight:700;color:var(--ink);line-height:1}
.donut-cap{font-size:12px;color:var(--muted);margin-top:4px}
.donut-legend{display:flex;flex-direction:column;gap:8px;flex:1;min-width:160px}
.donut-leg{display:flex;align-items:center;gap:10px;font-size:13.5px;padding:4px 8px;margin:-4px -8px;border-radius:6px;transition:background .15s;cursor:default}
.donut-leg:hover{background:var(--well)}
.donut-leg i{width:10px;height:10px;border-radius:3px;flex-shrink:0}
.donut-name{flex:1;color:var(--ink-2)}
.donut-val{font-family:var(--num);color:var(--ink);font-weight:500;font-feature-settings:"tnum"}
.donut-val em{font-style:normal;color:var(--muted);margin-left:4px;font-size:12px}
.columns{display:flex;align-items:flex-end;gap:8px;height:200px;margin:16px 0 8px;padding:0 4px;border-bottom:1px solid var(--line)}
.col{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;min-width:0;height:100%;cursor:default;transition:transform .15s}
.col:hover{transform:scaleX(1.08)}
.col:hover .col-fill{filter:brightness(1.12)}
.col:hover .col-val{color:var(--clay-deep)}
.col-track{width:100%;flex:1;display:flex;align-items:flex-end;min-height:0}
.col-fill{width:100%;border-radius:6px 6px 0 0;background:linear-gradient(180deg,var(--clay),var(--clay-2));height:0;animation:col-grow 1s cubic-bezier(.2,.8,.2,1) both;transition:filter .15s}
.col-val{font-size:11px;color:var(--ink);font-weight:600;font-feature-settings:"tnum";white-space:nowrap;order:-1;transition:color .15s}
.col-label{font-size:11px;color:var(--muted);text-align:center;line-height:1.2;padding-top:6px}
.radar-wrap{display:flex;justify-content:center;margin:16px 0 24px}
.radar-svg{overflow:visible;max-width:100%}
.radar-ring{fill:none;stroke:var(--line);stroke-width:.6}
.radar-axis{stroke:var(--line);stroke-width:.5;stroke-dasharray:3,3}
.radar-fill{fill:rgba(193,95,60,.13);stroke:none;animation:radar-appear .8s ease both;animation-delay:.4s}
.radar-stroke{fill:none;stroke:var(--clay);stroke-width:2;stroke-linejoin:round;animation:radar-appear .8s ease both;animation-delay:.4s}
.radar-dot{fill:var(--clay);stroke:var(--surface);stroke-width:2.5}
.radar-label{font-size:11.5px;fill:var(--ink-2);font-family:var(--sans)}
.radar-pct{font-weight:600;fill:var(--clay)}
[data-theme="dark"] .radar-fill{fill:rgba(224,120,80,.13)}
.pill-cloud{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 24px}
.pill{display:inline-flex;align-items:center;gap:8px;padding:8px 16px;border-radius:999px;background:var(--clay);color:#fff;font-size:13px;transition:transform .15s}
.pill:hover{transform:scale(1.05)}
.pill b{font-weight:600}
.pill em{font-style:normal;font-size:11.5px;opacity:.8}
.copairs{display:flex;flex-direction:column;gap:6px;margin:16px 0 24px}
.copair{display:flex;align-items:center;gap:12px;padding:6px 10px;border-radius:8px;transition:background .15s;cursor:default;position:relative}
.copair:hover{background:var(--well)}
.copair-names{flex:0 0 auto;font-size:13px;white-space:nowrap}
.copair-link{display:inline-block;margin:0 4px;color:var(--clay);font-weight:700;font-size:14px}
.copair-bar{flex:1;height:8px;background:var(--well);border-radius:4px;overflow:hidden}
.copair-fill{display:block;height:100%;width:var(--w);background:var(--clay);border-radius:4px;animation:grow .6s ease-out both}
.copair-pct{flex:0 0 42px;text-align:right;font-size:12px;font-weight:600;font-family:var(--num);color:var(--clay-deep)}
.insight-list{display:flex;flex-direction:column;gap:14px;margin:16px 0}
.insight-card{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--clay);border-radius:12px;padding:18px 22px;transition:border-color .2s,box-shadow .2s}
.insight-card:hover{border-color:var(--clay);box-shadow:0 4px 16px rgba(0,0,0,.06)}
.insight-head{display:flex;align-items:center;gap:12px;margin-bottom:8px}
.insight-idx{font-family:var(--num);font-size:13px;font-weight:700;color:#fff;width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:50%;background:var(--clay);flex-shrink:0}
.insight-title{font-size:15px;font-weight:600;color:var(--ink);flex:1}
.insight-pct{font-family:var(--num);font-size:22px;font-weight:700;color:var(--clay);font-feature-settings:"tnum"}
.insight-body{margin:0;font-size:14px;line-height:1.7;color:var(--ink-2)}
.insight-body b{color:var(--clay-deep);font-weight:600}
[data-tip]{position:relative}
[data-tip]:hover::after{content:attr(data-tip);position:absolute;top:-30px;left:50%;transform:translateX(-50%);background:var(--ink);color:var(--paper);font-size:11px;padding:3px 10px;border-radius:6px;white-space:nowrap;pointer-events:none;z-index:9;opacity:0;animation:tip-in .15s .25s forwards}
.col[data-tip]:hover::after{top:auto;bottom:calc(100% + 4px);left:50%}
.w[data-tip]:hover::after{top:auto;bottom:calc(100% + 4px)}
@keyframes tip-in{to{opacity:1}}
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes grow{from{width:0}to{width:var(--w)}}
@keyframes col-grow{from{height:0}to{height:var(--h)}}
@keyframes donut-spin{from{opacity:0;transform:rotate(-90deg)}to{opacity:1;transform:rotate(0)}}
@keyframes radar-appear{from{opacity:0;transform:scale(.7)}to{opacity:1;transform:scale(1)}}
@media(prefers-reduced-motion:reduce){*{animation:none!important}.bar-fill,.gb-fill{width:var(--w)!important}.col-fill{height:var(--h)!important}}
@media(max-width:1200px){.toc{display:none}}
@media(max-width:560px){.page{padding:50px 18px 72px}.bar-label{flex-basis:108px;width:108px}.bonus{columns:1}.bonus-grid{grid-template-columns:1fr}.figure{min-width:50%}.wall-controls{flex-direction:column}.wall-search{min-width:100%}.donut-wrap{flex-direction:column;align-items:center}.columns{height:160px}.radar-wrap svg{max-width:260px}}
@media print{
  .toolbar,.toc,.backtop,.wall-controls,.job-cue,.grain{display:none!important}
  body{background:#fff;color:#1a1a1a;font-size:12px}
  .page{max-width:100%;padding:20px}
  .block{animation:none!important;break-inside:avoid;page-break-inside:avoid;padding:24px 0 6px}
  .bar-fill,.gb-fill{animation:none!important;width:var(--w)!important}
  .job{break-inside:avoid;page-break-inside:avoid;box-shadow:none!important;transform:none!important;border:1px solid #ddd}
  .job[open]{grid-column:auto}
  .cards{grid-template-columns:1fr 1fr}
  .callout{border:1px solid #ccc;background:#fafafa}
  .stats{border:1px solid #ddd}
  a{color:inherit;text-decoration:none}
  @page{margin:1.5cm}
}
</style></head>
<body>
<div class="grain"></div>
__TOOLBAR__
__TOC__
<div class="page">
__MASTHEAD__
__BODY__
<footer>本报告由 <b>boss-job-analyzer</b> 技能离线生成 · __FOOTNOTE__ · 薪资取月薪区间中点</footer>
</div>
__BACKTOP__
<script>
(function(){
  var toggle=document.getElementById('themeToggle');
  var html=document.documentElement;
  var saved=localStorage.getItem('boss-theme');
  if(saved)html.setAttribute('data-theme',saved);
  else if(window.matchMedia&&window.matchMedia('(prefers-color-scheme:dark)').matches)html.setAttribute('data-theme','dark');
  if(toggle)toggle.addEventListener('click',function(){
    var t=html.getAttribute('data-theme')==='dark'?'light':'dark';
    html.setAttribute('data-theme',t);
    localStorage.setItem('boss-theme',t);
  });
  var pdf=document.getElementById('pdfExport');
  if(pdf)pdf.addEventListener('click',function(){window.print()});
  var bt=document.getElementById('backtop');
  if(bt){
    window.addEventListener('scroll',function(){bt.classList.toggle('show',window.scrollY>400)});
    bt.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'})});
  }
  var tocItems=document.querySelectorAll('.toc-item');
  if(tocItems.length){
    var secs=[];
    tocItems.forEach(function(a){var id=a.getAttribute('href').slice(1);var el=document.getElementById(id);if(el)secs.push({el:el,a:a})});
    window.addEventListener('scroll',function(){
      var y=window.scrollY+120;var cur=null;
      secs.forEach(function(s){if(s.el.offsetTop<=y)cur=s});
      secs.forEach(function(s){s.a.classList.toggle('active',s===cur)});
    });
  }
  var search=document.getElementById('wallSearch');
  var filterExp=document.getElementById('filterExp');
  var filterEdu=document.getElementById('filterEdu');
  var sortBy=document.getElementById('sortBy');
  var countEl=document.getElementById('wallCount');
  if(search){
    var allCards=Array.from(document.querySelectorAll('.job'));
    allCards.forEach(function(c,i){c.setAttribute('data-idx',i)});
    function applyFilters(){
      var q=(search.value||'').toLowerCase();
      var exp=filterExp?filterExp.value:'';
      var edu=filterEdu?filterEdu.value:'';
      var shown=0;
      allCards.forEach(function(c){
        var text=(c.textContent||'').toLowerCase();
        var vis=(!q||text.indexOf(q)>=0)&&(!exp||c.getAttribute('data-exp')===exp)&&(!edu||c.getAttribute('data-edu')===edu);
        c.classList.toggle('hidden',!vis);
        if(vis)shown++;
      });
      if(countEl)countEl.textContent=shown+'/'+allCards.length+' 个岗位';
      if(sortBy&&sortBy.value!=='default')doSort();
    }
    function doSort(){
      if(!sortBy)return;var mode=sortBy.value;
      document.querySelectorAll('.cards').forEach(function(cont){
        var items=Array.from(cont.querySelectorAll('.job'));
        items.sort(function(a,b){
          if(mode==='default')
            return (parseInt(a.getAttribute('data-idx'),10)||0)-(parseInt(b.getAttribute('data-idx'),10)||0);
          var sa=parseFloat(a.getAttribute('data-salary'))||0;
          var sb=parseFloat(b.getAttribute('data-salary'))||0;
          return mode==='salary-desc'?sb-sa:sa-sb;
        });
        items.forEach(function(el){cont.appendChild(el)});
      });
    }
    search.addEventListener('input',applyFilters);
    if(filterExp)filterExp.addEventListener('change',applyFilters);
    if(filterEdu)filterEdu.addEventListener('change',applyFilters);
    if(sortBy)sortBy.addEventListener('change',function(){applyFilters();doSort()});
    applyFilters();
  }
})();
</script>
</body></html>"""


def main():
    ap = argparse.ArgumentParser(description="把 jobs.json 生成人才市场需求分析 HTML 报告")
    ap.add_argument("jobs_json", help="抓取得到的 jobs.json 路径")
    ap.add_argument("--out", default="report.html", help="输出 HTML 路径")
    ap.add_argument("--analysis", default=None,
                    help="Claude 第 2 步生成的 analysis.json(主路径:含每岗 tech/langs/duties 标注 + 可选 insights)")
    ap.add_argument("--insights", default=None,
                    help="(兼容旧用法)只含 insights 的 json;--analysis 里带 insights 时无需再传")
    args = ap.parse_args()

    with open(args.jobs_json, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    if not isinstance(jobs, list) or not jobs:
        sys.exit("jobs.json 应是非空数组")

    # 同一岗位经不同会话参数 URL 可能被抓成多条,按岗位 ID 去重,避免虚增样本。
    seen, deduped = set(), []
    for j in jobs:
        k = canon_url(j.get("detail_url", ""))
        if k and k in seen:
            continue
        seen.add(k)
        deduped.append(j)
    if len(deduped) != len(jobs):
        print(f"[dedup] jobs.json 含 {len(jobs) - len(deduped)} 条重复岗位(同 ID 不同会话参数),已去重", flush=True)
    jobs = deduped

    html_text = build_html(jobs, analysis_path=args.analysis, insights_path=args.insights)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html_text)
    print(f"OK: {len(jobs)} 个岗位 -> {args.out}")


if __name__ == "__main__":
    main()
