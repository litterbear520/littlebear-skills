#!/usr/bin/env bash
# sync-skill.sh — 把 ~/.claude/skills/<skill> 的源文件一键同步到本仓库并提交（可选 push）。
#
# 把"运行副本"(.claude/skills 里实际跑的那份，含累计的 experience.md / reviewed_matches.json)
# 镜像回 git 仓库，排除运行产物 runs/ 与 __pycache__。省去每次手动 copy。
#
# 用法:
#   ./sync-skill.sh <skill> ["提交信息"] [--push]
# 例:
#   ./sync-skill.sh worldcup-bet-advisor "feat: xxx" --push   # 同步+提交+推送
#   ./sync-skill.sh worldcup-bet-advisor "fix: yyy"           # 同步+提交，不推送
#   ./sync-skill.sh worldcup-bet-advisor                      # 用默认信息，不推送
#
# 环境变量 CLAUDE_SKILLS_DIR 可覆盖默认源目录（默认 ~/.claude/skills）。
set -euo pipefail

SKILL="${1:-}"
if [ -z "$SKILL" ]; then
  echo "用法: $0 <skill-name> [\"提交信息\"] [--push]" >&2
  exit 1
fi
shift

MSG=""
PUSH=0
for a in "$@"; do
  case "$a" in
    --push) PUSH=1 ;;
    *)      MSG="$a" ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/$SKILL"
DST="$REPO_ROOT/$SKILL"

[ -f "$SRC/SKILL.md" ] || { echo "✗ 源不是有效 skill(缺 SKILL.md): $SRC" >&2; exit 1; }
[ -d "$DST" ]          || { echo "✗ 仓库里没有这个 skill: $DST" >&2; exit 1; }

echo "[sync] $SRC"
echo "   →   $DST   (排除 runs/ 与 __pycache__)"

# 镜像：先清掉 DST 顶层除 runs/.git 外的内容，再从 SRC 拷回（排除 runs/__pycache__ 与本地私有文件）。
# 这样源里删掉的文件，DST 也会同步删掉（真镜像，非只覆盖）。
# 本地私有(gitignore)文件不回传仓库：experience.local.md（本机经验）、reviewed_matches.json（本机进度账本）。
find "$DST" -mindepth 1 -maxdepth 1 ! -name 'runs' ! -name '.git' -exec rm -rf {} +
tar -C "$SRC" --exclude='./runs' --exclude='*__pycache__*' --exclude='*.local.md' --exclude='*reviewed_matches.json' -cf - . | tar -C "$DST" -xf -

cd "$REPO_ROOT"
git add -A "$SKILL"

if git diff --cached --quiet -- "$SKILL"; then
  echo "[sync] 无改动，跳过提交。"
  exit 0
fi

echo "[sync] 改动文件:"
git diff --cached --name-status -- "$SKILL" | sed 's/^/   /'

[ -z "$MSG" ] && MSG="chore($SKILL): sync from .claude"
git commit -q -m "$MSG" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
echo "[sync] ✓ 已提交: $MSG"

if [ "$PUSH" = "1" ]; then
  BR="$(git rev-parse --abbrev-ref HEAD)"
  git push -q origin "$BR"
  echo "[sync] ✓ 已 push 到 origin/$BR"
else
  echo "[sync] (未 push；想自动推送加 --push)"
fi
