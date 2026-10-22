# 数据源与字段字典

两个数据源，两个脚本各管一个。**两侧接口都能直接 urlllib/curl 拉到（带 Referer 即可）**，
脚本默认直连；若被网络环境/反爬阻断，再走 CDP 兜底（见末尾）。

---

## 一、预测侧 — worldcup.lyihub.com（"嘉豪世界杯预测"）

纯静态 JSON，无需登录、无需浏览器。`scripts/fetch_predictions.py` 负责。

### 赛程索引 `https://worldcup.lyihub.com/data/index.json`
```
{ generated_at, server_now, competition_name,
  matches: [ {
    match_id,            # worldcup 比赛 id，如 "54329959"
    kickoff_at,          # UTC ISO，如 "2026-06-15T16:00:00+00:00"（北京时间 +8h）
    stage, team_a, team_b, team_a_id, team_b_id, venue,
    has_predict,         # true=有模型预测
    bets: {H:[模型短键...], D:[...], A:[...]},   # 各方向有哪些模型"下注"
    comment: {模型短键: "我更看好: X"},          # 每个模型一句话（6 个都有）
    score: {team_a, team_b} | null               # null=未踢；有值=已赛 → 选场时默认排除
  } ] }
```
- "未开赛 + 有预测" = `has_predict==true 且 score==null` → 这是选场候选集。
- **队徽**：`https://worldcup.lyihub.com/assets/teams/{team_a_id|team_b_id}-logo-120.png`（120px 圆形 PNG，约 5-6KB）。`fetch_predictions.py matches` 抓取时按 team id 下载并 base64 内联进 `predictions.json` 的 `team_a_logo`/`team_b_logo`，供报告"今日赛程"卡与比赛卡头部渲染（离线单文件；`--raw-dir` 兜底时不抓、降级纯文字）。
- 注意 `bets` 里只列**下了注**的模型；像 Claude 可能写了讨论但 `暂无投注`，不会出现在 bets，但会出现在 `comment`。判断"哪些 agent 有讨论"应看 `comment` 的键（6 个模型几乎总是齐全）。

### 单场详情 `https://worldcup.lyihub.com/data/matches/{match_id}.json`
```
{ match: { match_id, kickoff_at, stage, team_a, team_b, ..., score, weather, temperature,
           odds:[{pool_code:"HHAD", HHAD_line, H,D,A}] },   # 站点自带简版赔率，仅 1 条，仅参考
  team_profiles, players,
  llm_predict: [ {
    llm_id,
    model_name,                     # 具体型号，如 "claude-opus-4-6" / "deepseek-v4-pro"
    status,                         # "ok"
    bet: {pool_code, selection_code, stake_amount} | {},   # {}=暂无投注
    teams: {A:{战术预测...}, B:{...}},
    fan_subjective_prediction_md,   # ★就是"讨论"正文（markdown），各模型以"嘉豪"口吻写的主观预测
    artifacts: {team_a_tactic_md, team_b_tactic_md, fan_subjective_prediction_md, jiahao_bet_md}
                                    # jiahao_bet_md 只是个文件路径指针，不含正文，忽略
  } ] }
```

### model_name → 厂牌（动态读取，不写死版本号）
| 厂牌 | model_name 关键词 | index 短键 |
|---|---|---|
| DeepSeek | `deepseek` | deepseek |
| Claude | `claude` | claude |
| GPT | `gpt` / `openai` | openai |
| Gemini | `gemini` | gemini |
| GLM | `glm` | glm |
| Kimi | `kimi` | kimi |

当前快照型号：`deepseek-v4-pro` / `gpt-5.5` / `claude-opus-4-6` / `gemini-3.5-flash` / `glm-5.1` / `kimi-k2.6`。
版本会升级，**脚本用关键词匹配厂牌、原样保留 model_name**，UI 显示成"Claude · claude-opus-4-6"。

### bet 方向解码
- `pool_code=="HAD"`（胜平负）：H=主胜, D=平, A=客胜
- `pool_code=="HHAD"`（让球胜平负）：H=主队让球赢盘, D=让球走盘(平), A=客队让球赢盘
  - 例：西班牙(主)让 -2，DeepSeek bet `HHAD/A` = 押"佛得角 +2 让负方向"（即西班牙赢但净胜＜2 也算赢）。

---

## 二、倍率侧 — jj.zhenzhunsp.cn（"好运计算器"，接口在 justpost.haoyun999.cn）

`scripts/fetch_odds.py` 负责。两个接口都带 `Referer: https://jj.zhenzhunsp.cn/`。

