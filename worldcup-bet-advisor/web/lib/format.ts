// Pure display helpers shared across server components. The real profit math
// lives in the Python exporter; here we only format what it already computed.

export function yuan(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  return `${sign}¥${Math.abs(n).toFixed(Math.abs(n) % 1 === 0 ? 0 : 1)}`;
}

export function plainYuan(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return `¥${n.toFixed(n % 1 === 0 ? 0 : 1)}`;
}

// Bet-slip odds: keep the real value but drop trailing zeros so a leg reads
// "1.5" not "1.50", while a串关 combined like 1.845 stays exact (toFixed(3)
// avoids the float artifact where 1.845.toFixed(2) collapses to 1.84).
export function odds(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toFixed(3).replace(/\.?0+$/, "");
}

// A profit's semantic color, expressed as a CSS variable name.
export function profitVar(n: number | null | undefined): string {
  if (n == null || n === 0) return "var(--text-secondary)";
  return n > 0 ? "var(--success)" : "var(--danger)";
}

export function stars(confidence?: number): string {
  const c = Math.max(0, Math.min(5, Math.round(confidence ?? 0)));
  return "★★★★★".slice(0, c) + "☆☆☆☆☆".slice(0, 5 - c);
}

export function tierColorVar(tier: string): string {
  if (tier.includes("稳健")) return "var(--sage)";
  if (tier.includes("平衡")) return "var(--gold)";
  if (tier.includes("激进")) return "var(--clay)";
  return "var(--text-secondary)";
}

export function weekdayOf(date: string, given?: string): string {
  if (given) return given;
  const names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  const d = new Date(`${date}T00:00:00`);
  return Number.isNaN(d.getTime()) ? "" : names[d.getDay()];
}
