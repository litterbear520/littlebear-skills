import { yuan } from "@/lib/format";

// Server-rendered SVG of the cumulative-profit (equity) curve — the running
// total starting from a 0 anchor, so it reads like a P&L chart: nice gridlines
// with ¥ axis labels, an emphasized break-even (0) line, a date range on the
// x-axis, and an open end-cap marker with the current total. No chart lib, no
// client JS. One settled day already draws a line (0 → that day's total).

// Pick a "nice" round tick step (1/2/5 × 10ⁿ) so axis labels read cleanly.
function niceStep(range: number, target = 4): number {
  if (range <= 0) return 1;
  const raw = range / target;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10;
  return step * mag;
}

function tickLabel(v: number): string {
  if (v === 0) return "0";
  return `${v > 0 ? "+" : "−"}¥${Math.abs(v).toLocaleString("en-US")}`;
}

export default function ProfitLine({
  series,
}: {
  series: { date: string; profit: number }[];
}) {
  if (!series || series.length === 0) {
    return (
      <div className="dim" style={{ fontSize: 13 }}>
        还没有已结算的收益，复盘后这里会出现累计收益曲线。
      </div>
    );
  }

  // cumulative curve, anchored at 0 before the first settled day
  const pts: { cum: number }[] = [{ cum: 0 }];
  let run = 0;
  for (const d of series) {
    run = Math.round((run + d.profit) * 100) / 100;
    pts.push({ cum: run });
  }

  const cums = pts.map((p) => p.cum);
  const dataMin = Math.min(0, ...cums);
  const dataMax = Math.max(0, ...cums);
  const step = niceStep(Math.max(dataMax - dataMin, 1));
  const niceMin = Math.floor(dataMin / step) * step;
  const niceMax = Math.ceil(dataMax / step) * step;
  const ticks: number[] = [];
  for (let v = niceMin; v <= niceMax + 1e-9; v += step) ticks.push(Math.round(v * 100) / 100);

  const W = 680;
  const H = 280;
  const L = 58;
  const R = 18;
  const T = 18;
  const B = 32;
  const plotW = W - L - R;
  const plotH = H - T - B;
  const n = pts.length;

  const xOf = (i: number) => (n === 1 ? L + plotW / 2 : L + (i / (n - 1)) * plotW);
  const yOf = (v: number) => T + ((niceMax - v) / (niceMax - niceMin || 1)) * plotH;

  const last = pts[n - 1];
  const lineColor = last.cum >= 0 ? "var(--success)" : "var(--danger)";
  const linePath = pts
    .map((p, i) => `${i ? "L" : "M"}${xOf(i).toFixed(1)} ${yOf(p.cum).toFixed(1)}`)
    .join(" ");

  // decorative vertical gridlines (evenly spaced, independent of point count)
  const cols = 6;
  const vGrid = Array.from({ length: cols + 1 }, (_, k) => L + (k / cols) * plotW);

  const endX = xOf(n - 1);
  const endY = yOf(last.cum);
  const labelY = Math.max(T + 11, endY - 9);

  const firstDate = series[0].date.slice(5);
  const lastDate = series[series.length - 1].date.slice(5);

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="累计收益曲线"
      style={{ display: "block", maxHeight: 260 }}
    >
      {vGrid.map((x, i) => (
        <line key={`v${i}`} x1={x} y1={T} x2={x} y2={H - B} stroke="var(--border)" strokeWidth={1} opacity={0.5} />
      ))}

      {ticks.map((t) => {
        const y = yOf(t);
        const zero = t === 0;
        return (
          <g key={`h${t}`}>
            <line
              x1={L}
              y1={y}
              x2={W - R}
              y2={y}
              stroke={zero ? "var(--border-strong)" : "var(--border)"}
              strokeWidth={zero ? 1.4 : 1}
            />
            <text x={L - 9} y={y + 3.6} textAnchor="end" fontSize={11.5} fill="var(--text-tertiary)">
              {tickLabel(t)}
            </text>
          </g>
        );
      })}

      <path d={linePath} fill="none" stroke={lineColor} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />

      <circle cx={endX} cy={endY} r={4.5} fill="var(--surface)" stroke={lineColor} strokeWidth={2.5} />
      <text x={endX - 9} y={labelY} textAnchor="end" fontSize={12.5} fontWeight={600} fill={lineColor}>
        {yuan(last.cum)}
      </text>

      <text x={L} y={H - 11} textAnchor="start" fontSize={11.5} fill="var(--text-tertiary)">
        {firstDate}
      </text>
      <text x={W - R} y={H - 11} textAnchor="end" fontSize={11.5} fill="var(--text-tertiary)">
        {lastDate}
      </text>
    </svg>
  );
}
