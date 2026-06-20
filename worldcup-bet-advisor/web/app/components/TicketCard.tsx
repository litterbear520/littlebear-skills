import type { Ticket } from "@/lib/types";
import { yuan, plainYuan, tierColorVar } from "@/lib/format";

const STATUS = {
  win: { label: "已中", color: "var(--success)", border: "var(--success)" },
  loss: { label: "未中", color: "var(--danger)", border: "var(--border-strong)" },
  pending: { label: "待结算", color: "var(--text-tertiary)", border: "var(--border-strong)" },
} as const;

export default function TicketCard({ ticket }: { ticket: Ticket }) {
  const s = STATUS[ticket.status];
  const tierVar = tierColorVar(ticket.tier);

  const isWin = ticket.status === "win";

  return (
    <div
      className="card"
      style={{
        position: "relative",
        background: "var(--bg)",
        borderColor: s.border,
        padding: 14,
        opacity: ticket.status === "loss" ? 0.92 : 1,
      }}
    >
      {isWin ? (
        <span className="win-seal" aria-label="已中奖">中</span>
      ) : null}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span
          className="pill"
          style={{ background: "color-mix(in srgb, var(--surface) 70%, transparent)", color: tierVar, border: `1px solid ${tierVar}` }}
        >
          {ticket.tier} · {ticket.type}
        </span>
        {!isWin ? <span style={{ fontSize: 12, color: s.color }}>{s.label}</span> : null}
      </div>

      <ul style={{ listStyle: "none", padding: 0, margin: "10px 0 0", fontSize: 14, lineHeight: 1.6 }}>
        {ticket.legs.map((leg, i) => {
          const lost = leg.hit === false;
          return (
            <li key={i} style={{ color: lost ? "var(--text-tertiary)" : "var(--text)" }}>
              {lost ? <s>{leg.text}</s> : leg.text}
              {leg.odds != null ? <span className="dim" style={{ fontSize: 12 }}> · {leg.odds}</span> : null}
              {leg.hit === true ? <span style={{ color: "var(--success)", fontSize: 12 }}> ✓</span> : null}
              {lost ? <span style={{ color: "var(--danger)", fontSize: 12 }}> ✗</span> : null}
            </li>
          );
        })}
      </ul>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 13,
          marginTop: 12,
          paddingTop: 10,
          borderTop: "1px solid var(--border)",
        }}
      >
        <span className="dim">
          {plainYuan(ticket.stake)} × {ticket.combinedOdds}
        </span>
        <span style={{ color: ticket.status === "win" ? "var(--success)" : ticket.status === "loss" ? "var(--danger)" : "var(--text-tertiary)", fontWeight: 500 }}>
          {ticket.status === "pending" ? "待结算" : yuan(ticket.profit)}
        </span>
      </div>
    </div>
  );
}