### 在售列表 `GET https://justpost.haoyun999.cn/api/Game/GetSimpleMatchsAll?dateFormat=&notSingle=false&mKind=0&reqtype=0`
```
{ code:0, info:"2026-06-15 周一",
  data:[ { dateFormat:"2026-06-15 周一", list:[ {
    matchId(竞彩内部id,数字), matchGuid, lotteryId("周一013"),
    homeChs, awayChs, homeId, awayId, homeRank, awayRank(FIFA排名),
    leagueChs, matchTime("2026-06-16T00:00:00", 北京时间),
    goalFoot(让球线,如 -2),
    spfWinFoot/spfEqualFoot/spfLoseFoot(胜平负倍率, 未开放单关时为 null),
    rspfWinFoot/rspfEqualFoot/rspfLoseFoot(让球胜平负倍率),
    singleSpfFoot/singleRqspfFoot(能否单关),
    footMatchState(0=未开赛)
  } ] } ] }
```
- 这是"当前竞彩日在售"的全部足球比赛；用来判断 worldcup 选场是否"在售"。
- **竞彩日边界 = 12:00 ~ 次日 12:00**。所以北京时间 00:00 的西班牙(实际 06-16 凌晨)归在 06-15 竞彩日。

### 单场全玩法 `GET https://justpost.haoyun999.cn/api/Game/GetMoreSpInfo?matchId={竞彩matchId}&mKind=0`
```
{ code:0, data:{ footballMoreSpInfo:{
  matchId, lotteryid, hometeamchs, homerank, awayteamchs, awayrank, matchtime,
  singlespf, singlerqspf, singlebf, singlejq, singlebqc,   # 各玩法能否单关
  spf_win/spf_draw/spf_lost,                # 胜平负(可能 null)
  rfspf_goal(让球线 string), rfspf_win/rfspf_draw/rfspf_lost,   # 让球胜平负
  # —— 比分 ——（字段名 = s + 方向 + 主客进球；缺的比分进"其他"桶）
  sw10 sw20 sw21 sw30 sw31 sw32 sw40 sw41 sw42 sw50 sw51 sw52   # 主胜各比分 sw{主}{客}
  sw5                                                            # 胜其他
  sd00 sd11 sd22 sd33                                            # 平局 sd{n}{n}
  sd4                                                            # 平其他
  sl01 sl02 sl03 sl12 sl13 sl23 sl04 sl14 sl24 sl05 sl15 sl25    # 客胜各比分 sl{主}{客}
  sl5                                                            # 负其他
  # —— 总进球 ——
  t0 t1 t2 t3 t4 t5 t6 t7        # 全场总进球 0..6，t7 = 7+
  # —— 半全场 ——（ht{半场}{全场}，数字 3=主胜 1=平 0=客胜）
  ht33 ht31 ht30 ht13 ht11 ht10 ht03 ht01 ht00
}, basketballMoreSpInfo } }
```
- 某玩法字段为 null/缺失 = 该选项未开售，脚本跳过。
- 西班牙强主时典型表现：`ht33`(半全场主/主)赔率最低、比分 `sw30`(3:0) 偏低、让胜 `rfspf_win` 偏低 → 与"大胜赢盘"一致。

---

## 三、跨站匹配

worldcup 与竞彩两侧**用中文队名匹配**，主客顺序一致（两边 home=team_a）。
名称偶有出入（"沙特阿拉伯" vs "沙特"、显示截断的"阿尔及利"），脚本用**子串模糊匹配**
（去空格后任一方为另一方子串即同队），实测可覆盖这些差异。

---

## 四、去水概率（merge.py 计算）

- 隐含概率 `implied = 1/赔率`。
- 一场内同一玩法归一化 `fair = implied / Σimplied`（消除庄家水位/抽水）。
- `margin = Σimplied − 1` = 该玩法的总抽水。
- 比分市场可反推 1X2：把各比分的 fair 按 side(主/平/客)聚合，与胜平负市场互校验。
- **去水概率是"市场认为的概率"，不是真理**；价值判断是把它和模型讨论的信心对比。

---

## 五、CDP 兜底（仅当直连被阻断时）

直连失败时，用 web-access skill 的 CDP proxy 在浏览器上下文里 `fetch` 同样的接口拿到 JSON，
存成本地文件，再喂给脚本：
- `fetch_predictions.py --raw-dir <dir>`：目录里放 `index.json` / `{match_id}.json`
- `fetch_odds.py --raw-list <file> --raw-detail-dir <dir>`：详情文件名用竞彩 `{matchId}.json`

走 CDP 前必须先向用户展示 web-access 的反爬风险须知。
