import type { SiteIndex, DayData } from "@/lib/types";
import { yuan, plainYuan, profitVar, weekdayOf } from "@/lib/format";
import ProfitLine from "./ProfitLine";
import TicketCard from "./TicketCard";

export default function Dashboard({
  index,
  settledDays: settledDaysData,
}: {
  index: SiteIndex;
  settledDays: DayData[];
}) {
  const winRate =
    index.totalTickets > 0 ? Math.round((index.winTickets / index.totalTickets) * 100) : null;
  const roi =
    index.totalStake > 0 ? Math.round((index.cumulativeProfit / index.totalStake) * 100) : null;
  const settledDays = index.days.filter((d) => d.status === "settled");
  // 票区不逐日铺开：最近一天完整展示，往期收进一个折叠列表（点日期行展开该天票卡）
  const [latestDay, ...pastDays] = settledDaysData.filter((d) => (d.tickets ?? []).length > 0);

  return (
    <main className="wrap">
      <h1 className="serif" style={{ fontSize: 26, fontWeight: 500, margin: "28px 0 4px" }}>
        收益仪表盘
      </h1>
      <p className="dim" style={{ fontSize: 13, marginTop: 0 }}>
        基于复盘时记录的真实本金与赔率。模型分析 ≠ 投注建议，理性娱乐。
      </p>

      <div className="card" style={{ padding: 18, marginTop: 16 }}>
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
            <span className="dim">盈利率 </span>
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

      <div className="card" style={{ padding: "16px 18px 12px", marginTop: 14 }}>
        <div className="dim" style={{ fontSize: 13, marginBottom: 8 }}>累计收益曲线</div>
        <ProfitLine series={index.profitSeries} />
      </div>

      {latestDay ? (
        <section>
          <h2 className="section-title">
            我买的票
            <span className="dim" style={{ fontSize: 13, fontWeight: 400 }}>
              {latestDay.date} {weekdayOf(latestDay.date, latestDay.weekday)} · 当日{" "}
              <span style={{ color: profitVar(latestDay.dayProfit) }}>{yuan(latestDay.dayProfit)}</span>
            </span>
          </h2>
          <div className="ticket-grid">
            {(latestDay.tickets ?? []).map((t) => (
              <TicketCard key={t.id} ticket={t} />
            ))}
          </div>
        </section>
      ) : null}

      {pastDays.length > 0 ? (
        <section style={{ marginTop: 26 }}>
          <h2 className="section-title">往期 · 我买的票</h2>
          <div className="card" style={{ padding: "2px 16px" }}>
            {pastDays.map((day) => (
              <details className="past-day" key={day.date}>
                <summary>
                  <span className="dp-date">{day.date}</span>
                  <span className="dim">{weekdayOf(day.date, day.weekday)}</span>
                  <span className="dim" style={{ fontSize: 12 }}>
                    {(day.tickets ?? []).length} 张票
                  </span>
                  <span className="past-profit" style={{ color: profitVar(day.dayProfit) }}>
                    {yuan(day.dayProfit)}
                  </span>
                  <span className="past-chev" aria-hidden="true" />
                </summary>
                <div className="ticket-grid" style={{ padding: "4px 0 16px" }}>
                  {(day.tickets ?? []).map((t) => (
                    <TicketCard key={t.id} ticket={t} />
                  ))}
                </div>
              </details>
            ))}
          </div>
        </section>
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
