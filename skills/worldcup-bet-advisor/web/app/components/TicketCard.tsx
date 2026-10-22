import type { Ticket, TicketLeg } from "@/lib/types";
import { yuan, plainYuan, odds, tierColorVar } from "@/lib/format";

// Mirrors a real 竞彩 票面: a 玩法 + 倍数 + 合计 header, one block per match
// (第N场 · 赛事编号 · 玩法类别 / 主队 VS 客队 / 选择@赔率 + 命中标记), then a result
// footer (倍率 / 回报 / 盈亏). Won tickets get the red 「中」 stamp. Legs missing the
// structured fields fall back to the plain `text` line so old data still renders.

// 一腿显示的选择项。历史 settle 数据的 `text` 写法五花八门：结构化 pick、
// "主队 vs 客队 [2:0 / 3球]" 复式简写、纯文本。这里统一解析：
// 剥掉与票头重复的队名，"[A / B]" 拆成独立选项，纯比分/N球补上玩法名。
type PickChip = { tag?: string; label: string };

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// 给光秃秃的选项补玩法名："2:0"/"比分2-0" → 比分 2:0，"3球"/"总进球3" → 总进球 3球
function tagPick(raw: string): PickChip {
  const s = raw.trim();
  let m = s.match(/^(?:比分\s*)?(\d{1,2})\s*[:\-]\s*(\d{1,2})$/);
  if (m) return { tag: "比分", label: `${m[1]}:${m[2]}` };
  m = s.match(/^(?:总进球\s*)?(\d{1,2})\s*球?$/);
  if (m && /球|总进球/.test(s)) return { tag: "总进球", label: `${m[1]}球` };
  return { label: s };
}

function legPicks(leg: TicketLeg): PickChip[] {
  if (leg.pick) return [{ label: leg.pick }]; // 结构化 pick 已是精确文案，原样
  let s = (leg.text ?? "").trim();
  if (!s) return [];
  const br = s.match(/\[([^\]]+)\]/); // 复式简写：[2:0 / 3球] → 每个选项一枚 chip
  if (br) {
    return br[1].split("/").map((x) => x.trim()).filter(Boolean).map(tagPick);
  }
  if (leg.home && leg.away) {
    // 票头已有 主队 Vs 客队，text 里再出现同样前缀就是冗余
    s = s
      .replace(
        new RegExp(`^${escapeRe(leg.home)}\\s*(?:vs|VS|Vs)\\s*${escapeRe(leg.away)}\\s*[·:：\\-]?\\s*`),
        "",
      )
      .trim();
  }
  return s ? [tagPick(s)] : [];
}

