---
name: worldcup-bet-advisor
description: 世界杯竞彩"嘉豪预测汇总"。把多个 AI 模型（Claude、DeepSeek、GPT、Gemini、GLM、Kimi 等"嘉豪世界杯预测"）对每场的实际下注、最可能比分、以及"嘉豪先疯一句"原文，连同当天全玩法（胜平负/让球/比分/总进球/半全场）的实时倍率与去水概率，原样汇总成一份 Anthropic 风格的单文件 HTML 报告——只做呈现，不含本站的分析、判断或买法推荐。当用户想看"今天/这几场世界杯各模型怎么预测""嘉豪世界杯预测""各模型下注一览""各模型猜的比分""市场怎么看这场""倍率/去水概率""世界杯竞彩"，或想要一份汇总各模型预测+实时赔率的报告时，**务必触发本 skill**——即使用户只说"看看今天世界杯各模型怎么说""帮我汇总下这几场"也应触发，不要自己凭空猜结果。但若用户只是查赛程/开赛时间、问已结束比赛的比分或战报、了解某支球队/球员资讯、看积分榜等与"模型预测/倍率汇总"无关的世界杯话题，则不属于本 skill，按普通查询处理即可。
allowed-tools: Bash, Read, Write, Edit, Skill, Agent, AskUserQuestion, ToolSearch, mcp__chrome-devtools__new_page, mcp__chrome-devtools__navigate_page, mcp__chrome-devtools__list_pages
---

# 嘉豪世界杯预测汇总（多模型下注 × 猜测比分 × 实时倍率）

把"最近几场世界杯各模型怎么预测"这种口语需求，变成一份**汇总报告**：各模型在嘉豪平台的实际下注、各模型的猜测比分、每场的"嘉豪先疯一句"原文，叠加当天全玩法实时倍率与市场去水概率。**只做汇总呈现，不做任何分析、推导或买法推荐。**

## 心法

- **汇总，不是推导**：本 skill 的产物是"对嘉豪预测网站 + 实时赔率的一份整洁汇总"。不写门面定调、不给稳健/平衡/激进三档、不点博冷/防平、不做价值/陷阱判断。用户要的是看清各模型怎么说、市场怎么看，自己拿主意。
- **原文照搬**：每场的"嘉豪先疯一句"（我更看好 / 常规时间方向 / 最可能比分 / 我敢押的一个具体画面）一字不改地呈现，别替模型总结、别提炼论点。
- **比分要归一、只这一处要判断**：报告里"各模型猜测比分一览"显示的是把各模型『最可能比分』**归一到「主队-客队」朝向**后的纯比分（如瑞士 vs 加拿大 → `2-1`）。模型报比分的朝向千奇百怪（带队名/不带队名/赢家在前/给多个），这步靠你读懂上下文判读——这是全流程**唯一**需要你下判断的地方，且只判"比分朝向"，不判"该买谁"。详见第 3 步。
- **市场视角来自去水赔率**：每场的"市场怎么看"全部由 `merge.py` 已算好的去水概率（胜平负）+ 比分榜 top 渲染，是赔率事实，不是本站观点。
- **脚本管确定性、你只判比分朝向**：抓取/解析倍率/去水/比分榜交给脚本；你的活只剩"把各模型最可能比分归一到主客朝向"。可复现、省 token。
- **自更新优先**：每次触发先查 GitHub 有无新版本（第 -1 步，`scripts/self_update.py`），有新版先更新再干活，本机数据（`runs/`）保留；连不上就跳过（fail-open）。
- **直连优先、CDP 兜底**：接口默认直接拉（urllib）；只有被反爬阻断才走 web-access 的 CDP，且先向用户展示反爬须知。
- **开工前读 `references/data-sources.md`**：两站接口、字段字典（sw/sd/sl 比分、t 总进球、ht 半全场、single* 单关标记）、跨站队名匹配都在里面。
- **收益仪表盘靠手动登记**：公网站点保留"我买的票 + 每日盈亏"仪表盘，但它追踪的是**你自己的下注**（本 skill 不再推荐买法）。出报告时若你上一期自己买过，用第 6 步的极简结算把那几注登记进去，用终场比分判中——不做任何模型校准/对账分析。

工作目录：每次新建 `runs/<日期>/`（在本 skill 目录下），所有中间文件和最终 `report.html` 放这里。命令示例里的 `$WS` 即指它。

## 依赖：web-access 技能（打开报告 + 抓数据兜底都靠它的 CDP）

