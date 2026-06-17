<div align="center">

# Littlebear Skills

**把口语需求变成可复现产物的 Agent Skills 合集**

抓数据 · 多步判断 · 出精美报告——脚本管确定性、模型管判断，结果可复现、省 token。

[![license](https://img.shields.io/badge/license-MIT-C15F3C?style=flat-square)](./LICENSE) ![skills](https://img.shields.io/badge/skills-3-C15F3C?style=flat-square) [![Agent Skills](https://img.shields.io/badge/standard-Agent_Skills-3b3b3b?style=flat-square)](https://agentskills.io)

适用于 Claude Code · Cursor · Codex · OpenCode 等支持 Agent Skills 的工具

</div>

---

## 什么是 Skills

Skills 是一组「指令 + 脚本 + 资源」的文件夹，Agent（如 Claude）按 `SKILL.md` 里写明的触发时机自动加载，把某类专门任务用**可复现**的方式做好。本仓库技能遵循 [Agent Skills](https://agentskills.io) 开放标准，与具体工具无关——同一份 `SKILL.md`，Claude Code、Cursor、Codex、OpenCode 都能装。

## 技能一览

| 技能 | 简介 | 依赖 |
| :-- | :-- | :-- |
| **[worldcup-bet-advisor](./worldcup-bet-advisor)** | 世界杯竞彩玩法建议——多 AI 预测 + 实时倍率去水找价值，给稳健 / 平衡 / 激进三档方案 | `web-access` |
| **[boss-job-analyzer](./boss-job-analyzer)** | BOSS直聘岗位 / 市场分析——抓岗位、读 JD 标技能、出技术栈与学历薪资分布 | `web-access` |
| **[code-teacher](./code-teacher)** | 读懂任何陌生代码库——先看地图画依赖图，再按依赖自底向上读，附讲解级 HTML 架构图 | 无 |

> worldcup / boss 两个技能产出**内置双主题、可导出 PDF 的 Anthropic 风单文件 HTML 报告**；code-teacher 产出**讲解级 HTML 架构图**并带你按依赖顺序读懂源码。更多技能持续添加中。

## 安装

技能采用标准 [Agent Skills](https://agentskills.io)（`SKILL.md`）格式，与具体工具无关。三选一：

**① `npx skills`（跨工具一键，推荐）**

```bash
npx skills add litterbear520/littlebear-skills
```

[`npx skills`](https://github.com/vercel-labs/skills) 是开放的 Agent Skills 安装器，支持 70+ 种 agent；交互向导会列出本仓库技能让你勾选，自动放进当前工具的 skills 目录。

**② 让 Claude 代装**

在 Claude Code 里直接说：

```
帮我安装这个 skill：https://github.com/litterbear520/littlebear-skills/tree/main/worldcup-bet-advisor
```

**③ 手动安装**

```bash
git clone https://github.com/litterbear520/littlebear-skills.git
# 复制到对应工具的 skills 目录，例如 Claude Code：
cp -r littlebear-skills/worldcup-bet-advisor ~/.claude/skills/                      # macOS / Linux
Copy-Item -Recurse littlebear-skills\worldcup-bet-advisor "$HOME\.claude\skills\"   # Windows
```

> **关于依赖 `web-access`** — 技能用它的 CDP 复用你日常 Chrome 抓数据 / 打开报告。没装也行：触发时会先问你要不要装，或自己先装好：
> ```bash
> npx skills add eze-is/web-access
> ```

## 技能详解

### worldcup-bet-advisor

> 不替你下注——把一堆球评和实时赔率揉碎了喂给你，只帮你看清哪儿有价值、哪儿是坑。

把「最近几场世界杯怎么买」变成一份**三档玩法方案** + 一份单文件 HTML 报告。

- 综合多个 AI agent（默认 Claude + DeepSeek）的预测比分与讨论
- 叠加当天全部玩法的实时倍率（胜平负 / 让球 / 比分 / 总进球 / 半全场），**去水校验**找价值点与陷阱点
- 给出**稳健 / 平衡 / 激进**三档方案（单关、串关、比分等）
- **复盘驱动进化**——每次先做赛后复盘，沉淀「哪个模型 / 哪类信号更准」，下次回灌，越打越准

**触发**：问「今天这几场买哪个」「怎么串」「比分推荐」「玩法建议」「倍率」等；仅查赛程 / 看比分 / 积分榜不触发。

**依赖**：Python 3（标准库）+ [web-access](https://github.com/eze-is/web-access)。

**了解更多**：[SKILL.md](./worldcup-bet-advisor/SKILL.md) · [决策口径 playbook.md](./worldcup-bet-advisor/references/playbook.md)

> 产出不构成投注建议，理性娱乐、量力而行。

### boss-job-analyzer

> 别再一条条手翻 JD——让 Claude 替你读完几十条招聘，告诉你这行到底要什么、该补什么。

把「看看 BOSS 上某类岗位都要什么」变成一份**岗位数据** + 一份单文件 HTML 报告。

- 复用你 Chrome 登录态，通过 web-access 的 CDP 抓取某类岗位真实 JD（薪资 / 公司 / 经验学历 / 技能标签 / 职责要求原文）
- **Claude 读 JD 标技能、脚本做统计**——模型逐岗标注技术栈 / 语言 / 职责（适配任意岗位、不靠写死词典），脚本确定性算占比、共现、薪资分布
- 报告含 5 个分析维度 + 学习建议 + **可点开看 BOSS 原文的岗位卡片墙**（搜索 / 经验学历筛选 / 薪资排序）

**触发**：同时提到 BOSS / zhipin 和某类岗位，想了解要求、薪资、技术栈、市场行情、求职准备方向等。

**依赖**：Python 3（标准库）+ [web-access](https://github.com/eze-is/web-access)（硬依赖——BOSS 反爬强，必须走它的 CDP）。

**了解更多**：[SKILL.md](./boss-job-analyzer/SKILL.md) · [抓取口径 zhipin-site-notes.md](./boss-job-analyzer/references/zhipin-site-notes.md)

> 复用合法登录态、像人一样浏览，请遵守站点条款、合理控制抓取频率。

### code-teacher

> 别再从 app.py 一行行硬啃——先给你画张地图，再按依赖从叶子读到入口，每读一个模块它的依赖你都已经见过。

把「这项目我看不懂、不知道从哪读」变成一套可复用的读码流程 + 一张讲解级的 HTML 架构图。

- **先看地图**：读 README / 找入口 / 追 import，**产出并打开一张清晰的 HTML 架构图**（看得清有哪些工具、哪些类、每个类的方法与属性、谁依赖谁）
- **找叶子、自底向上读**：在图上标出不依赖项目内其他模块的文件，从叶子沿依赖反向逐个读，自然走出「基础设施 → 核心服务 → 组装入口」三层
- **本质是按拓扑排序读代码**：每个模块被读到时，它的依赖你都已经理解；反过来也是从零搭项目的高效写码顺序
- 用「要加功能 X 得改哪些文件、按什么顺序改」自测是否真懂

**触发**：说「看不懂这个项目」「不知道从哪开始读代码」「帮我理一下这个仓库结构」「这个项目怎么跑起来的」「怎么读源码」「新接手一个项目怎么上手」等即触发。

**依赖**：无（纯方法 + 内置 HTML 生成，不依赖外部工具）。

**了解更多**：[SKILL.md](./code-teacher/SKILL.md) · [完整示例 worked-example.md](./code-teacher/references/worked-example.md)

## 关于 & 反馈

这些是个人在用 Claude Code 过程中沉淀下来的工作流。欢迎试用，也欢迎在 [Issues](https://github.com/litterbear520/littlebear-skills/issues) 提 bug、提建议、求新技能。

作者 [@litterbear520](https://github.com/litterbear520) · 仓库持续迭代、加入更多自制技能。

## License

[MIT](./LICENSE)
