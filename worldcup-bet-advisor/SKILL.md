---
name: worldcup-bet-advisor
description: 世界杯竞彩"玩法建议"分析。综合多个 AI agent（Claude、DeepSeek 等"嘉豪世界杯预测"模型）对比赛的预测比分与讨论，叠加当天全部玩法（胜平负/让球/比分/总进球/半全场）的实时倍率，去水校验找价值，最终给出稳健/平衡/激进三档玩法方案（单关、串关、比分等），并产出一份 Anthropic 风格的单文件 HTML 报告。当用户想预测最近几场世界杯比赛结果、问"今天/这几场买哪个""怎么串""单关还是串关""比分推荐""玩法建议""倍率""嘉豪世界杯预测""世界杯竞彩"，或想让你综合 agent 预测+实时倍率给投注思路时，**务必触发本 skill**——即使用户只说"看看今天世界杯怎么玩""帮我分析下这几场"也应触发，不要自己凭空猜结果。但若用户只是查赛程/开赛时间、问已结束比赛的比分或战报、了解某支球队/球员资讯、看积分榜等与"玩法/投注"无关的世界杯话题，则不属于本 skill，按普通查询处理即可。
allowed-tools: Bash, Read, Write, Edit, Skill, AskUserQuestion, ToolSearch, mcp__chrome-devtools__new_page, mcp__chrome-devtools__navigate_page, mcp__chrome-devtools__list_pages
---

# 世界杯玩法建议（多 agent 预测 × 实时倍率）

把"最近几场世界杯怎么买"这种口语需求，变成一份**三档玩法方案**（稳健单关 / 平衡单关+小串 / 激进串关博高赔）+ 一份 Anthropic 风格的单文件 HTML 报告。

## 心法

- **讨论为主、倍率校验**：先看用户勾选的 agent（默认 Claude+DeepSeek）的讨论方向，再用实时倍率的去水概率找性价比/价值点。决策口径全在 `references/playbook.md`。
- **脚本管确定性、模型管判断**：抓取、解析倍率、去水算概率、串关连乘 → 脚本；读讨论、下结论、定三档方案 → 你（模型）。这样可复现、省 token。
- **直连优先、CDP 兜底**：两侧接口都能直接拉（脚本默认 urllib）。只有被阻断时才走 web-access 的 CDP，并**先向用户展示反爬须知**。
- **数据细节先读 `references/data-sources.md`**：两站接口、字段字典（sw/sd/sl 比分、t 总进球、ht 半全场、single* 单关标记）、跨站队名匹配都在里面。开工前读它。
- **复盘驱动进化**：每次触发先做赛后复盘（第 R 步），把"哪个模型/哪类信号更准、买法该怎么调"沉淀进 `references/experience.md`，下次分析回灌——越打越准。判断/规律全由你（模型）做，`scripts/retro.py` 只拉终场比分与对账事实。复盘过的场次记在 `references/reviewed_matches.json`，不重复分析。

工作目录：每次新建 `runs/<日期>/`（在本 skill 目录下），所有中间文件和最终 `report.html` 放这里。命令示例里的 `$WS` 即指它。

## 依赖：web-access 技能（打开报告 + 抓数据兜底都靠它的 CDP）

