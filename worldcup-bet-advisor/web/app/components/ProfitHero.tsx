import type { DayData, SiteIndex } from "@/lib/types";
import { yuan, plainYuan, profitVar } from "@/lib/format";
import ProfitLine from "./ProfitLine";

export default function ProfitHero({
  day,
  index,
}: {
  day: DayData;
  index: SiteIndex;
}) {
  const settled = day.status === "settled";
  const hitCount = (day.tickets ?? []).filter((t) => t.status === "win").length;
  const ticketCount = (day.tickets ?? []).length;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1.4fr)",
        gap: 14,
        marginTop: 18,
      }}
      className="hero-grid"
    >
      <div className="card" style={{ padding: 18 }}>
        <div className="dim" style={{ fontSize: 13 }}>今日收益</div>
        <div
          className="serif"
          style={{ fontSize: 34, marginTop: 2, color: settled ? profitVar(day.dayProfit) : "var(--text-tertiary)" }}
        >
          {settled ? yuan(day.dayProfit) : "待结算"}
        </div>
        <div style={{ display: "flex", gap: 18, marginTop: 12, fontSize: 13, flexWrap: "wrap" }}>
          <span>
            <span className="dim">本金 </span>
            <span className="muted">{day.dayStake != null ? plainYuan(day.dayStake) : "—"}</span>
          </span>
          <span>
            <span className="dim">命中 </span>
            <span className="muted">{ticketCount > 0 ? `${hitCount} / ${ticketCount} 注` : "—"}</span>
          </span>
          <span>
            <span className="dim">累计 </span>
            <span style={{ color: profitVar(index.cumulativeProfit) }}>{yuan(index.cumulativeProfit)}</span>
          </span>
        </div>
      </div>

      <div className="card" style={{ padding: 18 }}>
        <div className="dim" style={{ fontSize: 13, marginBottom: 10 }}>近 14 日收益曲线</div>
        <ProfitLine series={index.profitSeries} />
      </div>
    </div>
  );
}
