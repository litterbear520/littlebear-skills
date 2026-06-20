import { plainYuan } from "@/lib/format";

// Server-rendered SVG bar chart of daily profit. No chart library, no client
// JS — just math + an <svg>. Positive bars rise above the zero line (teal),
// losses drop below (red).
export default function ProfitBars({
  series,
}: {
  series: { date: string; profit: number }[];
}) {
  const data = series.slice(-14);
  if (data.length === 0) {
    return (
      <div className="dim" style={{ fontSize: 13 }}>
        还没有已结算的收益，复盘后这里会出现每日收益柱状图。
      </div>
    );
  }

  const maxAbs = Math.max(1, ...data.map((d) => Math.abs(d.profit)));
  const step = 34;
  const barW = 20;
  const W = data.length * step;
  const baseline = 56;
  const amp = 42; // max bar length each direction
  const labelY = 108;

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} 118`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="每日收益柱状图"
      style={{ display: "block", maxHeight: 150 }}
    >
      <line x1={0} y1={baseline} x2={W} y2={baseline} stroke="var(--border)" strokeWidth={1} />
      {data.map((d, i) => {
        const x = i * step + (step - barW) / 2;
        const h = Math.round((Math.abs(d.profit) / maxAbs) * amp);
        const up = d.profit >= 0;
        const y = up ? baseline - h : baseline;
        const color = d.profit > 0 ? "var(--success)" : d.profit < 0 ? "var(--danger)" : "var(--text-tertiary)";
        const day = d.date.slice(8); // DD
        return (
          <g key={d.date}>
            <rect
              x={x}
              y={y}
              width={barW}
              height={Math.max(2, h)}
              rx={3}
              fill={color}
              opacity={d.profit === 0 ? 0.5 : 0.9}
            >
              <title>{`${d.date} · ${plainYuan(d.profit)}`}</title>
            </rect>
            <text
              x={x + barW / 2}
              y={labelY}
              textAnchor="middle"
              fontSize={11}
              fill="var(--text-tertiary)"
            >
              {day}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