本 skill 用 [web-access](https://github.com/eze-is/web-access) 的 CDP proxy 做两件事：**把报告开到用户日常的 Chrome**（第 4b 步，可截图确认），以及直连被反爬阻断时在浏览器上下文里 `fetch` 接口突破。proxy 默认在 `localhost:3456`，连不上即视为未就绪。

web-access 跨工具（Claude Code / Cursor / Codex 都能装）。新用户没装时别默默跳过或降级——先问用户要不要装，再给方式：
- 方式一（推荐，跨工具一键）：`npx skills add eze-is/web-access`
- 方式二（让我代装）：用户说「帮我安装这个 skill：https://github.com/eze-is/web-access」

装好后 proxy 起来，照常走 CDP。

---

## 第 -1 步：自更新检查（触发后最先做）

技能自带 `scripts/self_update.py`，每次触发先轻量检查 GitHub 有没有新版本——这样无论怎么装（`npx skills` / `cp` 拷贝、或 `git clone`）都能自动跟上作者更新、不必重装。它自动分两种情形（你不用判断）：

- **在 git 工作区**（作者机 junction / clone 用户）：跑 `git pull --ff-only`；工作区有未提交改动就只提示、不强拉。
- **纯拷贝**（第三方）：比对本技能目录的最新提交，有新版就从 GitHub 下载覆盖自己，**保留本机数据**（`runs/`）；每天最多查一次。

fail-open：连不上 GitHub / 出任何错都静默用当前版、绝不阻塞正事。在本 skill 目录跑：

```bash
python scripts/self_update.py
```

按输出行首标记处理：
- `= up-to-date` / `~ skipped` → 静默继续，进第 0 步。
- `✓ updated …` → 告诉用户已从 GitHub 更新，并**重新读取本 SKILL.md 与 `scripts/`**（逻辑可能已变）后再继续。
- `⚠ dirty …`（仅作者机）→ 本地有未提交改动挡住了更新。提示用户先 `git add -A && git commit && git push`，或这次跳过、用本地版。

## 第 0 步：选场（触发后先做）

抓赛程，列出"未开赛 + 有预测"的近几场，让用户勾选。

```bash
python scripts/fetch_predictions.py index --out "$WS/preds_index.json"
# 同时抓在售列表，确认哪些"在售"（能投注、有倍率）
python scripts/fetch_odds.py list --out "$WS/odds_list.json"
```

- `preds_index.json` 即"未开赛 + has_predict"的候选场次（已踢完的自动排除）。
- 用 `AskUserQuestion`（multiSelect）列出候选场次让用户勾选，**默认全选**。每个选项：
  - **label**：`队A vs 队B`（用 worldcup 侧队名）。
  - **description**：`开赛 MM-DD HH:MM · 已有 N 家预测(Claude/DeepSeek/…) · 在售/未在售`。
  - 未在售的场次明确标注；倍率缺失也能出"只有模型预测、无市场视角"的汇总，但要如实告知。

## 第 0b 步：选模型（多选，默认全选）

本 skill 是"各模型汇总"，**默认勾选全部可用模型**，让用户取消不关心的即可：

> **DeepSeek**、**Claude**、**GPT**、**Gemini**、**GLM**、**Kimi**（型号字符串以脚本从当场 JSON 动态读到的为准）

用 `AskUserQuestion`（multiSelect）列出，每个选项 **label** 用 `厂牌 · 型号`，**description** 一句话点出该模型覆盖了选中的哪几场。勾选结果决定报告里"各模型下注/比分一览"和"嘉豪先疯一句"展示谁。

## 第 1 步：抓数据

对勾选场次抓预测 + 全玩法倍率。

```bash
# 预测（逐模型的 bet + 嘉豪正文 discussion_md）
python scripts/fetch_predictions.py matches --ids <选中的 match_id,逗号分隔> --out "$WS/predictions.json"

# 全玩法实时倍率：pairs.json = [["瑞士","加拿大"], ...]（用 worldcup 侧队名）
python scripts/fetch_odds.py fetch --pairs "$WS/pairs.json" --out "$WS/odds.json"
```

若直连报错/被阻断 → 用 web-access 的 CDP proxy 在浏览器里 `fetch` 同样的接口存成本地 JSON，再用脚本的 `--raw-dir` / `--raw-list` / `--raw-detail-dir` 读入（见 data-sources.md 第五节）。**走 CDP 前先展示反爬须知**；没装 web-access 就按上文「依赖」节先问用户是否安装。

## 第 2 步：合并去水

```bash
python scripts/merge.py --predictions "$WS/predictions.json" --odds "$WS/odds.json" --out "$WS/merged.json"
```

产出每场统一对象：各玩法去水概率、比分榜 top、各模型 bet（落到胜平负/让球盘哪一格）、各模型 discussion_md（嘉豪正文）、单关标记。报告的"各模型下注一览"和"市场怎么看"全部由它直接渲染，无需你加工。

## 第 3 步：比分归一（全流程唯一要你判断的一步）

把各模型『最可能比分』原话，归一成「主队-客队」朝向的纯比分，写回 merged.json 供报告的"各模型猜测比分一览"渲染。脚本管两头 IO，朝向判读你来做：

```bash
# 抽出每场 team_a/team_b + 各模型 favor/direction/score_line（不带冗长正文，省 token）
python scripts/normalize_scores.py extract --merged "$WS/merged.json" --out "$WS/norm_in.json"
```

读 `norm_in.json`，对每条把比分归一成 `"主队进球-客队进球"`，结果写成 `{match_id: {brand: "2-1"}}` 存到 `$WS/norm_out.json`，再回写：

```bash
python scripts/normalize_scores.py apply --merged "$WS/merged.json" --norm "$WS/norm_out.json"
```

**归一规则（务必结合 favor + direction + score_line 整体读，别机械套）：**
- **写了队名**（"阿尔及利亚 2-1 约旦"）→ 按队名对应进球数，再映射回 team_a(主)-team_b(客) 顺序。例：约旦(主) vs 阿尔及利亚(客)、原话"阿尔及利亚 2-1 约旦" → `1-2`。
- **没写队名只有数字**（"2-1"）→ 用 favor/direction 判断模型认为**谁赢/谁不败/还是平局**，把大比分给它看好赢的那队；据此定朝向。别机械"首位数字归看好的队"——若看好的队写在小比分那侧会判反（如"看好科特迪瓦不败 + 1-2"指的是德国输或平，不是德国 2-1）。
- **平局比分**（1-1、2-2）→ 无朝向问题，直接照写。
- **给了多个比分**（"2-1 或 2-0"、"次选 2-1"、"1-0，3-1"）→ 每个都归一，用 ` / ` 连成一格（如 `2-1 / 2-0`）。
- **朝向必须与该模型自己的 favor/direction 自洽**：不许把本意"对方赢"的比分掰成"我看好的队赢"来凑。
- **没有最可能比分**（某模型没给）→ 该模型不写 `pred_score_norm`，一览里自动略过它。

**场次多就分治**：选中场 × 模型数较多（如 ≥ 五六场）时，把 `norm_in.json` 按场分几批，每批派一个子 agent 并行判读、各回一段 `{match_id:{brand:norm}}`，主 agent 合并后一次 `apply`（参考 web-access 的并行分治）。平时两三场主 agent 直接做，别为分治而分治。

> 注意：这步只影响"各模型猜测比分一览"那个汇总表。每场正文里"嘉豪先疯一句"的最可能比分仍是**原话照搬**（带不带队名都不动），两者分工不冲突。

## 第 4 步：生成报告

```bash
python scripts/build_report.py --merged "$WS/merged.json" --date <YYYY-MM-DD> --out "$WS/report.html"
```

`--date` 传当天日期（报告标题与站点文件名用它；不传则从最早开赛时间推北京日期，遇到深夜场会偏到次日，所以推荐传）。报告纯由 `merged.json` 渲染，**不再需要 analysis.json**。

报告内置 **Anthropic 编辑感**模板，版块顺序固定为：

1. **今日赛程**：圆形队徽 + 队名 + 阶段 + 北京时间 + FIFA 排名的卡片栅格，点任意比赛跳到下方对应场次。
2. **各模型下注一览**（tab 切换比赛）：把各模型在嘉豪平台的实际下注落到它在该场胜平负/让球盘押的那一格，高亮"最多模型押的方向"，标 `N/总数` 和赔率。
3. **各模型猜测比分一览**（tab 切换比赛）：各模型『最可能比分』归一后的纯比分（主队-客队）并排，末行附市场比分榜 top。
4. **每场**：①"市场怎么看"——胜平负去水概率条 + 市场最看好谁 + 比分榜 top；②"嘉豪先疯一句 · 各模型原话"——各模型四行原文照搬；③折叠的"全部玩法赔率"（胜平负/比分/让球/总进球/半全场）。

还支持：双主题（跟随系统 + 手动切换记忆）、左侧目录栏（大块 + 逐场跳转、滚动高亮、可收起、窄屏抽屉）、模型品牌图标、PDF 导出（`⤓ 导出 PDF` 或 Ctrl+P，自动展开折叠 + 强制浅色 + A4 分页）。

> 想换风格/重做版式时，可调用 `frontend-design` skill 重新设计模板再回填到 `build_report.py`，保持 Anthropic 调性。模板（CSS/JS/品牌图标 SVG）全部内联在 `build_report.py`，产物为单文件 HTML。

## 第 4b 步：用 CDP 打开报告（生成后必做）

报告生成后，用 CDP 在浏览器里把 `report.html` 打开给用户看，别只丢一个路径。

**主路径：web-access 的 CDP Proxy**：

- 确认 Proxy 就绪：`localhost:3456` 连得上即可（不确定就跑 web-access 的 `scripts/check-deps.mjs`）。没装 web-access 就按「依赖」节先问用户是否安装。
- 新开后台标签页打开报告（先 `/new` 拿 targetId，再 `/navigate` 到本地文件 URL；Windows 用正斜杠）：
  ```bash
  TID=$(curl -s -X POST --data-raw "about:blank" http://localhost:3456/new | python -c "import sys,json;print(json.load(sys.stdin)['targetId'])")
  curl -s "http://localhost:3456/navigate?target=$TID&url=file:///C:/.../runs/<日期>/report.html"
  ```
- 可顺手截图确认：`curl -s "http://localhost:3456/screenshot?target=$TID&file=<临时目录>/r.png"`。

**备选**：当前环境装了 chrome-devtools MCP 时，也可用它（`mcp__chrome-devtools__new_page` → `navigate_page`）打开同一个 file URL。

打开后在聊天里仍把 `report.html` 的路径给用户（方便他自己再开 / 导出 PDF）。

## 第 5 步：聊天摘要

在聊天里给一段精炼版：一句话说清"今天 N 场、覆盖哪几个模型"，再点几句最直观的汇总（如"瑞士vs加拿大六家全押瑞士胜、比分多在 2-1""市场最看好谁"）。别复述报告全文，引导用户去看报告（本地 `report.html` 或公网站点链接）。**不给买法建议**——这是汇总不是投顾。

## 第 6 步：发布到每日站点 + 结算我买的票（Vercel）

把第 4 步的 `report.html` **原样**搬上公网站点（`web/` 的 Next.js 应用 iframe 嵌入，一字不改），外面只多两样：**日期切换**看往期、**收益仪表盘**看"我买的票 + 每日盈亏"。机制、隐私边界、一次性设置见 `references/site-deploy.md`。

发布（公开模式：报告/数据入库，靠 `git push` 触发 Vercel 部署）：

```bash
bash scripts/publish_site.sh --report "$WS/report.html" --date <YYYY-MM-DD>
git add worldcup-bet-advisor/web/data worldcup-bet-advisor/web/public/reports && \
  git commit -m "report: <日期>" && git push   # Vercel 自动上线
```

**结算上一期"我买的票"（仅当你自己买过、想记进仪表盘）**：本 skill 不再推荐买法，但你可能自己下了注。要让仪表盘显示，做一条极简结算：

1. 用 `AskUserQuestion` 问用户上一期（`runs/<上一期>/`）买了哪些注、每注本金（¥）和各腿赔率。"只看没买"就跳过本步。
2. 判每腿中没中：胜平负/让球/比分/总进球这类只依赖终场比分的，自己抓终场比分判（终场可从 `fetch_predictions.py index` 的已结束场或直接读 worldcup 的 `data/index.json` 的 `score_full` 拿）；半全场/半场比分这类问用户最快（`AskUserQuestion`：中了/没中/还没结算）。
3. 写一个最小结算文件 `$PREV/settle.json`：
   ```json
   { "reviewed_run": "<上一期日期 YYYY-MM-DD>",
     "user_bought": { "tickets": [
       { "tier": "自选", "type": "比分单关", "stake": 50,
         "legs": [ { "text": "瑞士 2-1 加拿大", "odds": 8.5, "hit": true } ] }
     ] } }
   ```
   多注独立票（一张票押多场各自单关）加 `"mode": "independent"`，每腿可带 `stake`。
4. 回填进仪表盘：
   ```bash
   python scripts/export_site_data.py settle --retro "$PREV/settle.json" --site-data worldcup-bet-advisor/web/data
   ```
   它按"本金 × 命中腿赔率连乘"算真实盈亏，渲染成"我买的票"没中卡片 + 每日收益柱状图。**只算盈亏、不做任何模型校准或买法复盘。**

- **首次/未设置站点**：先读 `references/site-deploy.md` 走一次性设置，或用官方 `deploy-to-vercel` 技能部署。别默默跳过——告诉用户站点没建、问要不要现在建。
- **fail-soft**：没装/没登录 Vercel 时，数据仍备在本地，本地 `report.html` 始终在，不阻塞正事。

---

## 边界

- 只覆盖"未开赛 + 有预测"的场次；倍率缺失时出"只有模型预测、无市场视角"的汇总并如实告知。
- 某玩法未开售（字段缺失）= 跳过，不脑补倍率。
- 比分归一只判"主客朝向"，不替用户解读"该买谁"；模型没给比分就略过该模型。
- **本 skill 只做汇总呈现，不构成投注建议**；理性娱乐、量力而行，未满法定年龄者请勿参与。
