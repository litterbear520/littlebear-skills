// Embeds the original report.html untouched. It is fully self-contained (its
// own styles, theme, TOC, tabs, PDF export), so an iframe preserves it exactly
// while the surrounding nav handles date-switching and the dashboard link.
export default function ReportFrame({ date }: { date: string }) {
  return (
    <iframe
      src={`/reports/${date}.html`}
      title={`${date} 玩法报告`}
      style={{ flex: 1, width: "100%", border: "none", background: "var(--paper)" }}
    />
  );
}
