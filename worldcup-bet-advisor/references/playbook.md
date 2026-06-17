# 玩法决策手册

技能的"灵魂"在这里：怎么把"模型讨论 + 实时倍率"变成最终的三档玩法。
核心原则：**讨论为主、倍率校验**——先看采纳模型的讨论方向，再用去水概率找性价比/价值点。

---

## 一、读讨论（产出每场判断）

对**用户勾选的 agent**（默认 Claude + DeepSeek），逐个读 `fan_subjective_prediction_md`，
抽出这几样写进 analysis：
- **方向**：胜/平/负、让球赢盘/输盘、看好谁。优先用结构化 `bet`；`bet=={}`（暂无投注）时从讨论判断倾向。
- **3-5 个核心论点**：原文里"我真正看重的点 / 我不太买账的点"，保留具体细节（球员、区域、数据分位），这是价值所在。
- **最可能比分**：讨论里常直接写"最可能比分：X"。
- **分歧点**：勾选的多个模型之间哪里一致、哪里冲突。冲突往往就是价值/风险的来源。

未勾选的模型：**只取一句"我更看好"**（merge.py 已抽好 `lean`）做脚注，不读正文。

---

## 二、倍率校验 + 找价值

把讨论方向和去水概率对照：
- **一致且赔率合理** → 进稳健候选。
- **价值点**：讨论里**明确看好**、但市场去水概率给得**偏低**（赔率偏高）的选项。
  例：DeepSeek/GPT 都说"西班牙难净胜两球"，而"让负(客+2)"市场只给 23% → 这是价值点，写进 `value_points`。
- **陷阱点**：市场很热 / 赔率极低（去水概率很高），但讨论里有人点出明确风险 → 别当稳胆，写进 `trap_points`（报告会以"避雷"块琥珀警示呈现，与价值点的陶土橘形成"机会 vs 风险"对照）。典型如热门强队但勾选模型有人押冷、或"穿盘大胜"看着诱人但两家都说不会大胜。
- 别迷信去水概率，它只是市场共识；模型讨论提供的是市场没充分定价的信息（伤停、战术克制、状态）。

判断"单关 vs 仅过关"：看 `singles` 标记（spf/rqspf/score/goals/htft 各自布尔）。
**只有标记可单关的玩法才能进单关方案**；否则只能进串关。胜平负常常未开放单关（尤其强弱悬殊场）。

---

## 三、三档方案

每次都给三档，让用户临场自己挑。

### 稳健（calm）— 求命中率
- 只取**勾选模型方向一致**、且赔率不过低也不过高的**单关**。
- 宁缺毋滥：某场有输盘分歧、或胜平负未开单关，就**跳过该场**，别硬凑。
- 每腿给信心星级（0-5）和一句理由。

### 平衡（mid）— 命中与回报兼顾
- 一组**核心单关**（稳健底仓）+ **1 个 2-3 腿小串**。
- 小串每腿都要高把握；避免把两个"博"的腿绑一起（串关命中率是各腿相乘，越串越低）。

### 激进（bold）— 博高回报
- **跨场串关**博高赔（可多组），顺着讨论里的"博冷剧本"（如险胜输盘、爆冷、大比分）。
- 加少量**高赔单关**（讨论支持的比分/总进球/半全场）。
- 明说这是低命中、高回报，容忍踢飞。

### 串关赔率
合计赔率 = 各腿赔率连乘（build_report.py 会自动算）。串关任一腿不中则整串作废。

---

## 四、信心星级口径（写 confidence: 0-5）
- 5：勾选模型方向一致 + 去水概率高 + 无明显风险点。
- 4：方向一致，小瑕疵或赔率略低。
- 3：方向基本一致但有分歧/风险，或博中等赔。
- 2：跟某一个模型的"博"判断（如险胜输盘、爆冷）。
- 1：纯博冷/高赔比分。

---

## 五、底线（务必遵守）
- **不报真实下注金额**，只给信心星级 + 相对仓位语言（底仓/小注/博一点）。
- 报告底部固定"理性投注"提示（build_report.py 已内置 disclaimer，可按需覆盖）。
- 不承诺胜率、不打包票；明确"模型分析 ≠ 投注建议"。
- 数据有缺口（某场无倍率、未开售）时如实标注，不脑补。

---

## 六、analysis.json 结构（模型产出 → 喂给 build_report.py）

