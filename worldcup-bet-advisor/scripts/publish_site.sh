#!/usr/bin/env bash
# 发布当天报告到收益站点（私有模式：数据只在本地 + Vercel，不进 GitHub）。
#
# 做三件事：① 把 build_report.py 生成的 report.html 原样拷进站点 public/reports/<日期>.html
# ② 用 export_site_data.py 登记当天有报告 +（可选）回填上一期的票与盈亏到 data/
# ③ 可选 --deploy：cd web && npx vercel --prod，把本地文件（含 gitignore 的报告/数据）推上线。
#
# 报告本体一字不改——站点用 iframe 原样嵌入；Next.js 只多了日期切换 + 收益仪表盘。
# 一次性设置（vercel login / link）见 references/site-deploy.md；也可改用官方 deploy-to-vercel 技能部署。
#
# 用法：
#   bash scripts/publish_site.sh --report "$WS/report.html" --analysis "$WS/analysis.json" \
#        [--date 2026-06-20] [--retro "$PREV/retro.json"] [--deploy]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WEB="$(cd "$HERE/../web" && pwd)"

# 选一个真正能跑的 Python。Mac/Linux 一般是 python3；但 Windows(Git Bash) 的 python3 常是
# 失效的应用商店占位符——command -v 找得到、真跑却报错——所以逐个候选「试运行」，取第一个跑通的。
PY=""
for _c in python3 python; do
  if command -v "$_c" >/dev/null 2>&1 && "$_c" -c 'import sys' >/dev/null 2>&1; then
    PY="$_c"; break
  fi
done
[ -n "$PY" ] || { echo "[publish] 找不到可用的 Python（试过 python3 / python）" >&2; exit 1; }

ANALYSIS=""; RETRO=""; DATE=""; REPORT=""; DEPLOY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --analysis) ANALYSIS="$2"; shift 2;;
    --retro)    RETRO="$2";    shift 2;;
    --date)     DATE="$2";     shift 2;;
    --report)   REPORT="$2";   shift 2;;
    --deploy)   DEPLOY=1;      shift;;
    *) echo "未知参数：$1" >&2; exit 2;;
  esac
done

# 日期：优先 --date，否则从 analysis.meta.date 解析
if [ -z "$DATE" ] && [ -n "$ANALYSIS" ]; then
  DATE="$("$PY" -c "import json,re,sys; d=json.load(open(sys.argv[1])); m=re.match(r'(\d{4}-\d{2}-\d{2})', str(d.get('meta',{}).get('date',''))); print(m.group(1) if m else '')" "$ANALYSIS" 2>/dev/null || true)"
fi

# ① 拷报告
if [ -n "$REPORT" ]; then
  [ -n "$DATE" ] || { echo "[publish] 复制报告需要 --date（或可解析的 --analysis）" >&2; exit 1; }
  mkdir -p "$WEB/public/reports"
  cp "$REPORT" "$WEB/public/reports/$DATE.html"
  echo "[publish] 报告 -> public/reports/$DATE.html"
fi

# ② 写仪表盘数据
mkdir -p "$WEB/data"
if [ -n "$DATE" ] || [ -n "$ANALYSIS" ]; then
  "$PY" "$HERE/export_site_data.py" day \
    ${ANALYSIS:+--analysis "$ANALYSIS"} ${DATE:+--date "$DATE"} --site-data "$WEB/data"
fi
if [ -n "$RETRO" ]; then
  "$PY" "$HERE/export_site_data.py" settle --retro "$RETRO" --site-data "$WEB/data"
fi

# ③ 部署
if [ "$DEPLOY" -eq 1 ]; then
  echo "[publish] 部署到 Vercel：npx vercel --prod"
  ( cd "$WEB" && npx vercel --prod )
  echo "[publish] 已部署。"
else
  echo "[publish] 数据已就绪（未部署）。"
  echo "[publish] 部署： cd \"$WEB\" && npx vercel --prod    （或用官方 deploy-to-vercel 技能）"
fi
