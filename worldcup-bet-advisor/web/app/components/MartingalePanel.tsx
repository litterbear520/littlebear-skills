import type { Martingale } from "@/lib/types";
import { yuan, plainYuan, odds } from "@/lib/format";

// 比分叠层（翻倍 / 马丁格尔）面板：进行中那一轮的「叠到第几层 · 累计已亏 · 下一层要叠多少 ·
// 命中可赚」一目了然，下面列往期已命中收官的轮。数据全来自 index.json.martingale。
export default function MartingalePanel({ m }: { m: Martingale }) {
  const cur = m.current;
  const roundUnit = m.baseUnit * m.scoresPerRound; // 第1层两注合计

  return (
    <section style={{ marginTop: 26 }}>
      <h2 className="section-title">
        比分叠层 · 翻倍追分
        <span className="dim" style={{ fontSize: 13, fontWeight: 400 }}>
          每轮买 {m.scoresPerRound} 个比分、每注翻倍，中一个收官
        </span>
      </h2>

      {cur ? (
        <div className="card" style={{ padding: 18 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
            <span
              className="pill"
              style={{ background: "var(--accent-soft)", color: "var(--clay-d)", fontWeight: 600 }}
            >
              进行中
            </span>
            <span className="serif" style={{ fontSize: 20 }}>
              第 {cur.layer} 层 · {cur.multiple}×
            </span>
            <span className="dim" style={{ fontSize: 13 }}>
              {plainYuan(m.baseUnit * cur.multiple)}/比分 ×{m.scoresPerRound}
            </span>
          </div>

          <div className="grid-3">
            <Tile label="累计已亏" value={yuan(-cur.cumLoss)} valueColor="var(--danger)" />
            <Tile
              label="下一层要叠"
              value={plainYuan(cur.nextTotal)}
              sub={`${cur.nextMultiple}× · ${plainYuan(cur.nextPerScore)}/比分 ×${m.scoresPerRound}`}
              valueColor="var(--clay)"
            />
            <Tile
              label={`命中可赚 (按@${odds(m.assumedOdds)})`}
              value={yuan(cur.nextNetIfHit)}
              valueColor="var(--success)"
            />
          </div>

          <p className="dim" style={{ fontSize: 12.5, marginTop: 14, marginBottom: 0, lineHeight: 1.65 }}>
            翻倍法（赌徒定律 / 马丁格尔）：比分赔率 &gt; 4，命中即回本并净赚，拖得越久赚得越多。但注码每层翻倍（
            {roundUnit}→{roundUnit * 2}→{roundUnit * 4}→{roundUnit * 8}…），连黑会指数膨胀——建议设个封顶层数、量力而行。
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 18 }}>
          <span className="dim">
            当前没有进行中的叠层——上一轮已命中收官，下次从第 1 层（{plainYuan(m.baseUnit)}/比分）重开。
          </span>
        </div>
      )}

      {m.history.length > 0 ? (
        <div className="card" style={{ padding: "6px 16px", marginTop: 12 }}>
          <div className="dim" style={{ fontSize: 12, padding: "8px 0 4px" }}>往期叠层 · 命中收官</div>
          {m.history.map((c, i) => (
            <div
              key={`${c.wonDate}-${i}`}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 10,
                padding: "10px 0",
                borderTop: "1px solid var(--line)",
                fontSize: 14,
                flexWrap: "wrap",
              }}
            >
              <span>
                <span style={{ color: "var(--clay)" }}>{c.wonDate}</span>{" "}
                <span className="dim">第 {c.layers} 层命中</span>
              </span>
              <span className="muted" style={{ fontSize: 13 }}>
                {c.hitPick ?? "—"}
                {c.hitOdds != null ? <span className="dim"> @{odds(c.hitOdds)}</span> : null}
              </span>
              <span>
                <span className="dim" style={{ fontSize: 12 }}>
                  回 {plainYuan(c.payout)} · 投 {plainYuan(c.cost)} ·{" "}
                </span>
                <span style={{ color: "var(--success)", fontWeight: 600 }}>整轮 {yuan(c.net)}</span>
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function Tile({
  label,
  value,
  sub,
  valueColor,
}: {
  label: string;
  value: string;
  sub?: string;
  valueColor?: string;
}) {
  return (
    <div
      style={{
        background: "var(--surface-2)",
        border: "1px solid var(--line)",
        borderRadius: 12,
        padding: "12px 14px",
      }}
    >
      <div className="dim" style={{ fontSize: 12 }}>{label}</div>
      <div className="serif" style={{ fontSize: 22, marginTop: 3, color: valueColor ?? "var(--ink)" }}>
        {value}
      </div>
      {sub ? <div className="dim" style={{ fontSize: 11.5, marginTop: 2 }}>{sub}</div> : null}
    </div>
  );
}
