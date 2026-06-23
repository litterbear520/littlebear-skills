---
name: worldcup-bet-advisor
description: 世界杯竞彩"玩法建议"分析。综合多个 AI agent（Claude、DeepSeek 等"嘉豪世界杯预测"模型）对比赛的预测比分与讨论，叠加当天全部玩法（胜平负/让球/比分/总进球/半全场）的实时倍率，去水校验找价值，最终给出稳健/平衡/激进三档玩法方案（单关、串关、比分等），并产出一份 Anthropic 风格的单文件 HTML 报告。当用户想预测最近几场世界杯比赛结果、问"今天/这几场买哪个""怎么串""单关还是串关""比分推荐""玩法建议""倍率""嘉豪世界杯预测""世界杯竞彩"，或想让你综合 agent 预测+实时倍率给投注思路时，**务必触发本 skill**——即使用户只说"看看今天世界杯怎么玩""帮我分析下这几场"也应触发，不要自己凭空猜结果。但若用户只是查赛程/开赛时间、问已结束比赛的比分或战报、了解某支球队/球员资讯、看积分榜等与"玩法/投注"无关的世界杯话题，则不属于本 skill，按普通查询处理即可。
allowed-tools: Bash, Read, Write, Edit, Skill, AskUserQuestion, ToolSearch, mcp__chrome-devtools__new_page, mcp__chrome-devtools__navigate_page, mcp__chrome-devtools__list_pages
---

# 世界杯玩法建议（多 agent 预测 × 实时倍率）

把"最近几场世界杯怎么买"这种口语需求，变成一份**三档玩法方案**（稳健单关 / 平衡单关+小串 / 激进串关博高赔）+ 一份 Anthropic 风格的单文件 HTML 报告。

## 心法

- **自更新优先**：每次触发先查 GitHub 有无新版本（第 -1 步，`scripts/self_update.py`），有新版就先更新再干活，本机经验/复盘数据始终保留；连不上就跳过（fail-open）。
- **讨论为主、倍率校验**：先看勾选 agent（默认 Claude+DeepSeek）的讨论方向，再用实时倍率的去水概率找价值点。决策口径全在 `references/playbook.md`。
- **比分≠表现**：本届已出场的队，赛前联网搜上一场真实战况（谁压谁、xG、丢球方式、红牌伤停），别只看比分。详见第 1b 步。
- **防平是守、博冷是攻**：防平诊断提醒"别买热门赢"，博冷雷达再主动给一注"最可能的爆冷"（本届热门翻车约 40%、多为冷平）。详见第 3 步 + playbook"二·补"。
- **脚本管确定性、模型管判断**：抓取/解析倍率/去水/串关连乘交给脚本，读讨论、下结论、定三档方案是你的活——这样可复现、省 token。
- **直连优先、CDP 兜底**：接口默认直接拉（urllib）；只有被反爬阻断才走 web-access 的 CDP，且先向用户展示反爬须知。
- **开工前读 `references/data-sources.md`**：两站接口、字段字典（sw/sd/sl 比分、t 总进球、ht 半全场、single* 单关标记）、跨站队名匹配都在里面。
- **复盘驱动进化**：每次触发先做赛后复盘（第 R 步），两条线增量沉淀进 `references/experience.local.md`——Track 1 把"嘉豪预测 vs 真实比分"提炼成判断力，Track 2 对账上期买法。脚本只拉事实，判断由你做。
- **本地报告 + 公网站点**：第 5 步的 `report.html` 既本地打开，也被第 7 步的 Next.js 站点（`web/`）**原样 iframe 嵌入**发布到公网——报告版式一字不改，只多了日期切换（看往期）和收益仪表盘（「我买的票」中没中 + 每日收益）。默认私有模式：报告/本金/收益不进公开仓库，`npx vercel --prod` 直推上线。详见 `references/site-deploy.md`。

工作目录：每次新建 `runs/<日期>/`（在本 skill 目录下），所有中间文件和最终 `report.html` 放这里。命令示例里的 `$WS` 即指它。

## 依赖：web-access 技能（打开报告 + 抓数据兜底都靠它的 CDP）