// 选择行：单选项贴原样式，多选项（复式）逐枚 chip 展示
function Picks({ leg }: { leg: TicketLeg }) {
  const picks = legPicks(leg);
  const multi = picks.length > 1;
  return (
    <span className="leg-pick">
      {picks.map((p, j) => (
        <span className={multi ? "pick-chip" : "pick-sel"} key={j}>
          {p.tag ? <i className="pick-tag">{p.tag}</i> : null}
          {p.label}
        </span>
      ))}
      {leg.odds != null ? <span className="pick-odds">@{odds(leg.odds)}</span> : null}
    </span>
  );
}
export default function TicketCard({ ticket }: { ticket: Ticket }) {
  const tierVar = tierColorVar(ticket.tier);
  const isWin = ticket.status === "win";
  const profitColor = isWin
    ? "var(--success)"
    : ticket.status === "loss"
      ? "var(--danger)"
      : "var(--text-tertiary)";

  // 玩法 label: 单关 → 单场固定, otherwise 过关方式 N串1 (matches the printed slip)
  const play = ticket.type === "单关" ? "单场固定" : ticket.mode === "independent" ? ticket.type : `过关方式 ${ticket.type}`;
  // 倍数: explicit if recorded, else derive from stake。竞彩一注(一个组合)一倍 = 2 元，
  // 复式票 stake 摊给全部注：倍数 = 本金 / (2 × 注数)，如 复式8注 ¥16 = 8注 × 1倍
  const multiple = ticket.multiple ?? (ticket.stake ? Math.round(ticket.stake / 2 / (ticket.combos ?? 1)) : null);
  // 复式/系统过关（如 5场4关=28注）：没有单一连乘赔率，页脚改显「N注·命中X场」
  const isCombo = ticket.combos != null && ticket.combos > 1;
  const hitMatches = ticket.legs.filter((l) => l.hit === true).length;

  // 独立多注票（单场固定·多个比分）：按场分组、每注一行，不挤成一团
  if (ticket.mode === "independent") {
    return <IndependentTicket ticket={ticket} tierVar={tierVar} play={play} profitColor={profitColor} />;
  }

  return (
    <div className="ticket" data-status={ticket.status}>
      {isWin ? (
        <span className="win-seal" aria-label="已中奖">中</span>
      ) : null}

      <div className="ticket-head">
        <span className="ticket-tier" style={{ color: tierVar }}>{ticket.tier}</span>
        <span className="ticket-play">{play}</span>
      </div>

      <div className="ticket-legs">
        {ticket.legs.map((leg, i) => {
          const lost = leg.hit === false;
          const hasTeams = Boolean(leg.home && leg.away);
          return (
            <div className={lost ? "ticket-leg lost" : "ticket-leg"} key={i}>
              {hasTeams ? (
                <>
                  <div className="leg-top">
                    <span className="leg-no">第{i + 1}场</span>
                    {leg.matchNo ? <span className="leg-code"> · {leg.matchNo}</span> : null}
                    {leg.category ? <span className="leg-cat"> · {leg.category}</span> : null}
                  </div>
                  <div className="leg-teams">
                    <span className="team">{leg.home}</span>
                    <span className="vs">Vs</span>
                    <span className="team">{leg.away}</span>
                  </div>
                  <div className="leg-bottom">
                    <Picks leg={leg} />
                    {leg.hit === true ? <span className="hit-y">✓</span> : null}
                    {lost ? <span className="hit-n">✗</span> : null}
                    {leg.hit == null ? <span className="hit-p">待结算</span> : null}
                  </div>
                </>
              ) : (
                <div className="leg-bottom">
                  <Picks leg={leg} />
                  {leg.hit === true ? <span className="hit-y">✓</span> : null}
                  {lost ? <span className="hit-n">✗</span> : null}
                  {leg.hit == null ? <span className="hit-p">待结算</span> : null}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="ticket-foot">
        <div className="ticket-foot-row">
          {isCombo ? (
            <span className="dim">{ticket.combos}注{multiple != null ? ` · ${multiple}倍` : ""}</span>
          ) : multiple != null ? (
            <span className="dim">{multiple}倍</span>
          ) : (
            <span />
          )}
          <span className="ticket-total">合计 {plainYuan(ticket.stake)}</span>
        </div>
        <div className="ticket-foot-row">
          <span className="foot-l">
            {isCombo ? (
              <span className="dim">命中 {hitMatches}/{ticket.legs.length} 场</span>
            ) : (
              <span className="odds-chip" title={`回报 ${plainYuan(ticket.payout)}`}>
                <span className="odds-x">×</span>
                {odds(ticket.combinedOdds)}
              </span>
            )}
            {isWin ? <span className="dim">回报 {plainYuan(ticket.payout)}</span> : null}
          </span>
          <span className="ticket-profit" style={{ color: profitColor }}>
            {ticket.status === "pending" ? "待结算" : yuan(ticket.profit)}
          </span>
        </div>
      </div>
    </div>
  );
}

// 单场固定·多注比分：一张票里每场买了多个比分、各注独立结算。按场分组，
// 每注一行（比分@赔率 + 命中标记），命中的注高亮，避免长串挤成一团。
function IndependentTicket({
  ticket,
  tierVar,
  play,
  profitColor,
}: {
  ticket: Ticket;
  tierVar: string;
  play: string;
  profitColor: string;
}) {
  const isWin = ticket.status === "win";
  const hitCount = ticket.legs.filter((l) => l.hit === true).length;
  // 按场分组（保序）
  const groups: { key: string; matchNo?: string; home?: string; away?: string; legs: TicketLeg[] }[] = [];
  for (const leg of ticket.legs) {
    const key = leg.matchNo || `${leg.home ?? ""}-${leg.away ?? ""}`;
    let g = groups.find((x) => x.key === key);
    if (!g) {
      g = { key, matchNo: leg.matchNo, home: leg.home, away: leg.away, legs: [] };
      groups.push(g);
    }
    g.legs.push(leg);
  }

  return (
    <div className="ticket" data-status={ticket.status}>
      {isWin ? (
        <span className="win-seal" aria-label="已中奖">中</span>
      ) : null}

      <div className="ticket-head">
        <span className="ticket-tier" style={{ color: tierVar }}>{ticket.tier}</span>
        <span className="ticket-play">{play}</span>
      </div>

      <div className="ticket-legs">
        {groups.map((g, gi) => (
          <div className="score-group" key={gi}>
            <div className="leg-top">
              <span className="leg-no">第{gi + 1}场</span>
              {g.matchNo ? <span className="leg-code"> · {g.matchNo}</span> : null}
              {g.home && g.away ? (
                <span className="score-grp-teams"> · {g.home} <span className="vs">Vs</span> {g.away}</span>
              ) : null}
            </div>
            <div className="score-rows">
              {g.legs.map((leg, i) => {
                const won = leg.hit === true;
                const lost = leg.hit === false;
                return (
                  <span className={"score-chip" + (won ? " won" : lost ? " lost" : "")} key={i}>
                    <span className="sc-pick">{leg.pick ?? leg.text}</span>
                    {leg.odds != null ? <span className="sc-odds">@{odds(leg.odds)}</span> : null}
                    {won ? <span className="hit-y">✓</span> : null}
                    {lost ? <span className="hit-n">✗</span> : null}
                    {leg.hit == null ? <span className="hit-p">待</span> : null}
                  </span>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="ticket-foot">
        <div className="ticket-foot-row">
          <span className="dim">{ticket.legs.length}注 · 命中 {hitCount}</span>
          <span className="ticket-total">合计 {plainYuan(ticket.stake)}</span>
        </div>
        <div className="ticket-foot-row">
          <span className="foot-l">
            {ticket.payout > 0 ? <span className="dim">回报 {plainYuan(ticket.payout)}</span> : <span />}
          </span>
          <span className="ticket-profit" style={{ color: profitColor }}>
            {ticket.status === "pending" ? "待结算" : yuan(ticket.profit)}
          </span>
        </div>
      </div>
    </div>
  );
}
