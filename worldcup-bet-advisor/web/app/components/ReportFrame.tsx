"use client";

import { useEffect, useRef } from "react";

// Sidebar TOC labels: a match reads like "01:00 荷兰 / 瑞典" in the report — drop
// the kickoff time and show "荷兰 vs 瑞典". Section headers (今日赛程 / 三档方案 …)
// carry neither a leading time nor a slash, so they pass through unchanged.
function tidyTocLabel(raw: string): string {
  return raw
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\d{1,2}:\d{2}\s*/, "")
    .replace(/\s*\/\s*/g, " vs ")
    .trim();
}

// Embeds the original report.html. After it loads we:
//  1. match the current theme,
//  2. collapse the report's OWN built-in TOC (its native toc-collapsed mode →
//     content goes full-width) and hide its reopen button → SINGLE sidebar,
//  3. lift the report's section links into the outer sidebar via a window event.
//
// Driven from a ref + effect (not just onLoad) because a fast local iframe can
// finish loading before React attaches an onLoad handler.
export default function ReportFrame({ date }: { date: string }) {
  const ref = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const frame = ref.current;
    if (!frame) return;

    const apply = () => {
      try {
        const doc = frame.contentDocument;
        if (!doc || !doc.documentElement) return;
        const t = document.documentElement.getAttribute("data-theme") || "light";
        doc.documentElement.setAttribute("data-theme", t);

        doc.documentElement.classList.add("toc-collapsed");
        try {
          doc.defaultView?.localStorage.setItem("wc-toc", "collapsed");
        } catch {}
        if (!doc.getElementById("wc-onesidebar")) {
          const s = doc.createElement("style");
          s.id = "wc-onesidebar";
          s.textContent = "#tocToggle,.toc-toggle,#tocScrim{display:none!important}";
          doc.head.appendChild(s);
        }

        const items = Array.from(doc.querySelectorAll("#toc a[href^='#']"))
          .map((a) => ({
            label: tidyTocLabel(a.textContent || ""),
            href: a.getAttribute("href") || "",
          }))
          .filter((i) => i.label && i.href);
        if (items.length) {
          window.dispatchEvent(new CustomEvent("report-toc", { detail: items }));
        }
      } catch {}
    };

    frame.addEventListener("load", apply);
    try {
      if (frame.contentDocument?.readyState === "complete") apply();
    } catch {}
    const t1 = setTimeout(apply, 120);
    const t2 = setTimeout(apply, 400);

    return () => {
      frame.removeEventListener("load", apply);
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [date]);

  return (
    <iframe
      ref={ref}
      className="report-frame"
      src={`/reports/${date}.html`}
      title={`${date} 玩法报告`}
      style={{ display: "block", width: "100%", height: "100%", border: "none", background: "var(--paper)" }}
    />
  );
}