本 skill 用 [web-access](https://github.com/eze-is/web-access) 的 CDP proxy 做两件事：**把报告开到用户日常的 Chrome**（第 5b 步，可截图确认），以及直连被反爬阻断时在浏览器上下文里 `fetch` 接口突破。proxy 默认在 `localhost:3456`，连不上即视为未就绪。

web-access 跨工具（Claude Code / Cursor / Codex 都能装）。新用户没装时别默默跳过或降级——先问用户要不要装，再给方式：
- 方式一（推荐，跨工具一键）：`npx skills add eze-is/web-access`
- 方式二（让我代装）：用户说「帮我安装这个 skill：https://github.com/eze-is/web-access」

装好后 proxy 起来，照常走 CDP。

---

## 第 -1 步：自更新检查（触发后最先做，先于复盘）

技能自带 `scripts/self_update.py`，每次触发先轻量检查 GitHub 有没有新版本——这样无论怎么装（`npx skills` / `cp` 拷贝、或 `git clone`）都能自动跟上作者更新、不必重装。它自动分两种情形（你不用判断）：

- **在 git 工作区**（作者机 junction / clone 用户）：跑 `git pull --ff-only`；工作区有未提交改动就只提示、不强拉。
- **纯拷贝**（第三方）：比对本技能目录的最新提交，有新版就从 GitHub 下载覆盖自己，**保留本机数据**（`runs/`、`experience.local.md`、`reviewed_matches.json`）；每天最多查一次。

fail-open：连不上 GitHub / 出任何错都静默用当前版、绝不阻塞正事。

在本 skill 目录跑：

```bash
python scripts/self_update.py
```

按输出行首标记处理：
- `= up-to-date` / `~ skipped`（今日已查 / 连不上 / 用本地版） → 静默继续，进第 R 步。
- `✓ updated …` → 告诉用户已从 GitHub 更新，并**重新读取本 SKILL.md 与 `scripts/`**（逻辑可能已变）后再继续。
- `⚠ dirty …`（仅作者机）→ 本地有未提交改动挡住了更新（多半是累计经验）。提示用户：先 `git add -A && git commit && git push` 回传，再重跑本检查；或这次跳过、用本地版。

---

## 第 R 步：赛后复盘（自更新后、出买法前先做，自我进化）

复盘是本 skill 的自我进化引擎——每次触发都先做，带着经验出今天的买法。两条线各自跨期累计、别混写（判断/规律由你做，`scripts/retro.py` 只算确定性事实：终场比分、各模型方向对错）：

| | **Track 1 · 建库**（→ 判断力：信谁） | **Track 2 · 对账**（→ 买法力：怎么买） |
|---|---|---|
| 问什么 | 各模型嘉豪预测 vs 真实比分，哪个模型/哪类信号更准（**可泛化**） | 我们上期三档、用户那一注赢没赢（**这一单**） |
| 范围 | **所有**未复盘的已踢完场（含下注过的、首次积压的） | **每个**未复盘的自有 run（不只最近一个） |
| 产物 | 增量写 `experience.local.md`【模型校准】+【可信信号】+ 样本数 + 日志 | `retro.json`（渲染进今天报告）+ 回灌【买法倾向】 |
| 改进 | 第 3 步读讨论**信谁** | 第 4 步定三档**怎么买** |

**重合是常态**：昨天下注、今天踢完的场，同时进 Track 1（历史场）和 Track 2（上期 run）——一次遍历同产两者（嘉豪正文只读一遍），但两层经验都要落，别把建库省成只做对账。

**顺序**：先把 Track 1 建库、写进 local、`mark` 掉，再做 Track 2 问用户"上期买了哪档"——开场先建库，别用买法问题开场。

**经验库 = 种子 + 本地两份**（隐私/可发布的分界）：
- `references/experience.seed.md`（版本化、共享基线，作者 curated 的通用规律）+ `references/experience.local.md`（gitignore、本机累计，含你的下注流水）。
- 读：两份都读，冲突时本地优先。写：自动复盘只写 local、不写 seed（seed 由作者从 local 里手动提炼可靠规律后再 push）。
- `reviewed_matches.json`（进度账本）同为 gitignore，不跨用户共享。
- 首次运行若 `experience.local.md` 不存在：先建一份（含【模型校准 / 可信信号 / 买法倾向】三个空节 + 空"复盘日志" + "累计样本 0 场"）再建库。

先定位有什么可复盘：

```bash
python scripts/retro.py locate --out "$WS/retro_locate.json"
```

输出：
- `historical_unreviewed`：已踢完 + 有预测 + 没复盘过的历史场；每条带 `in_own_run`（true = 这场也在我们上一期 run 里＝重合场）。
- `own_runs_to_review`：**所有**未复盘的自有 run 列表（旧→新，各含 `finished_ids` / `pending_ids`）；`own_run_to_review` = 其中最近一个，供报告 `--retro` 渲染。
- `reviewed_count`：manifest 里已复盘的场数。
- 有重合（`in_own_run`）时脚本打印一行 `⚠`：这些场两条线都要做。

触发逻辑：
- `historical_unreviewed` 非空 → 做 **Track 1**（不管它是否也在上期 run 里；首次运行 `reviewed_count`=0 时这里可能很多场，要全部建库）。
- `own_runs_to_review` 非空 → 对其中**每个** run **额外**做 **Track 2**（已复盘的 run 不在列表里、不重复）。
- 两者都空 → 真没东西可复盘，直接进第 0 步。

### Track 1 — 建库复盘（对所有未复盘已踢完场）

对 `historical_unreviewed` 每一场，回答"各模型嘉豪预测 vs 终场，谁对谁错、为什么、能泛化出什么经验"：

- 拿确定性事实：`python scripts/retro.py score --ids <这批> --out "$WS/track1_facts.json"`（终场比分 + 各模型 bet 方向对错）。
- 读这些场的嘉豪正文 `fan_subjective_prediction_md`（`fetch_predictions.py matches`），逐场洞察：哪个模型、哪类嘉豪信号（门将评分、体能休整、盘口、边路点、真碾压三件套…）与押对/押错相关。
- 判模型别只看"比分中没中"，要联网看真实过程：搜该场真实战况（谁压着打、xG、丢球方式、红牌），对照模型赛前剧本——模型可能比分猜错但逻辑对（被运气/定位球坑、剧本其实应验），也可能比分蒙对但过程相反。看了真实过程，模型校准才不会被一场运气误导。方法见 playbook"一·补"。
- 按量决定要不要分治：场次多（首次积压、或一次 ≥6 场）→ 把 match_id 分几批、每批派一个子 agent 并行（参考 web-access 的并行分治、保主 agent 上下文），子 agent 只回结构化小结、不回原文；平时只有 2-4 场，主 agent 直接做，别为分治而分治。
- 汇总 → 增量更新 `references/experience.local.md` 的【模型校准】+【可信信号】+ 顶部"累计样本 N 场" + "复盘日志"加一行（日期 · 这批场次 · 学到什么）。只写 local、不写 seed；买法层面的教训留给 Track 2 写【买法倾向】。
- 标记：`python scripts/retro.py mark --ids <这批全部> --synced <今天日期>`，先 mark 再往下，保证不重复分析。

### Track 2 — 自有 run 买法复盘（对每个未复盘的 run；grade + 问用户 + 分析）

遍历 `own_runs_to_review` 每个 run（积压多期则旧→新逐个补，已复盘的不在列表里）。设当前 run 目录为 `$PREV`，其 `finished_ids` 多半在 Track 1 已读过正文，这里复用事实、只补"我们买法对没对"这一层：

- 拉终场对账：`python scripts/retro.py score --ids <$PREV finished_ids,逗号分隔> --out "$PREV/retro_facts.json"`。
- 读 `$PREV/analysis.json`（上期三档买法 + 价值/陷阱点）。
- 问用户这期买了哪个（含自选腿）：用 `AskUserQuestion` 列出该期三档与关键腿，让用户选实际买了哪档/哪些腿（含"没买/只看"）。用户常超出我们三档自己组合（自选比分串、对冲腿、半全场串等），让他一并补上。积压的旧 run 用户可能记不清，允许选"记不清"——那条 run 仍要 grade 我们的推荐、写买法经验、mark，只是缺"用户实际所买"这一维。
- **记每注本金 + 赔率（公网站点收益的唯一数据源）**：拿到用户实际所买后，顺带问每注下了多少钱（¥）、各腿赔率。这两个数让站点能用"本金 × 连乘赔率"算出**真实盈亏**（命中由本就要做的 grade 得出，你只多收集"本金 + 赔率"）。把每注写进 `retro.json` 的 `user_bought.tickets[]`（`tier`/`type`/`stake`/`legs[{text,odds,hit}]`，schema 见 playbook 第七节）——第 7 步发布时 `export_site_data.py settle` 据此渲染「我买的票」中没中卡片与每日收益柱状图。用户"只看没买"则 `tickets` 留空（站点显示当日 0 收益）。本金只进私有站点仓库，不进公开 skill 仓库。
- 判定分两层：
  - 脚本可判（胜平负/让球/比分/总进球，只依赖终场比分）→ 用 `retro_facts.json` 自动判 hit/miss。
  - 脚本判不了（半全场 htft、半场比分、任何依赖"半场/过程"的玩法；或某场终场暂时拉不到）→ 两接口都只给全场比分。这类腿问用户最快也最权威：把它们用 `AskUserQuestion`（multiSelect）列出问"中没中"（`中了`/`没中`/`还没结算`），拿回答写进 `hit`——别自己猜，也别含糊标 null 或"存疑"。我们三档里的此类腿（如"阿根廷 半全场主/主"）同样问、同样别猜。（模型校准要看真实过程，那是 Track 1 的事。）
  - 实操：先问"买了哪档/哪些腿"，拿到用户实际所买后，把其中判不了的腿汇总成一条 `AskUserQuestion` 追问——通常一轮搞定。
- 据「我们的推荐 + 用户实际所买(含自选) + 终场 + 用户对判不了腿的确认」复盘：每条推荐 hit/miss、用户那注得失、哪个模型这几场更靠谱、大方向对不对、下次怎么调。写 `$PREV/retro.json`（schema 见 `references/playbook.md` 第七节；事实抄 `retro_facts.json`，判断你写；可记 `historical_synced` = 本次 Track 1 新建库场数）。
- 买法教训回灌：把"我们哪类推荐屡空、用户那注得失"并进 `experience.local.md` 的【买法倾向】+ 复盘日志（与 Track 1 的更新合并写，仍只写 local）。
- 标记：仅当该 run 的 `pending_ids` 为空（全部踢完）才 `python scripts/retro.py mark --run <$PREV 日期>`；还有 pending 场就先别标 run，留到它们也踢完再标（场次 id 已在 Track 1 mark 过）。
- 多期时只渲染最近一个：今天报告的 `--retro` 用最近那个 run 的 `retro.json`（locate 已单独放在 `own_run_to_review` 字段）；更早补的旧 run 只更新买法经验 + mark，不进今天报告。

复盘做完（所有未复盘 run 都补完），带着经验库（`experience.seed.md` + `experience.local.md`）进入选场。

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

## 第 1b 步：查本届实际表现（赛前真实战况）

比分只是结果，表现才是趋势。今天要分析的队，凡本届已出场过的，都把它上一场（们）的**真实战况**联网搜出来（不只比分），综合成"这支队最近怎么踢"，喂给第 3 步判断和防平诊断。完整方法（搜什么、怎么用、样本怎么权衡）见 `references/playbook.md` "一·补"。

> **为什么 form 默认要联网搜**：这是真实进行中的 2026 世界杯——结果、战报、xG、伤停在 ESPN/Yahoo/FIFA/Sports Mole 都查得到（已反复核对一致：USA 4:1 巴拉圭、澳 2:0 土、德 7:1 库拉索）。早期误把它当"AI 模拟/虚构、搜不到"而跳过，form 全靠站点比分脑补，防平因此屡屡踩雷。所以 form 走真实搜索、别凭嘉豪正文或比分推测；只有真试过 `WebSearch`/`WebFetch`、确认环境无联网，才按第 4 条 fail-open 跳过。

1. 先列出该搜哪几场（脚本从赛程里取选中场两队的本届已踢场次）：
   ```bash
   python scripts/fetch_predictions.py history --ids <第0步选中的 match_id,逗号分隔> --out "$WS/history.json"
   ```
   输出每队此前的对手 / 比分 / 当时各模型一句话；某队若"本届首秀"则为空、跳过。
2. 对每场联网搜真实战况——任一可用联网工具都行：优先 `WebSearch`/`WebFetch`（最直接、不依赖代理），其次 web-access 的 CDP（没装见上文「依赖」节）。CDP proxy 没起 ≠ 不能联网。关键词如 `<队> vs <对手> World Cup 2026 preview team news lineup`、`<队> <对手> World Cup 2026 match report xG`。重点抽：谁压着谁打 / xG / 中楣、丢球方式（定位球·反击·失误）、**红黄牌停赛与伤停**（今天谁能上、谁缺阵，最影响盘口）、关键球员与替补状态。顺手搜今天这场的赛前预览（伤停、预计首发、博彩市场实际赔率），与站点赔率交叉校验。
3. 归成每队一两句**画像**（"压着打但低效"／"被压制靠运气"／"真 carry 碾压"），第 4 步写进各场 `analysis.json` 的 `form`，报告显示"本届走势 · 真实战况"块。真实表现 > 比分、也常 > 模型旧讨论：讨论可能没覆盖最新一场，用真实战况校准方向与比分；"该队本届已被逼平/被偷平"是 `draw_guard` 的硬先例信号。
4. **fail-open**：仅当真试过联网、确认环境不可用，才跳过本步、用现有讨论推进（`form` 留空或标"未联网核实"）。范围只搜选中场两队的本届此前场次（通常每队 1–2 场）+ 今天这场预览；战报当"一个信号"、不当真理，并在 `form[].src` 标注来源（ESPN/Yahoo/Sports Mole 等）。

顺手再取**本届爆冷基准率**（不依赖联网、扫赛程即可，喂第 3 步"博冷雷达"）：
```bash
python scripts/fetch_predictions.py upsets --out "$WS/upsets.json"
```
输出本届"有明显共识热门"的场里几场翻车（冷平/弱队胜清单 + 翻车率 + 当时各模型一句话）。用法见 playbook"二·补2"。

## 第 2 步：合并去水

```bash
python scripts/merge.py --predictions "$WS/predictions.json" --odds "$WS/odds.json" --out "$WS/merged.json"
```

产出每场统一对象：各玩法去水概率、比分反推 1X2、各模型"我更看好"一句话、单关标记。

## 第 3 步：读讨论、下判断（你来做）

先读经验库 `experience.seed.md`（共享基线）+ `experience.local.md`（本机累计、冲突时本地优先）：哪个模型在哪类场更可信、嘉豪正文重点看哪类信号、买法有哪些历史教训——作为"可能有效的提示"带进判断（样本少时弱倾斜，别盖过当场推理）。

读 `merged.json`，对勾选的 agent 逐场读其 `discussion_md`（即 `fan_subjective_prediction_md`）：
- 抽方向、3-5 个核心论点（保留球员/区域/数据等细节）、最可能比分、模型间分歧点。
- 对照去水概率找**价值点**（讨论看好但赔率偏高）与**陷阱点**。
- 未勾选模型只用 merge 抽好的 `lean` 做脚注。
- 结合第 1b 步的真实表现校准：把搜到的真实战况（谁压着打、上一场怎么丢球、是否已被逼平、红牌伤停）和讨论对照——真实表现 > 比分、也常 > 旧讨论；据此校准方向与 `most_likely_scores`（**比分一律按 主队:客队 朝向**——模型常“赢家在前”报比分、客队是热门时极易抄反，见 playbook“最可能比分”那条），每队综述写进 `form`。
- **防平诊断（必做）**：对"输赢明显/大热"（一方去水胜率 ≥60% 或赔率 ≤1.3）和"势均力敌易平"（平局去水 ≥28%）的场，选完赢的方向后再单独查一遍会不会平——看平局去水概率、比分榜里平局比分的位置、各家"最容易打脸我的地方"是否集体指向被偷平/闷平/门将爆发。完整判别（数据三件套 + 嘉豪话四件套）见 playbook"二·补 防平诊断"。这是葡萄牙 1:1 那种惨案换来的一步，别省。
- **博冷雷达**：读 `upsets.json` 的本届爆冷史（翻车率、冷平 vs 弱队胜占比——本届 7/8 是冷平，所以默认偏押"大热被逼平"），结合今日各热门的本届前科 / 超低赔结构 / form / 嘉豪冷剧本 / 赔率价值，判出今日最可能爆冷的首选 + 一注备选，写进顶层 `upset_pick`。它与 `draw_guard` 常指向同一场（防平=别买热门赢、博冷=反手押冷），一守一攻、相互印证。完整三步法见 playbook"二·补2"。今天没够格的冷点就留空、别硬凑。

判断口径、信心星级、单关/串关可投性、防平诊断、博冷雷达，全部按 `references/playbook.md`。

## 第 4 步：定三档方案 + 写 analysis.json

按 playbook 的稳健/平衡/激进规则，结合价值点和单关标记，写出 `analysis.json`
（schema 见 `references/playbook.md` 第六节，含 meta / matches / plans）。
- 稳健只取方向一致、可单关的高把握腿；有分歧/未开单关的场次该跳就跳。
- 串关每腿赔率连乘由报告脚本算，你只需列出腿。
- 不写真实金额，只给信心星级 + 仓位语言。
- **`draw_guard`**：对第 3 步查出有平局风险（中/高）的场，填 `draw_guard`（level / draw_prob / signals / hedge，见 playbook 第六节），报告显示"防一手·平局"提示块。默认只提示 + 给对冲思路（押平/双选/别堆串/只锁胜不博比分），不改三档主推——把"要不要防"交给用户，但别让他不知道有这个坑。平局本身有性价比时（概率不低、赔率可观）就在 `value_points` 或 `hedge` 里点出"顺势押平"。
- **`upset_pick`**：把博冷雷达判出的首选 + 备选填进顶层 `upset_pick`（tournament_upsets / primary / alt，见 playbook 第六节），报告渲染成三档下方"最有可能的爆冷"块。独立于三档主推（三档仍以赢的方向为底），信心星级压低、`history_basis` 标本届/H2H 先例。今天没够格的冷点就整个省略。
- **结合复盘**：若经验库/本期复盘指出某模型某类判断更准、某买法倾向屡空，显式据此调整（如"上期让球大胜全空 + DeepSeek 防反更准 → 本期稳健更偏 DeepSeek 的小胜/防反剧本"），并在 `risk_note` 里点一句让用户看到复盘是怎么影响今天的。

## 第 5 步：生成报告

```bash
python scripts/build_report.py --merged "$WS/merged.json" --analysis "$WS/analysis.json" \
  --retro "$PREV/retro.json" --out "$WS/report.html"
```

`--retro` 可选：有第 R 步产出的上期复盘就传，渲染进三档方案下方的"上期复盘回顾"模块；无则省略。

报告已内置 **Anthropic 编辑感**模板（亮：纸感米白 / 暗：对齐 claude.ai 的暖炭灰，陶土橘点缀，Fraunces 衬线标题，价值高亮克制），并支持：

- **双主题**：跟随系统、可手动切换并记忆（侧栏底部按钮）；已声明 `color-scheme`，浏览器的自动深色不会污染浅色版。
- **今日赛程总览**：标题下、三档方案上一块"今日赛程"卡片栅格（圆形队徽 + 队名 + 阶段 + 北京时间 + FIFA 排名 + 未开赛），点任意比赛平滑跳到下方对应分析区。队徽来自 worldcup 站 `assets/teams/{id}-logo-120.png`，由 `fetch_predictions.py` 抓取时 base64 内联（保持离线单文件；CDP 兜底/抓不到时降级纯文字）。
- **左侧目录栏**：大块（赛程/三档/博冷/复盘）+ 逐场（开赛时间 + 全名）跳转、滚动高亮当前所在节；可一键收起/展开（状态记忆到 localStorage），窄屏自动收成 ☰ 目录抽屉。
- **渐进披露**：顶部三档方案用 **Tabs 聚焦切换**（一次看一档、选中档独占全宽面板，腿按内容自动铺多列；PDF 导出时三档自动全展开并各自标注档位）；每场只常驻"结论 + 最可能比分 + 价值点 + 重点玩法（胜平负，缺则比分）"，"全部玩法赔率"和"模型讨论对比"默认折叠，点开再看——解决信息过载。
- **模型品牌图标**：Claude/DeepSeek/Gemini/OpenAI 官方矢量 + GLM/Kimi 简标，内联 SVG、主题自适应，用在观点卡/脚注/采纳模型标签。
- **PDF 导出**：`⤓ 导出 PDF` 按钮（或 Ctrl+P）走 `window.print()`，自动展开所有折叠、隐藏导航/按钮、强制浅色、A4 分页。
- **上期复盘回顾**：三档方案下方一个可折叠模块（传了 `--retro` 才有），渲染上期对账（每场 ✓/⊘/✗）、三档命中、模型校准、本期据此调整。

> 想换风格/重做版式时，可调用 `frontend-design` skill 重新设计模板再回填到 `build_report.py`，保持 Anthropic 调性。模板（CSS/JS/品牌图标 SVG）全部内联在 `build_report.py`，产物为单文件 HTML（仅 Fraunces 字体走 Google Fonts，离线优雅降级到系统衬线）。

## 第 5b 步：用 CDP 打开报告（生成后必做）

报告生成后，用 CDP 在浏览器里把 `report.html` 打开给用户看，别只丢一个路径。

**主路径：web-access 的 CDP Proxy**（最稳——直连用户日常 Chrome，一条 curl 即开）：

- 确认 Proxy 就绪：`localhost:3456` 连得上即可（不确定就跑 web-access 的 `scripts/check-deps.mjs`，已在跑则秒过）。没装 web-access 就按上文「依赖」节先问用户是否安装（`npx skills add eze-is/web-access` 或让你代装），装好再继续。
- 新开后台标签页打开报告的本地文件 URL（v2.5.3 起 `/new` 改 POST、URL 走请求体；Windows 用正斜杠）：
  ```bash
  curl -s -X POST --data-raw "file:///C:/Users/.../runs/<日期>/report.html" http://localhost:3456/new
  ```
  返回 `{"targetId":"..."}`。
- 可顺手截图确认渲染正常：`curl -s "http://localhost:3456/screenshot?target=<上一步返回的 targetId>&file=<临时目录>/r.png"`。

**备选**：当前环境恰好装了 chrome-devtools MCP 时，也可用它（`mcp__chrome-devtools__new_page`；未加载先用 `ToolSearch` 查 `chrome-devtools`）打开同一个 file URL。

打开后在聊天里仍然把 `report.html` 的路径给用户（方便他自己再开 / 导出 PDF）。

## 第 6 步：聊天摘要

在聊天里给一段精炼版：每场一句结论 + 三档方案（关键腿 + 合计赔率）+ 一句"理性投注"。别把报告全文复述一遍，点到为止、引导用户去看报告（本地 `report.html` 或公网站点链接）。

## 第 7 步：发布到每日站点（Vercel）

把第 5 步的 `report.html` **原样**搬上一个公网站点（`web/` 里的 Next.js 应用用 iframe 嵌入报告，一字不改），外面只多两样：**日期切换**看当天/往期、**收益仪表盘**看「我买的票」中没中 + 每日收益。机制、隐私边界、一次性设置全在 `references/site-deploy.md`。

默认**私有模式**：报告/本金/收益 gitignore、不进公开仓库，用 `npx vercel --prod` 从本地直推上线（CLI 不读 `.gitignore`，数据上线但不进 GitHub）。

一次性设置（`cd web && pnpm install && npx vercel login && npx vercel link`）做过后，发布一条命令：

```bash
bash scripts/publish_site.sh \
  --report "$WS/report.html" --analysis "$WS/analysis.json" \
  ${PREV:+--retro "$PREV/retro.json"} --deploy
```

它把 `report.html` 拷进 `web/public/reports/<日期>.html`、登记当天有报告（status=open）；带 `--retro` 时用 `export_site_data.py settle` 回填上一期的票与真实盈亏（status=settled）；`--deploy` 则直接 `npx vercel --prod` 上线。几十秒后刷新链接即可。

- **首次/未设置**：先读 `references/site-deploy.md` 走一次性设置，或用官方 `deploy-to-vercel` 技能部署。别默默跳过——告诉用户站点没建、问要不要现在建。
- **fail-soft**：没装/没登录 Vercel 时不带 `--deploy` 也能把数据备在本地，本地 `report.html` 始终在，不阻塞正事。
- 线上站「有链接即可见」，但**只有你能改**——别人 clone 仓库只能用技能生成自己的报告，碰不到你的部署（原理见 `references/site-deploy.md`）。

---

## 边界

- 只覆盖"未开赛 + 有预测 + 在售"的场次；已封盘/未开售如实告知。
- 某玩法未开售（字段缺失）= 跳过，不脑补倍率。
- 胜平负常常未开放单关（强弱悬殊场尤甚），这类只能进串关，别推成单关。
- 复盘按场次/run 增量去重：已复盘的场次（`reviewed_match_ids`）、run（`own_runs_reviewed`）不再重复，每次只补新的。两条线的范围、顺序、判不了的腿问用户——详见第 R 步。
- **不构成投注建议**；理性娱乐、量力而行。