```json
{
  "meta": {
    "date": "2026-06-15 周一",
    "generated_at": "YYYY-MM-DD HH:MM",
    "selected_agents": ["Claude", "DeepSeek"],
    "risk_note": "一句话总基调（可选）"
  },
  "matches": [
    {
      "match_id": "54329959",
      "headline": "一句话抓重点的结论",
      "consensus": "方向一致点 / 分歧点说明",
      "agent_views": [
        { "brand": "Claude", "model_name": "claude-opus-4-6",
          "stance": "西班牙3-0大胜·暂无投注",
          "points": ["论点1(带细节)", "论点2", "论点3"] },
        { "brand": "DeepSeek", "model_name": "deepseek-v4-pro",
          "stance": "赢球输盘·押客让·最可能2:1", "points": ["...", "..."] }
      ],
      "most_likely_scores": ["3:0", "2:0", "2:1"],
      "value_points": [
        { "play": "让负", "odds": 3.85, "market_prob": 0.23,
          "why": "为什么这是价值点" }
      ],
      "trap_points": [
        { "play": "胜", "odds": 1.31, "market_prob": 0.676,
          "why": "为什么这是陷阱（市场热但勾选模型有人明确反对/点出风险，别当稳胆、别进稳健单关）" }
      ]
    }
  ],
  "plans": {
    "steady":   { "title": "...", "sub": "...", "legs": [ {"match":"周一014 比利时","play":"比利时 胜(单关)","odds":1.41,"confidence":4,"reason":"..."} ], "note":"..." },
    "balanced": { "title": "...", "sub": "...", "singles":[ {leg} ], "parlay": {"legs":[ {leg}, {leg} ], "note":"..."}, "note":"..." },
    "aggressive": { "title": "...", "sub": "...", "parlays":[ {"legs":[ {leg}, {leg} ], "note":"..."} ], "singles":[ {leg} ], "note":"..." }
  },
  "disclaimer": "可选，覆盖默认理性投注提示"
}
```
- `leg` 字段：`match`(显示名，如"周一013 西班牙")、`play`(玩法文字)、`odds`(数字)、`confidence`(0-5，可选)、`reason`(可选)。
- `value_points[].play` 的文字若与倍率表里的选项 label/sel 一致（如"让负"、"2:1"），报告会自动把对应格子高亮成"价值"。
- `trap_points`（可选，0-2 个）：字段同 `value_points`（`play`/`odds`/`market_prob`/`why`，后两者可省）。没有明显陷阱就留空；不要为凑数硬写。
- 留空的部分可省略；缺 analysis 条目的比赛报告会以"仅数据"呈现。

---

## 七、retro.json 结构（第 R 步 Track 2 产出 → 喂给 build_report.py --retro）

模型据「上期 analysis.json + retro_facts.json（脚本算的终场/对错）+ 用户实际所买」写成。事实字段抄 `retro_facts.json`，判断字段你写。

```json
{
  "reviewed_run": "2026-06-15", "reviewed_at": "2026-06-16",
  "user_bought": { "tier": "平衡", "legs": ["比利时 胜(单关)"], "note": "或：没买/只看" },
  "user_result": "你买的那注中没中的一句话总结",
  "matches": [
    { "match_id": "54329956", "teams": "比利时 vs 埃及",
      "final_score": "1:1", "result_side": "平局",                       // 脚本(retro.py score)
      "graded": [                                                        // 你判：上期每条推荐对账
        {"play": "比利时 胜(单关)", "from": "稳健", "hit": false},
        {"play": "让胜(比-1) 已避开", "from": "陷阱点", "would_hit": false, "warned_correctly": true} ],
      "model_take": "这场的一句复盘（谁对谁错、为什么）" }
  ],
  "plans_review": {
    "steady":   {"legs": 1, "hit": 0, "verdict": "..."},                // legs/hit 可省；verdict 必有
    "balanced": {"verdict": "..."}, "aggressive": {"verdict": "..."} },
  "model_calibration": [ {"brand": "DeepSeek", "direction_right": "2/3", "note": "更可信在哪"} ],
  "jiahao_signal_lessons": ["被验证可信的信号1", "..."],
  "big_direction_verdict": "大方向对不对一段话",
  "next_adjustments": ["下次买法怎么调1", "..."],
  "historical_synced": 15                                               // 可选：本次 Track 1 新分析的历史场数
}
```
- `graded[].hit`=命中；`warned_correctly`=陷阱点正确避开（渲染成 ⊘ 琥珀）；其余渲染成 ✗。
- **半全场/半场等脚本判不了的腿**：`hit` 必须来自**用户确认**（见 SKILL.md 第 R 步 Track 2 "判定分两层"），不要写 null 猜、也不要"存疑"含糊；确实还没结算才用 `null` 并在 `note` 写"待结算"。
- 渲染位置：三档方案**下方**的"上期复盘回顾"可折叠模块。
- 这些判断同时增量沉淀进 `references/experience.md`（跨期累积大脑）。
