# 🧸 Littlebear Skills

> 小熊（littlebear）自制的 [Claude Code / Claude Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) 合集。
> 每个 skill 都是一套「把口语需求 → 变成可复现产物」的工作流，开箱即用，持续迭代。

把日常重复的、需要"抓数据 + 多步判断 + 出精美报告"的活儿，封装成一句话就能触发的技能。脚本管确定性、模型管判断，结果可复现、省 token。

---

## 📋 目录

| Skill | 一句话介绍 | 详解 |
| --- | --- | --- |
| 🏆 [worldcup-bet-advisor](./worldcup-bet-advisor) | 世界杯竞彩「玩法建议」：综合多个 AI 预测 + 实时倍率去水找价值，给稳健/平衡/激进三档方案，产出 Anthropic 风格单文件 HTML 报告 | [↓ 跳转](#-worldcup-bet-advisor世界杯竞彩玩法建议) |
| 💼 [boss-job-analyzer](./boss-job-analyzer) | BOSS直聘岗位/市场分析：复用你 Chrome 登录态抓岗位，Claude 读 JD 标技能、脚本做确定性统计，产出 Anthropic 风格单文件 HTML 报告（技术栈/语言/学历薪资/加分项 + 可点开原文的岗位卡片墙） | [↓ 跳转](#-boss-job-analyzerboss直聘岗位分析) |

> 更多技能持续添加中……

---

## 📦 安装方式

这些技能用标准的 [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills)（`SKILL.md`）格式，**与具体工具无关**——Claude Code / Cursor / Codex / OpenCode 等都能用。三选一：

### 方式一：`npx skills`（跨工具一键，推荐）

[`npx skills`](https://github.com/vercel-labs/skills) 是开放的 Agent Skills 安装器，支持 Claude Code、Cursor、Codex 等 70+ 种 agent，会自动放到**你当前工具**对应的 skills 目录：

```bash
# 交互式向导会列出本仓库里的技能（worldcup-bet-advisor 等）让你勾选
npx skills add litterbear520/littlebear-skills
```

### 方式二：让 Claude 帮你装

在 Claude Code 里直接说：

```
帮我安装这个 skill：https://github.com/litterbear520/littlebear-skills/tree/main/worldcup-bet-advisor
```

Claude 会把对应技能目录拉到本地并放进 `~/.claude/skills/`，下次触发即可用。

### 方式三：手动安装

```bash
# 1. 克隆仓库
git clone https://github.com/litterbear520/littlebear-skills.git

# 2. 把想要的技能目录复制到对应工具的 skills 目录，例如 Claude Code：
#    macOS / Linux
cp -r littlebear-skills/worldcup-bet-advisor ~/.claude/skills/

#    Windows (PowerShell)
Copy-Item -Recurse littlebear-skills\worldcup-bet-advisor "$HOME\.claude\skills\"
```

> Cursor / Codex 等的技能目录与 Claude Code 不同，推荐用**方式一**让 `npx skills` 自动放对位置。复制完成后重启会话，对 Agent 描述需求即可自动触发对应技能。

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

- Python 3（运行抓取/合并/出报告的脚本）——仅用标准库，无需 `pip install`
- **[web-access](https://github.com/eze-is/web-access) 技能**：用它的 CDP 把报告开到你**日常的 Chrome**（直连被反爬阻断时也用它兜底抓数据）。跨工具一键装：

  ```bash
  npx skills add eze-is/web-access
  ```

  没装也行——触发技能时它会先问你要不要装。

**了解更多**：[SKILL.md](./worldcup-bet-advisor/SKILL.md) ｜ 决策口径见 [playbook.md](./worldcup-bet-advisor/references/playbook.md)

> ⚠️ 本技能产出**不构成投注建议**，理性娱乐、量力而行。

---

### 💼 boss-job-analyzer（BOSS直聘岗位分析）

把「看看 BOSS 上某类岗位都要什么」这种口语需求，变成一份**岗位数据** + 一份 **Anthropic 博客风的单文件 HTML 报告**。

**它做什么**

- 复用你日常 Chrome 的登录态，通过 web-access 的 CDP 像人一样浏览、抓取 BOSS直聘 某类岗位的真实 JD（岗位名 / 薪资 / 公司 / 经验学历 / 技能标签 / 职责要求原文）
- **Claude 读 JD 标技能、脚本做统计**：模型逐岗标注技术栈/语言/职责（适配任意岗位、不靠写死词典），脚本确定性地算占比、共现、薪资分布——可复现、不失真
- 产出单文件报告：顶部概览 + 学习建议 callout + 5 个分析维度（技术栈雷达 / 语言占比 / 学历薪资分布 / 加分项 / 市场规律洞察）+ **可点开看 BOSS 原文的岗位卡片墙**（带搜索、经验学历筛选、薪资排序）
- 内置双主题、浮动目录、可导出 PDF，图表全手写 CSS/SVG、零图表库

**什么时候会触发**

当你同时提到 BOSS / boss直聘 / zhipin 和某类岗位，想了解要求、薪资、技术栈、加分项、市场行情、技术趋势、求职准备方向、技能学习路线等任何一项时。

**前置要求**

- Python 3（仅标准库，无需 `pip install`）
- **[web-access](https://github.com/eze-is/web-access) 技能（硬依赖）**：BOSS 反爬强，必须用它的 CDP 复用你 Chrome 的登录态抓取 + 打开报告。跨工具一键装：

  ```bash
  npx skills add eze-is/web-access
  ```

  没装也行——触发技能时它会先问你要不要装。

**了解更多**：[SKILL.md](./boss-job-analyzer/SKILL.md) ｜ 站点抓取口径见 [zhipin-site-notes.md](./boss-job-analyzer/references/zhipin-site-notes.md)

> ⚠️ 本技能复用用户合法登录态、像人一样浏览，请遵守站点条款、合理控制抓取频率。

---

## 🌟 关于

- 作者：[@litterbear520](https://github.com/litterbear520)
- 这些技能是个人在用 Claude Code 过程中沉淀出来的工作流，欢迎试用、提 issue、提建议。
- 仓库会持续迭代，加入更多自制技能。

## 📄 License

[MIT](./LICENSE)
