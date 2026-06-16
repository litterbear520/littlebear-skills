# 设计：赛后复盘 + 跨期经验累积（自我进化）

> 状态：**已实现（2026-06-16）**。`scripts/retro.py`(locate/score/mark) + `references/experience.md` + `references/reviewed_matches.json` + `build_report.py` 复盘模块 + SKILL.md 第 R 步/第3·4·5步接线 + playbook 第七节 schema 均已落地并用真实数据验证。技能不在 git 仓库内，本文档仅存于技能目录、不提交。

## 目标

给 `worldcup-bet-advisor` 加一个**自我进化闭环**：每次出买法推荐前先做**赛后复盘**，复盘结论**跨期累积**、回灌下一次，越打越准。复盘有**两条线**：

1. **历史规律 backfill**：技能中途上线，前面 嘉豪 已预测过很多已踢完的场次。把所有「已踢完 + 有嘉豪预测 + 没复盘过」的历史场抓回来（比分 + 各模型 嘉豪下注 + 主观预测），洞察**背后规律**——哪个模型/哪类信号更准。用持久 manifest 标记已复盘的 `match_id`，**增量**、踢过的不重复。
2. **上一期推荐复盘**：对上一期我们自己生成的报告里的三档买法判 hit/miss，**问用户上次实际买了哪个**，分析当时策略 vs 最终结果，沉淀经验。

**红线**：这是世界杯预测分析（**模型判断驱动**），**不是**按数字算命中率自动改买法的计算引擎。脚本只管确定性事实（拉终场比分、逐条对账命中、各模型方向对错）；所有规律洞察、校准、买法调整都是模型的分析。

## 核心闭环（时间错位）

第 N 期比赛踢完才能复盘，所以**复盘在第 N+1 期触发时做**：

```
第 N+1 期触发
  └─ [新] 第 R 步 赛后复盘（触发后最先做）
       Track 1 历史规律 backfill（增量）
         1. retro.py 扫 index(--include-finished) − reviewed_matches.json → 未复盘的已赛+有预测场
         2. 子 agent 分治：每个子 agent 领一批 match → 抓比分+各模型 bet+主观预测 → 析方向对错与可信信号
            → 只回结构化小结（不回原文，保主 agent 上下文）
         3. 主 agent 汇总 → 更新 experience.md（模型校准/信号/买法倾向）→ 把这批 match_id 标记进 manifest
       Track 2 上一期推荐复盘
         4. 定位上一期我们自己的 run（runs/<date>/analysis.json、已赛、own_runs_reviewed 里没有）
         5. retro.py 拉终场比分、逐条对账三档/价值点/陷阱点 → retro_facts.json
         6. [交互] 问用户上次实际买了哪档/哪些腿（AskUserQuestion）
         7. 模型复盘策略 vs 结果 → 写 runs/<date>/retro.json + 追加 experience.md
            + 记 own_runs_reviewed + 把该 run 的 match_id 并入 reviewed_match_ids（避免 Track 1 重复分析同批场）
  └─ 第 0 / 0b 步 选场 / 选 agent（原样）
  └─ 第 1 / 2 步 抓数据 / 合并去水（原样）
  └─ 第 3 步 读讨论下判断 ←[改] 先读 experience.md，回灌倾向
  └─ 第 4 步 定三档方案 ←[改] 显式结合本期复盘结论调整买法
  └─ 第 5 步 生成报告（三档方案【下面】渲染"上期复盘回顾"模块）
  └─ 第 5b / 6 步 CDP 打开 / 聊天摘要（原样）
```

## 两条复盘线（细节）

### Track 1 — 历史规律 backfill（子 agent 分治、增量）
- **目的**：从大量历史场快速学到"哪个模型/哪类嘉豪信号更准"的规律。历史场**没有我们自己的推荐**，只有 嘉豪 各模型的下注与主观预测 vs 终场——所以这条线分析的是 **嘉豪 模型准度与信号规律**，不是我们的买法。
- **pacing**：首次**全量**（可能很多场）用子 agent 分治并行；之后每次触发只增量消化新结束的未复盘场。
- **脚本管事实**：`retro.py` 对一批 match 算每个模型 `bet` 方向 vs 实际 result 的对错（确定性）。
- **子 agent 管语言层规律**：每个子 agent 领一批 `match_id`，抓 `fan_subjective_prediction_md`，提炼"哪类信号（门将评分/体能/盘口/边路点）与押对相关"，返回**结构化小结**（不回原文）。
  - 子 agent prompt 目标导向：抓这批比赛的嘉豪预测与讨论+比分、洞察各模型方向对错与可信信号、返回小结；直连被阻断则加载 web-access skill 走 CDP。
- **主 agent**：汇总各子 agent 小结 + 脚本对错数据 → 增量更新 `experience.md` → 把这批 `match_id` 写进 `reviewed_matches.json`。

### Track 2 — 上一期推荐复盘（grade + 问用户 + 分析）
- 定位上一期我们生成的 run（有 `analysis.json`、比赛已赛、`own_runs_reviewed` 里还没有）。
- `retro.py` 对账上期三档每条腿 / 价值点 / 陷阱点 → hit/miss（陷阱点判"是否正确避开"）。
- **[交互] 问用户上次买了哪个**：`AskUserQuestion` 列出上期三档（稳健/平衡/激进）及关键腿，让用户选实际买了哪档/哪些腿（含"没买/只看"选项）。
- 模型据「我们的推荐 + 用户实际所买 + 终场」复盘：策略对不对、用户那一注中没中、哪个模型这几场更靠谱、嘉豪正文哪类信号被验证、大方向对不对、下次怎么调整 → 写 `runs/<date>/retro.json` + 追加 `experience.md` + 记 `own_runs_reviewed`。
- `retro.json` 渲染进 N+1 报告（三档方案下面）。