本 skill 用 [web-access](https://github.com/eze-is/web-access) 的 CDP proxy 做两件事：**把报告开到用户日常的 Chrome**（第 5b 步，可截图确认），以及直连被反爬阻断时在浏览器上下文里 `fetch` 接口突破。proxy 默认在 `localhost:3456`，连不上即视为未就绪。

web-access 本身跨工具（Claude Code / Cursor / Codex 都能装），所以新用户没装时**别跳过、别降级**——先**问用户**要不要装，再给方式：
- 方式一（推荐，跨工具一键）：`npx skills add eze-is/web-access`
- 方式二（让我代装）：用户说「帮我安装这个 skill：https://github.com/eze-is/web-access」

装好后 proxy 起来，照常走 CDP。

---

## 第 R 步：赛后复盘（触发后最先做，自我进化）

出今天的买法前，先复盘历史与上一期、把经验沉淀进 `references/experience.md`，再带着经验做今天的分析。
**判断/规律/校准全由你做；`scripts/retro.py` 只算确定性事实（终场比分、各模型方向对错）。**

先定位有什么可复盘：

```bash
python scripts/retro.py locate --out "$WS/retro_locate.json"
```

输出 `historical_unreviewed`（已踢完 + 有预测 + 没复盘过的历史场）+ `own_run_to_review`（上一期我们自己的 run）。两者皆空 → 本次无可复盘，直接进第 0 步。

### Track 1 — 历史规律 backfill（子 agent 分治）

对 `historical_unreviewed`（首次可能很多场）：

- 把 match_id 分成几批，**每批派一个子 agent 并行**处理（参考 web-access 的并行分治、保主 agent 上下文）。子 agent prompt **目标导向**：
  > 用 `scripts/retro.py score --ids <这批>` 拿终场 + 各模型方向对错；再抓这批比赛的 `fan_subjective_prediction_md`（`fetch_predictions.py matches`），洞察"哪个模型 / 哪类嘉豪信号（门将评分、体能休整、盘口、边路点）与押对相关"，**只回结构化小结**（不回原文）。直连被阻断则加载 web-access skill 走 CDP。
- 你（主 agent）汇总各子 agent 小结 → **增量更新** `references/experience.md` 三小节（模型校准 / 可信信号 / 买法倾向）。
- 标记已复盘：`python scripts/retro.py mark --ids <这批全部> --synced <今天日期>`。

### Track 2 — 上一期推荐复盘（grade + 问用户 + 分析）

对 `own_run_to_review`（设其目录为 `$PREV`）：

- 拉终场对账（只复盘已结束场，未完的挂起）：
  ```bash
  python scripts/retro.py score --ids <$PREV 的 match_id,逗号分隔> --out "$PREV/retro_facts.json"
  ```
- 读 `$PREV/analysis.json`（我们上期的三档买法 + 价值/陷阱点）。
- **问用户上次买了哪个**：用 `AskUserQuestion` 列出上期三档（稳健/平衡/激进）与关键腿，让用户选实际买了哪档 / 哪些腿（含"没买 / 只看"选项）。
- 你据「我们的推荐 + 用户实际所买 + 终场」复盘：每条推荐 hit/miss、用户那注中没中、哪个模型这几场更靠谱、嘉豪正文哪类信号被验证、大方向对不对、下次怎么调整。写 `$PREV/retro.json`（schema 见 `references/playbook.md` 第七节；事实字段抄 `retro_facts.json`，判断字段你写）。
- **追加经验**：把校准 / 可信信号 / 买法倾向增量并进 `references/experience.md`，并在"复盘日志"加一行；可在 retro.json 里记 `historical_synced` = 本次 Track 1 新分析的历史场数。
- 标记：`python scripts/retro.py mark --ids <$PREV 的 match_id> --run <$PREV 日期>`。
- `$PREV/retro.json` 在第 5 步用 `--retro` 渲染进今天报告的"上期复盘回顾"模块。

复盘做完，带着 `experience.md` 进入选场。

## 第 0 步：选场（触发后先做）

抓赛程，列出"未开赛 + 有预测"的近几场，让用户勾选。

```bash
python scripts/fetch_predictions.py index --out "$WS/preds_index.json"
```

- 输出即"未开赛 + has_predict"的候选场次（已踢完的自动排除）。
- 同时抓在售列表，确认哪些"在售"（能投注）：
  ```bash
  python scripts/fetch_odds.py list --out "$WS/odds_list.json"
  ```
- 用 `AskUserQuestion`（multiSelect）列出候选场次让用户勾选，**默认全选**。每个选项信息放清楚、便于决策：
  - **label**：`队A vs 队B`（用 worldcup 侧队名）。
  - **description**：`开赛 MM-DD HH:MM · 已有 N 家预测(Claude/DeepSeek/…) · 在售/未在售`。
  - 未在售的场次要么不列、要么明确标注"未在售不可投"；只有两侧（预测+倍率）都有且在售的场次才进入后续抓取。

## 第 0b 步：选 agent（多选）

用 `AskUserQuestion`（multiSelect）列出可用 agent 让用户勾选要看谁的讨论：

> **DeepSeek**(deepseek-v4-pro)、**Claude**(claude-opus-4-6)、GPT(gpt-5.5)、Gemini(gemini-3.5-flash)、GLM(glm-5.1)、Kimi(kimi-k2.6)

- **默认预勾 Claude + DeepSeek**，但用户可只看一个、多选几个、或全看。
- 型号字符串以脚本从当场 JSON 动态读到的为准（版本会升级）。每个选项：**label** 用 `厂牌 · 型号`（如 `Claude · claude-opus-4-6`）；**description** 一句话点出该模型当前覆盖了选中的哪几场（没覆盖全部时尤其要说）。默认预勾的 Claude / DeepSeek 排在选项列表最前。
- 勾选结果决定第 3 步读谁的讨论、以及"方向一致"基于哪个集合判断。

## 第 1 步：抓数据

对勾选场次抓预测 + 全玩法倍率。

```bash
# 预测（逐 agent 的 bet + 讨论正文）
python scripts/fetch_predictions.py matches --ids <选中的 match_id,逗号分隔> --out "$WS/predictions.json"

# 全玩法实时倍率：pairs.json = [["西班牙","佛得角"], ...]（用 worldcup 侧队名）
python scripts/fetch_odds.py fetch --pairs "$WS/pairs.json" --out "$WS/odds.json"
```

若直连报错/被阻断 → 用 web-access 的 CDP proxy 在浏览器里 `fetch` 同样的接口存成本地 JSON，再用脚本的 `--raw-dir` / `--raw-list` / `--raw-detail-dir` 读入（见 data-sources.md 第五节）。**走 CDP 前先展示反爬须知**；没装 web-access 就按上文「依赖」节先问用户是否安装，或直接用 `--raw-*` 读预抓数据。

## 第 2 步：合并去水

```bash
python scripts/merge.py --predictions "$WS/predictions.json" --odds "$WS/odds.json" --out "$WS/merged.json"
```

产出每场统一对象：各玩法去水概率、比分反推 1X2、各模型"我更看好"一句话、单关标记。

## 第 3 步：读讨论、下判断（你来做）

**先读 `references/experience.md`**（复盘累积的经验）：哪个模型在哪类场更可信、嘉豪正文里重点看哪类信号、买法有哪些历史教训——作为"可能有效的提示"带进判断（样本少时弱倾斜，别盖过当场推理）。

读 `merged.json`，对**勾选的 agent**逐场读其 `discussion_md`（即 `fan_subjective_prediction_md`）：
- 抽方向、3-5 个核心论点（保留球员/区域/数据等细节）、最可能比分、模型间分歧点。
- 对照去水概率找**价值点**（讨论看好但赔率偏高）与**陷阱点**。
- 未勾选模型只用 merge 抽好的 `lean` 做脚注。

判断口径、信心星级、单关/串关可投性，全部按 `references/playbook.md`。

## 第 4 步：定三档方案 + 写 analysis.json

按 playbook 的稳健/平衡/激进规则，结合价值点和单关标记，写出 `analysis.json`
（schema 见 `references/playbook.md` 第六节，含 meta / matches / plans）。
- 稳健只取方向一致、可单关的高把握腿；有分歧/未开单关的场次该跳就跳。
- 串关每腿赔率连乘由报告脚本算，你只需列出腿。
- 不写真实金额，只给信心星级 + 仓位语言。
- **结合复盘结论**：若 `experience.md` / 本期复盘指出某模型某类判断更准、某买法倾向屡空，显式据此调整（如"因上期让球大胜全空 + DeepSeek 防反更准，本期稳健更偏 DeepSeek 的小胜/防反剧本"），并在 `analysis.json` 的 `risk_note` 里点一句让用户看到复盘是怎么影响今天的。

## 第 5 步：生成报告

```bash
python scripts/build_report.py --merged "$WS/merged.json" --analysis "$WS/analysis.json" \
  --retro "$PREV/retro.json" --out "$WS/report.html"
```

`--retro` 可选：有第 R 步产出的上期复盘就传，渲染进三档方案下方的"上期复盘回顾"模块；无则省略。

报告已内置 **Anthropic 编辑感**模板（亮：纸感米白 / 暗：对齐 claude.ai 的暖炭灰，陶土橘点缀，Fraunces 衬线标题，价值高亮克制），并支持：

- **双主题**：跟随系统、可手动切换并记忆（右上角 `🌙/☀` 按钮）。
- **顶部吸顶导航**：比赛跳转 chips + 滚动高亮当前场次。
- **渐进披露**：顶部三档方案用 **Tabs 聚焦切换**（一次看一档、选中档独占全宽面板，腿按内容自动铺多列；PDF 导出时三档自动全展开并各自标注档位）；每场只常驻"结论 + 最可能比分 + 价值点 + 重点玩法（胜平负，缺则比分）"，"全部玩法赔率"和"模型讨论对比"默认折叠，点开再看——解决信息过载。
- **模型品牌图标**：Claude/DeepSeek/Gemini/OpenAI 官方矢量 + GLM/Kimi 简标，内联 SVG、主题自适应，用在观点卡/脚注/采纳模型标签。
- **PDF 导出**：`⤓ 导出 PDF` 按钮（或 Ctrl+P）走 `window.print()`，自动展开所有折叠、隐藏导航/按钮、强制浅色、A4 分页。
- **上期复盘回顾**：三档方案下方一个可折叠模块（传了 `--retro` 才有），渲染上期对账（每场 ✓/⊘/✗）、三档命中、模型校准、本期据此调整。

> 想换风格/重做版式时，可调用 `frontend-design` skill 重新设计模板再回填到 `build_report.py`，保持 Anthropic 调性。模板（CSS/JS/品牌图标 SVG）全部内联在 `build_report.py`，产物为单文件 HTML（仅 Fraunces 字体走 Google Fonts，离线优雅降级到系统衬线）。

## 第 5b 步：用 CDP 打开报告（生成后必做）

报告生成成功后，**务必用 CDP 在浏览器里把 `report.html` 打开给用户看**，不要只丢一个路径。

**主路径：web-access 的 CDP Proxy**（最稳——直连用户日常 Chrome，一条 curl 即开）：

- 确认 Proxy 就绪：`localhost:3456` 连得上即可（不确定就跑 web-access 的 `scripts/check-deps.mjs`，已在跑则秒过）。**没装 web-access？别跳过**——按上文「依赖」节先问用户是否安装（`npx skills add eze-is/web-access` 或让你代装），装好再继续。
- 新开后台标签页打开报告的本地文件 URL（Windows 用正斜杠）：
  ```bash
  curl -s "http://localhost:3456/new?url=file:///C:/Users/.../runs/<日期>/report.html"
  ```
- 可顺手截图确认渲染正常：`curl -s "http://localhost:3456/screenshot?target=<上一步返回的 targetId>&file=<临时目录>/r.png"`。

**备选**：当前环境恰好装了 chrome-devtools MCP 时，也可用它（`mcp__chrome-devtools__new_page`；未加载先用 `ToolSearch` 查 `chrome-devtools`）打开同一个 file URL。

打开后在聊天里仍然把 `report.html` 的路径给用户（方便他自己再开 / 导出 PDF）。

## 第 6 步：聊天摘要

在聊天里给一段精炼版：每场一句结论 + 三档方案（关键腿 + 合计赔率）+ 一句"理性投注"。别把报告全文复述一遍，点到为止、引导用户去看报告。

---

## 边界

- 只覆盖"未开赛 + 有预测 + 在售"的场次；已封盘/未开售如实告知。
- 某玩法未开售（字段缺失）= 跳过，不脑补倍率。
- 胜平负常常未开放单关（强弱悬殊场尤甚），这类只能进串关——别推成单关。
- 复盘：首次运行做大批量历史 backfill（子 agent 分治）；没有上一期 / 上期未踢完 → Track 2 跳过、报告无复盘模块。复盘过的场次（`reviewed_matches.json` 记录）不重复分析。
- **不构成投注建议**；理性娱乐、量力而行。
