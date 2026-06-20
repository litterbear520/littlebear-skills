import type { SiteIndex, DayData } from "@/lib/types";
import { yuan, plainYuan, profitVar, weekdayOf } from "@/lib/format";
import ProfitBars from "./ProfitBars";
import TicketCard from "./TicketCard";

export default function Dashboard({
  index,
  latestSettled,
}: {
  index: SiteIndex;
  latestSettled: DayData | null;
}) {
  const winRate =
    index.totalTickets > 0 ? Math.round((index.winTickets / index.totalTickets) * 100) : null;
  const roi =
    index.totalStake > 0 ? Math.round((index.cumulativeProfit / index.totalStake) * 100) : null;
  const settledDays = index.days.filter((d) => d.status === "settled");

  return (
    <main id="main" className="wrap">
      <h1 className="serif" style={{ fontSize: 26, fontWeight: 500, margin: "28px 0 4px" }}>
        收益仪表盘
      </h1>
      <p className="dim" style={{ fontSize: 13, marginTop: 0 }}>
        基于复盘时记录的真实本金与赔率。模型分析 ≠ 投注建议，理性娱乐。
      </p>

      <div
        className="hero-grid"
        style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1.5fr)", gap: 14, marginTop: 16 }}
      >
        <div className="card" style={{ padding: 18 }}>
          <div className="dim" style={{ fontSize: 13 }}>累计收益</div>
          <div className="serif" style={{ fontSize: 36, marginTop: 2, color: profitVar(index.cumulativeProfit) }}>
            {yuan(index.cumulativeProfit)}
          </div>
          <div style={{ display: "flex", gap: 18, marginTop: 12, fontSize: 13, flexWrap: "wrap" }}>
            <span>
              <span className="dim">总本金 </span>
              <span className="muted">{plainYuan(index.totalStake)}</span>
            </span>
            <span>
              <span className="dim">命中率 </span>
              <span className="muted">
                {winRate != null ? `${winRate}% (${index.winTickets}/${index.totalTickets})` : "—"}
              </span>
            </span>
            <span>
              <span className="dim">回报率 </span>
              <span style={{ color: profitVar(index.cumulativeProfit) }}>{roi != null ? `${roi}%` : "—"}</span>
            </span>
          </div>
        </div>

        <div className="card" style={{ padding: 18 }}>
          <div className="dim" style={{ fontSize: 13, marginBottom: 10 }}>近 14 日收益</div>
          <ProfitBars series={index.profitSeries} />
        </div>
      </div>

      {latestSettled && (latestSettled.tickets ?? []).length > 0 ? (
        <>
          <h2 className="section-title">
            最近一期 · 我买的票
            <span className="dim" style={{ fontSize: 13, fontWeight: 400 }}>
              {latestSettled.date} {weekdayOf(latestSettled.date, latestSettled.weekday)} · 当日{" "}
              <span style={{ color: profitVar(latestSettled.dayProfit) }}>{yuan(latestSettled.dayProfit)}</span>
            </span>
          </h2>
          <div className="grid-3">
            {(latestSettled.tickets ?? []).map((t) => (
              <TicketCard key={t.id} ticket={t} />
            ))}
          </div>
        </>
      ) : null}

      {settledDays.length > 0 ? (
        <>
          <h2 className="section-title">按日收益</h2>
          <div className="card" style={{ padding: "6px 16px" }}>
            {settledDays.map((d, i) => (
              <div
                key={d.date}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "10px 0",
                  borderTop: i === 0 ? "none" : "1px solid var(--line)",
                  fontSize: 14,
                }}
              >
                <span>
                  {d.hasReport ? (
                    <a href={`/r/${d.date}`} style={{ color: "var(--clay)" }}>
                      {d.date}
                    </a>
                  ) : (
                    <span className="muted">{d.date}</span>
                  )}{" "}
                  <span className="dim">{weekdayOf(d.date, d.weekday)}</span>
                </span>
                <span style={{ color: profitVar(d.dayProfit), fontWeight: 500 }}>{yuan(d.dayProfit)}</span>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </main>
  );
}