## 文件与接口

| 文件 | 角色 | 谁写 |
|---|---|---|
| `references/experience.md` | **跨期累积"大脑"**：模型校准 / 嘉豪正文可信信号 / 买法倾向 / 复盘日志。开头声明"是可能有效的提示、非铁律、样本少弱倾斜"。第3步必读 | 模型 |
| `references/reviewed_matches.json` | **复盘 manifest**：已复盘的 match_id 集合 + 已复盘的自有 run | 脚本+模型维护 |
| `runs/<date>/retro.json` | 那一期 Track 2 的结构化复盘（事实+判断），渲染进下期报告 | 脚本事实+模型判断 |
| `scripts/retro.py`（新） | 事实层：定位未复盘场、拉终场比分、逐条对账、各模型方向对错 | 纯脚本 |

`reviewed_matches.json`：
```json
{ "reviewed_match_ids": ["54329959", "54329956"], "last_synced": "2026-06-16", "own_runs_reviewed": ["2026-06-15"] }
```

`retro.json`（Track 2）：
```json
{
  "reviewed_run": "2026-06-15", "reviewed_at": "2026-06-16",
  "user_bought": {"tier": "平衡", "legs": ["比利时 胜(单关)", "比利时+伊朗 2串"], "note": "或：没买/只看"},
  "matches": [
    { "match_id": "54329956", "teams": "比利时 vs 埃及",
      "final_score": "2:1", "result": "主胜",                       // 脚本
      "graded": [ {"play": "比利时 胜(单关)", "from": "稳健", "hit": true},
                  {"play": "让胜(比利时 -1)", "from": "陷阱点", "would_hit": false, "warned_correctly": true} ],  // 脚本
      "model_results": [ {"brand":"Claude","bet_direction":"比利时胜","right":true} ],  // 脚本
      "model_take": "两家押小胜，2:1 印证。" }                        // 模型
  ],
  "plans_review": { "steady": {"legs":1,"hit":1,"verdict":"..."}, "balanced": {"verdict":"..."}, "aggressive": {"verdict":"..."} },
  "user_result": "用户买的平衡档：底仓命中、小串中/飞 …（结合 user_bought 与 graded）",   // 模型
  "model_calibration": [ {"brand":"DeepSeek","direction_right":"3/4","note":"防反/门将 reads 准"} ],
  "jiahao_signal_lessons": ["门将扑救评分高→低比分验证"],
  "big_direction_verdict": "强队一致胜进串、对冲跳过——整体正确。",
  "next_adjustments": ["冲突时略偏 DeepSeek 防反/险胜", "强主慎追让-2"]
}
```

`experience.md` 结构：开头声明 + 三小节（模型校准 / 嘉豪正文重点看哪里 / 买法倾向）+ 末尾按日期追加的复盘日志。Track 1 与 Track 2 都增量更新这三小节。

## 脚本 vs 模型 vs 子 agent 分工

| | retro.py（脚本） | 子 agent（Track 1 并行） | 主 agent / 模型 |
|---|---|---|---|
| 终场比分、各玩法结果、逐条 hit/miss、各模型方向对错 | ✓ | | |
| 历史大批量的语言层信号规律挖掘 | | ✓（分治、只回小结） | |
| 汇总规律、写 experience.md、判断校准与买法调整 | | | ✓ |
| 问用户买了哪个、分析其结果、写 retro.json 判断字段 | | | ✓ |

## 报告里的"上期复盘回顾"模块

- 位置：**三档方案下面**，紧凑、**可折叠**。
- 内容：上期每场一行（终场比分 + 上次推过什么 + ✓/✗）、三档命中小结、**你上次买的那一注中没中**、一行模型校准结论、"本期据此调整了什么"一句话；末尾一行 Track 1 同步提示（"本次新增分析 N 场历史，规律沉淀于经验"）。
- 视觉：沿用已对齐 claude.ai 的深浅色；命中=柔和绿、未中=灰、结论用陶土橘点缀。
- `build_report.py` 新增 `render_retro(retro)` + CSS；`build` 接收可选 `--retro runs/<date>/retro.json`，有则在三档方案后渲染。

## 回灌（payoff）

- **第 3 步**先读 `experience.md` → 冲突时倾向历史更准的模型剧本、重点读正文里被验证可信的信号段落。
- **第 4 步**定三档时显式写明"因历史/上期…所以本期稳健更偏…"，让下一期买法**带着复盘结论**出。

## 边界 / 冷启动

- 首次运行：Track 1 做大批量历史 backfill（子 agent 分治）；Track 2 无上期则跳过。
- 没有上一期 / 上期还没踢完 → Track 2 优雅跳过，报告无复盘模块。
- 上期部分踢完 → 只复盘已结束的场次，未完的挂起。
- `reviewed_match_ids` 防重复；某场只复盘一次。
- `experience.md` 过长 → 复盘时可合并老经验（**本版不做**）。

## 不做（YAGNI）

- 不做命中率计算引擎 / 自动按数字调买法（全靠模型判断）。
- 不做独立复盘 HTML 报告（只在主报告加模块）。
- 不做经验文件自动压缩/归并。
