# 分发友好的自更新设计（worldcup-bet-advisor）

日期：2026-06-23 · 状态：已批准，待实现

## 背景与问题

现有自更新（SKILL.md 第 -1 步 + 仓库根 `update-skill.sh` / `sync-skill.sh`）依赖「本机存在一个 clone 的 git 仓库」，且探测路径硬编码 `/d/littlebear-skills`（作者本地路径）。但三种安装方式（`npx skills` / 让 Claude 代装 / `git clone` 后 `cp -r`）都把 skill 子目录**纯拷贝**进 `~/.claude/skills/`，不带 `.git`、也不带仓库根的两个脚本（它们在 monorepo 根，不随技能分发）。

后果：

- **作者机**（junction → 仓库工作区，有 `.git`）：自更新有效。
- **任何第三方**：自更新 100% fail-open 跳过，技能冻结在安装那一刻，要更新只能删了重装。

## 目标

让任何方式安装的使用者，在使用时自动跟上作者的 GitHub 更新、无需重装；作者自己的开发体验（junction + `git pull` 即时生效）保持不变。

## 决策摘要（已与作者确认）

| 维度 | 决策 |
| :-- | :-- |
| 实现形态 | 技能自带 `scripts/self_update.py`（纯 Python 标准库，跨平台），作为第 -1 步唯一入口 |
| 更新行为 | 自动拉取覆盖，**完成后告知一句** |
| 检查频率 | 每次触发检查，但**每日缓存防抖**（每天最多一次） |
| 版本判定 | GitHub commits API 带 `path` 过滤，比对该技能目录最新 commit `sha`（作者不维护版本号） |
| 旧脚本清理 | **删除** `update-skill.sh` + `sync-skill.sh`，回归原生 git（作者回传用 `git add/commit/push`） |
| 首次无缓存 | **下载对齐一次**（保证装了即最新） |
| 作者机行为 | 检测到在 git 工作区 → 脚本自己 `git pull --ff-only`，工作区脏则只提示不强拉（取代 `update-skill.sh`） |

## 架构与数据流

```
python scripts/self_update.py
├─ 在 git 工作区？ (git rev-parse --is-inside-work-tree)
│   └─ YES（作者机 junction / clone 用户）→【git 分支】
│        fetch → behind=0? "= up-to-date"
│                       : 工作区对本 skill 路径脏? "⚠ dirty（先 commit/push）"
│                       : git pull --ff-only → "✓ updated (git pull)"
│                         （ff 失败=分叉 → "~ skipped（分叉，用本地版）"）
└─ NO（第三方纯拷贝）→【自拉分支】
     缓存防抖(last_check_date==今天?) → "~ skipped (checked today)"
       否 → 远端 sha(commits API) → 失败? "~ skipped (offline)"（写当日日期）
              == 本地 current_sha? "= up-to-date"（更新日期）
              != → 下 tar.gz/<sha> → 只解 */worldcup-bet-advisor/ → overlay 覆盖
                   → 写缓存(current_sha,today) → "✓ updated (<sha7>)"
```

## self_update.py 内部结构（便于测试）

- 定位：`SKILL_DIR = Path(__file__).resolve().parents[1]`；常量 `OWNER/REPO/SKILL_NAME` 硬编码
- 可注入/可单测的函数：
  - `is_git_worktree(path) -> bool`
  - `git_update(skill_dir) -> str`（git 分支；返回输出契约字符串）
  - `remote_latest_sha(timeout) -> str|None`（commits API）
  - `download_subtree(sha, dest)`（下 tarball、只解子树、overlay 覆盖、保留私有文件）
  - `read_cache()/write_cache()`（`.self_update.json`）
  - `self_update()` 主流程
- **输出契约**（stdout 行首标记，供 SKILL.md/Claude 判断）：`✓ updated` / `= up-to-date` / `~ skipped` / `⚠ dirty`
- **fail-open**：网络/解析/写入任何异常一律捕获 → 用当前版、非阻塞；offline 也写当日日期避免反复重试

## 覆盖时保留的本机私有文件（overlay 不预删、不覆盖）

`runs/`、`references/experience.local.md`、`references/reviewed_matches.json`、`.self_update.json`、`**/__pycache__`

> overlay 语义：解包写入、不预删目标。本机私有文件天然保留；代价是「上游删除/重命名的文件不会在运行副本里消失」（罕见，可接受，注释说明）。

## 影响的文件

- **新增** `worldcup-bet-advisor/scripts/self_update.py`
- **新增** `worldcup-bet-advisor/docs/2026-06-23-self-update-design.md`（本文件）
- **改** `worldcup-bet-advisor/SKILL.md`：第 -1 步重写为调 `self_update.py`、去掉硬编码 `/d/littlebear-skills`；心法「自更新优先」措辞同步
- **改** `.gitignore`：增 `**/.self_update.json`
- **删** `update-skill.sh`、`sync-skill.sh`

## 实现步骤

1. 写 `self_update.py`（网络函数可注入）
2. 改 SKILL.md 第 -1 步 + 心法
3. 改 `.gitignore`
4. 删两个根脚本
5. 测试：git 分支（临时仓库+bare remote）、自拉分支（本地假 tarball）、fail-open
6. 提交

## 测试策略

- **git 分支**：临时 git 仓库 + bare remote 造「远端领先 1 提交」，验证 ff-pull 生效、脏检查拦截、behind=0 跳过（复用已验证过的隔离手法）
- **自拉分支**：把 `remote_latest_sha` / tarball 下载抽成可注入函数；用本地构造的 `repo-<sha>/worldcup-bet-advisor/...` 假 `tar.gz` 喂入，验证只解子树、保留本机私有文件、写缓存、输出契约
- **fail-open**：注入坏 URL/超时 → 用当前版、不报错、写当日日期

## 风险与权衡

- **overlay 不删上游已删文件**：罕见，可接受（与原 update-skill.sh 行为一致）
- **GitHub 未认证 rate limit 60/h**：每日缓存远低于；fail-open
- **自动执行远端代码的信任**：固定 `OWNER/REPO`、仅 `https` GitHub 官方域；第三方安装本技能即已信任来源
- **首次下载对齐**：第三方首次跑多几秒
