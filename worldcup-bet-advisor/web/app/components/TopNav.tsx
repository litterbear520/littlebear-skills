"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

// Thin chrome around the report. Date switcher + a link to the profit
// dashboard + a theme toggle that drives the SAME data-theme / wc-theme the
// report uses, so toggling here also flips the embedded report.
export default function TopNav({
  reportDates,
  current,
  view,
}: {
  reportDates: string[];
  current: string;
  view: "report" | "profit";
}) {
  const router = useRouter();
  const [dark, setDark] = useState<boolean | null>(null);

  useEffect(() => {
    setDark(document.documentElement.getAttribute("data-theme") === "dark");
    const onStorage = (e: StorageEvent) => {
      if (e.key === "wc-theme") {
        const t = e.newValue === "dark";
        document.documentElement.setAttribute("data-theme", t ? "dark" : "light");
        setDark(t);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  function toggleTheme() {
    const next = document.documentElement.getAttribute("data-theme") !== "dark";
    document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
    try {
      localStorage.setItem("wc-theme", next ? "dark" : "light");
    } catch {}
    setDark(next);
  }

  return (
    <nav
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
        flexWrap: "wrap",
        padding: "12px 20px",
        borderBottom: "1px solid var(--line)",
        background: "var(--paper)",
      }}
    >
      <a href={reportDates[0] ? `/r/${reportDates[0]}` : "/"} className="serif" style={{ fontSize: 18 }}>
        世界杯 · 每日玩法
      </a>

      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <select
          aria-label="选择报告日期"
          value={view === "report" ? current : ""}
          onChange={(e) => e.target.value && router.push(`/r/${e.target.value}`)}
          className="btn"
        >
          {view === "profit" ? <option value="">选择报告…</option> : null}
          {reportDates.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>

        <a
          href={reportDates[0] ? `/r/${reportDates[0]}` : "/"}
          className="btn"
          style={view === "report" ? { borderColor: "var(--clay)", color: "var(--clay)" } : undefined}
        >
          报告
        </a>
        <a
          href="/profit"
          className="btn"
          style={view === "profit" ? { borderColor: "var(--clay)", color: "var(--clay)" } : undefined}
        >
          收益仪表盘
        </a>

        <button
          type="button"
          onClick={toggleTheme}
          className="btn"
          aria-label="切换深浅色"
          title="切换深浅色"
          style={{ width: 40, padding: "6px 0" }}
        >
          {dark == null ? "◐" : dark ? "☀" : "☾"}
        </button>
      </div>
    </nav>
  );
}
