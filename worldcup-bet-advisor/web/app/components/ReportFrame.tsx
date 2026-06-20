"use client";

// Embeds the original report.html untouched (its own styles/theme/TOC/tabs/PDF).
// On load we copy the current data-theme into the iframe so the report matches
// the rest of the site, and the top-right toggle also reaches in to flip it.
export default function ReportFrame({ date }: { date: string }) {
  return (
    <iframe
      className="report-frame"
      src={`/reports/${date}.html`}
      title={`${date} 玩法报告`}
      onLoad={(e) => {
        try {
          const doc = e.currentTarget.contentDocument;
          const t = document.documentElement.getAttribute("data-theme") || "light";
          doc?.documentElement.setAttribute("data-theme", t);
        } catch {}
      }}
      style={{ display: "block", width: "100%", height: "100%", border: "none", background: "var(--paper)" }}
    />
  );
}
