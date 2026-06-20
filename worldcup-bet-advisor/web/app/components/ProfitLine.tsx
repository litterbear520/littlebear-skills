import { plainYuan } from "@/lib/format";

// Server-rendered SVG line chart of daily profit. No chart library, no client
// JS — just math + an <svg>. A dashed zero line is the break-even axis; the
// trace weaves above it (profit, teal) and below it (loss, red), with a dot per
// settled day. One settled day renders as a single marker; the line appears as
// soon as there are two.
export default function ProfitLine({
  series,
}: {
  series: { date: string; profit: number }[];
}) {
  const data = series.slice(-14);
  if (data.length === 0) {
    return (
      <div className="dim" style={{ fontSize: 13 }}>
        还没有已结算的收益，复盘后这里会出现每日收益曲线。
      </div>
    );
  }

  const maxAbs = Math.max(1, ...data.map((d) => Math.abs(d.profit)));
  const padX = 16;
  const stepX = 48;
  const baseline = 56; // y of the zero / break-even line
  const amp = 42; // px the trace may travel each direction
  const W = padX * 2 + Math.max(1, data.length - 1) * stepX;
  const H = 124;
  const dateY = 108;
  const showValues = data.length <= 8; // avoid label crowding once the run grows

  const xOf = (i: number) => padX + i * stepX;
  const yOf = (p: number) => baseline - (p / maxAbs) * amp;

  const pts = data.map((d, i) => ({ x: xOf(i), y: yOf(d.profit), d }));
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="每日收益折线图"
      style={{ display: "block", maxHeight: 165 }}
    >
      {/* break-even axis */}
      <line
        x1={0}
        y1={baseline}
        x2={W}
        y2={baseline}
        stroke="var(--border-strong)"
        strokeWidth={1}
        strokeDasharray="3 4"
      />
      <text x={2} y={baseline - 4} fontSize={9} fill="var(--text-tertiary)">
        0
      </text>

      {pts.length > 1 ? (
        <path
          d={line}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : null}

      {pts.map((p) => {
        const color =
          p.d.profit > 0 ? "var(--success)" : p.d.profit < 0 ? "var(--danger)" : "var(--text-tertiary)";
        const above = p.d.profit >= 0;
        return (
          <g key={p.d.date}>
            <circle cx={p.x} cy={p.y} r={3.6} fill="var(--surface)" stroke={color} strokeWidth={2}>
              <title>{`${p.d.date} · ${plainYuan(p.d.profit)}`}</title>
            </circle>
            {showValues ? (
              <text
                x={p.x}
                y={above ? p.y - 9 : p.y + 16}
                textAnchor="middle"
                fontSize={10.5}
                fontWeight={600}
                fill={color}
              >
                {plainYuan(p.d.profit)}
              </text>
            ) : null}
            <text x={p.x} y={dateY} textAnchor="middle" fontSize={11} fill="var(--text-tertiary)">
              {p.d.date.slice(8)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
