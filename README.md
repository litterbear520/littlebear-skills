# 🧸 Littlebear Skills

> 小熊（littlebear）自制的 [Claude Code / Claude Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) 合集。
> 每个 skill 都是一套「把口语需求 → 变成可复现产物」的工作流，开箱即用，持续迭代。

把日常重复的、需要"抓数据 + 多步判断 + 出精美报告"的活儿，封装成一句话就能触发的技能。脚本管确定性、模型管判断，结果可复现、省 token。

---

## 📋 目录

| Skill | 一句话介绍 | 详解 |
| --- | --- | --- |
| 🏆 [worldcup-bet-advisor](./worldcup-bet-advisor) | 世界杯竞彩「玩法建议」：综合多个 AI 预测 + 实时倍率去水找价值，给稳健/平衡/激进三档方案，产出 Anthropic 风格单文件 HTML 报告 | [↓ 跳转](#-worldcup-bet-advisor世界杯竞彩玩法建议) |

> 更多技能持续添加中……

---

## 📦 安装方式

### 方式一：让 Claude 帮你装（推荐）

在 Claude Code 里直接说：

```
帮我安装这个 skill：https://github.com/litterbear520/littlebear-skills/tree/main/worldcup-bet-advisor
```

Claude 会把对应技能目录拉到本地并放进 `~/.claude/skills/`，下次触发即可用。

### 方式二：手动安装

```bash
# 1. 克隆仓库
git clone https://github.com/litterbear520/littlebear-skills.git

# 2. 把想要的技能目录复制到 Claude 的 skills 目录
#    macOS / Linux
cp -r littlebear-skills/worldcup-bet-advisor ~/.claude/skills/

#    Windows (PowerShell)
Copy-Item -Recurse littlebear-skills\worldcup-bet-advisor "$HOME\.claude\skills\"
```

复制完成后重启会话，对 Claude 描述需求即可自动触发对应技能。

---

## ✨ Skills

### 🏆 worldcup-bet-advisor（世界杯竞彩玩法建议）

把「最近几场世界杯怎么买」这种口语需求，变成一份**三档玩法方案** + 一份 **Anthropic 风格的单文件 HTML 报告**。

**它做什么**

- 综合多个 AI agent（默认 Claude + DeepSeek，可多选）对比赛的预测比分与讨论
- 叠加当天**全部玩法**的实时倍率（胜平负 / 让球 / 比分 / 总进球 / 半全场）
- **去水校验**找价值点与陷阱点，给出**稳健 / 平衡 / 激进**三档方案（单关、串关、比分等）
- **复盘驱动进化**：每次先做赛后复盘，把"哪个模型/哪类信号更准、买法该怎么调"沉淀进经验库，下次回灌——越打越准
- 产出一份内置双主题、吸顶导航、渐进披露、可导出 PDF 的单文件 HTML 报告

**什么时候会触发**

当你问「今天/这几场买哪个」「怎么串」「单关还是串关」「比分推荐」「玩法建议」「倍率」「世界杯竞彩」，或想让它综合 AI 预测 + 实时倍率给投注思路时。
（只查赛程、问已结束比赛的比分、看积分榜等与"玩法/投注"无关的话题不会触发。）

**前置要求**

- Python 3（运行抓取/合并/出报告的脚本）
- 浏览器环境用于打开报告（依赖 web-access skill 的 CDP，或 chrome-devtools MCP）

**了解更多**：[SKILL.md](./worldcup-bet-advisor/SKILL.md) ｜ 决策口径见 [playbook.md](./worldcup-bet-advisor/references/playbook.md)

> ⚠️ 本技能产出**不构成投注建议**，理性娱乐、量力而行。

---

## 🌟 关于

- 作者：[@litterbear520](https://github.com/litterbear520)
- 这些技能是个人在用 Claude Code 过程中沉淀出来的工作流，欢迎试用、提 issue、提建议。
- 仓库会持续迭代，加入更多自制技能。

## 📄 License

[MIT](./LICENSE)
