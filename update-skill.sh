#!/usr/bin/env bash
# update-skill.sh — 技能启动时检查 GitHub 有没有新版本；有且安全就 pull 并同步到 .claude 运行副本。
#
# 方向：GitHub --pull--> 本仓库 --镜像--> ~/.claude/skills/<skill>（与 sync-skill.sh 相反）。
# 设计要点：
#   - fail-open：连不上 GitHub / 没装仓库 → 静默跳过、用本地版，绝不阻塞用户的正事。
#   - 不覆盖本地累计经验：运行副本相对仓库有未同步改动(如没推的 experience.md)时，
#     提示先回传、不自动拉，避免把本地学习覆盖掉。
#
# 用法: ./update-skill.sh <skill>
# 退出码: 0=已是最新/已成功更新/fail-open;  2=有更新但需用户决策(本地未同步 或 ff 失败)。
set -uo pipefail   # 故意不开 -e：自己控流程以保证 fail-open

SKILL="${1:-}"
[ -z "$SKILL" ] && { echo "用法: $0 <skill-name>" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/$SKILL"
DST="$REPO_ROOT/$SKILL"

[ -d "$DST" ] || { echo "[update] 仓库无此 skill，跳过"; exit 0; }

# 1. fetch（连不上 → fail-open）
if ! git -C "$REPO_ROOT" fetch -q origin 2>/dev/null; then
  echo "[update] 连不上 GitHub，用本地版继续"; exit 0
fi

BR="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)"
git -C "$REPO_ROOT" rev-parse --verify -q "origin/$BR" >/dev/null 2>&1 \
  || { echo "[update] 无 origin/$BR，跳过"; exit 0; }
BEHIND="$(git -C "$REPO_ROOT" rev-list --count "$BR..origin/$BR" 2>/dev/null || echo 0)"

if [ "${BEHIND:-0}" -eq 0 ]; then
  echo "[update] 已是最新版"; exit 0
fi
echo "[update] GitHub 有 $BEHIND 个新提交可更新"

# 2. 本地未同步检查：运行副本 vs 仓库(pull 前)，或仓库工作区有未提交改动 → 不自动覆盖
LOCALDIFF="$(diff -rq --exclude=runs --exclude=__pycache__ --exclude=.git --exclude='*.local.md' --exclude=reviewed_matches.json "$RUNTIME" "$DST" 2>/dev/null | head -5)"
REPODIRTY="$(git -C "$REPO_ROOT" status --porcelain -- "$SKILL" 2>/dev/null | head -5)"
if [ -n "$LOCALDIFF" ] || [ -n "$REPODIRTY" ]; then
  echo "[update] ⚠ 本地有未同步改动（很可能是累计的经验 / 没推送的修改），不自动拉以免覆盖："
  [ -n "$LOCALDIFF" ] && echo "$LOCALDIFF" | sed 's/^/   /'
  [ -n "$REPODIRTY" ] && echo "$REPODIRTY" | sed 's/^/   repo: /'
  echo "[update]   建议：先  ./sync-skill.sh $SKILL \"...\" --push  回传，再重跑本检查。"
  exit 2
fi

# 3. 安全：ff-only 拉取 + 镜像 仓库 -> 运行副本（排除 runs/）
if ! git -C "$REPO_ROOT" pull --ff-only -q origin "$BR" 2>/dev/null; then
  echo "[update] ⚠ ff-only 拉取失败（本地与远端分叉），跳过、用本地版"; exit 2
fi
# 覆盖式同步(overlay)：把仓库的代码/种子盖到运行副本，但【不删】本地私有文件。
# experience.local.md / reviewed_matches.json 不在仓库里，自然不会被覆盖；故不做 pre-rm。
# 注意：上游若删除/重命名了文件，运行副本里的旧文件不会自动消失（罕见，必要时手动清）。
if tar -C "$DST" --exclude='./runs' --exclude='*__pycache__*' --exclude='./.git' -cf - . | tar -C "$RUNTIME" -xf -; then
  echo "[update] ✓ 已更新到最新并同步到运行副本（保留了本地经验；请重新读取 SKILL.md / 脚本后再继续）"
  exit 0
else
  echo "[update] ⚠ 拉取成功但镜像到运行副本失败，请手动检查 $RUNTIME"; exit 2
fi
