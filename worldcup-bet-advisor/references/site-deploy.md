# 每日站点：Vercel 部署 & 发布

把每天的报告做成一个**公网可访问的站点**:`report.html` 原样嵌入(iframe),外面只多两样——**日期切换**(看当天/往期)+ **收益仪表盘**(中没中卡片 + 每日收益)。报告本体一字不改,还是 `build_report.py` 那套版式。

## 谁能看、谁能改(先讲清原理)

- **线上站只有你能改**:Vercel 部署绑定的是**你账号下的项目**。别人 `git clone` 你的公开仓库,只能拿到**只读副本**——他们能本地跑、能 fork 出去部署**他们自己的**站,但 push 不进你的仓库、碰不到你的 Vercel 项目。所以「技能共享、部署独占」天然成立:别人 clone 下来只能**用技能生成自己的报告**,改不了你的在线报告。
- 能改到你线上站的只有:你主动合并别人的 PR / 把人加成协作者 / 凭证泄露。光 clone 做不到。
- **「读」和「改」分开**:clone 能读仓库里**已提交**的东西。当前启用**公开模式**(报告/本金/收益入库 + push 自动部署,见下),想改回不公开见「私有模式(备选)」。

## 私有模式(备选):数据不进 GitHub,CLI 部署

- **应用代码**(`web/` 下的组件/配置)随 skill 提交进 littlebear-skills——纯前端、可公开。
- **每天的报告 + 本金 + 收益**(`web/data/*.json`、`web/public/reports/*.html`)被 `.gitignore`,**不进 GitHub**。
- 发布用 `npx vercel --prod`:Vercel CLI 上传的是**本地工作目录**(它不读 `.gitignore`),所以这些数据**上线但不进公开仓库**。

工具链:本机已装 Node + pnpm。Vercel 免费 Hobby 套餐即可。

### 一次性设置(约 3 分钟)

```bash
cd <本 skill 目录>/web      # 形如 .../littlebear-skills/worldcup-bet-advisor/web
pnpm install               # 装依赖
npx vercel login           # 用你的账号登录(GitHub 登录即可)
npx vercel link            # 在这个目录建/连一个 Vercel 项目(按提示选 create new)
```

`link` 完会生成 `web/.vercel/`(已 gitignore)。之后这个目录就认得你的项目了。

> 想更省心,也可以用官方 **deploy-to-vercel** 技能(`npx skills add vercel-labs/agent-skills@deploy-to-vercel`)代跑这套 CLI。

### 每天发布(技能第 6 步自动调用)

```bash
# 当天:把报告嵌进站点 + 登记日期(--date);自己买过且要结算上一期就带 --retro 指向极简
# settle.json(结构见 SKILL.md 第 6 步)回填票与盈亏;--deploy 直接上线
bash scripts/publish_site.sh \
  --report "$WS/report.html" --date <YYYY-MM-DD> \
  ${PREV:+--retro "$PREV/settle.json"} --deploy
```

- 不带 `--deploy`:只在本地把数据/报告备好,最后自己 `cd web && npx vercel --prod`。
- push 后几十秒,刷新你的 Vercel 链接就能看到当天报告;日期下拉可切往期;「收益仪表盘」看收益。

### 数据节奏(为什么分两次)

| 时点 | 写什么 | status |
|---|---|---|
| **当天**出完报告 | 拷 `report.html` 进站点 + 登记日期(`hasReport`) | `open` |
| **次日**复盘上一期 | 回填上一期 `tickets`(中/未中)+ `dayProfit` | `settled` |

收益仪表盘的累计/柱状图 = 各 `settled` 日 `dayProfit` 汇总(exporter 重建进 `index.json`)。

## 公开模式(✅ 当前启用):push 自动部署

报告/本金/收益**提交进公开仓库**,Vercel 接 GitHub 自动部署 —— 多机(家里/公司)只靠 `git pull/push` 同步,无需 Vercel CLI。代价:真实本金/收益在公开仓库可读(但别人仍**改不了**你的线上站)。一次性设置:

1. ✅ `web/.gitignore` 已注释掉 `data/`、`public/reports/` 两行(数据改为入库)。
2. ✅ Vercel 项目已用 `npx vercel git connect <repo-url>` 连上 `litterbear520/littlebear-skills`。
3. ⬜ **(需在 Vercel 后台手动设一次)** 项目 `worldcup-bet-site` → Settings → Build and Deployment → **Root Directory** 填 `worldcup-bet-advisor/web` → Save。本仓库是 monorepo、Next.js 应用在子目录,不设这个 Git 构建会在仓库根找不到 `package.json` 而失败。
4. 之后日常发布 = 出报告 + settle 后 `git add` 数据 → `git commit` → `git push`,Vercel 自动上线;`publish_site.sh` 不再需要 `--deploy`。

**多机同步**:任意电脑 `git clone` 本仓库(历史数据随仓库一起下来)+ 配好 litterbear520 的推送凭证(`gh auth login` 登 litterbear520 / PAT / SSH key),即可 `pull → 出报告 → commit → push`。推送权限看的是**登录凭证**,不是 commit 署名。

> 想改回不公开:把 `web/.gitignore` 里那两条 `data/`、`public/reports/` ignore 取消注释,数据回到只存本地 + 经 `.vercelignore` 由 `npx vercel --prod` 上传(见上「私有模式(备选)」),但多机同步需另配私有数据通道。

## 本地预览

```bash
cd <skill>/web && pnpm build && npx next start -p 3100   # 打开 http://localhost:3100
# 注意:改了代码要先重新 build 再 start,否则会引用到旧的静态资源(白屏)。开发时用 pnpm dev 免此问题。
```

## 排错

- **构建失败**:本地 `pnpm build` 能过即可定位;Vercel 项目 Settings 确认 Node ≥ 18。
- **报告页空白**:`web/public/reports/<日期>.html` 是否存在、`data/index.json` 的 `reportDates` 是否含该日。
- **仪表盘没数据**:`data/` 里有没有 settled 的日期文件(复盘 settle 过)。
- **CLI 部署报未登录**:`npx vercel login` 再 `npx vercel --prod`。
