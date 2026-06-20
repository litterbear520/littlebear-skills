"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";

const GITHUB_URL = "https://github.com/litterbear520/littlebear-skills";
const WD = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

function weekday(d: string): string {
  const x = new Date(`${d}T00:00:00`);
  return Number.isNaN(x.getTime()) ? "" : WD[x.getDay()];
}

// One consistent line-icon set (1.7px stroke, currentColor) so the top-right
// controls read as a family rather than a grab-bag of glyphs.
const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

function PanelIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="2.5" />
      <line x1="9.5" y1="4" x2="9.5" y2="20" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4l1.4-1.4M18 6l1.4-1.4" />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.9a3.4 3.4 0 0 0-.9-2.6c3-.3 6.2-1.5 6.2-6.7A5.2 5.2 0 0 0 20 4.8a4.9 4.9 0 0 0-.1-3.6s-1.1-.3-3.6 1.4a12.3 12.3 0 0 0-6.6 0C7.2.9 6.1 1.2 6.1 1.2A4.9 4.9 0 0 0 6 4.8 5.2 5.2 0 0 0 4.7 8.4c0 5.2 3.2 6.4 6.2 6.7a3.4 3.4 0 0 0-.9 2.6V22" />
    </svg>
  );
}

export default function AppShell({
  reportDates,
  children,
}: {
  reportDates: string[];
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState<boolean | null>(null);
  const [toc, setToc] = useState<{ label: string; href: string }[]>([]);

  useEffect(() => {
    setDark(document.documentElement.getAttribute("data-theme") === "dark");
  }, []);

  // close drawer + reset the report's lifted TOC when the route changes
  useEffect(() => {
    setOpen(false);
    setToc([]);
  }, [pathname]);

  useEffect(() => {
    const onToc = (e: Event) => setToc(((e as CustomEvent).detail as typeof toc) || []);
    window.addEventListener("report-toc", onToc as EventListener);
    return () => window.removeEventListener("report-toc", onToc as EventListener);
  }, []);

  const onProfit = pathname === "/profit";
  const currentDate =
    pathname === "/"
      ? reportDates[0]
      : pathname.startsWith("/r/")
        ? decodeURIComponent(pathname.slice(3))
        : "";

  function toggleTheme() {
    const next = document.documentElement.getAttribute("data-theme") !== "dark";
    const val = next ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", val);
    try {
      localStorage.setItem("wc-theme", val);
    } catch {}
    const f = document.querySelector("iframe.report-frame") as HTMLIFrameElement | null;
    try {
      f?.contentDocument?.documentElement.setAttribute("data-theme", val);
    } catch {}
    setDark(next);
  }

  // one button: on mobile it opens the drawer, on desktop it collapses the rail
  function toggleNav() {
    if (typeof window !== "undefined" && window.matchMedia("(max-width: 720px)").matches) {
      setOpen((o) => !o);
      return;
    }
    const next = !document.documentElement.classList.contains("nav-collapsed");
    document.documentElement.classList.toggle("nav-collapsed", next);
    try {
      localStorage.setItem("wc-nav", next ? "collapsed" : "open");
    } catch {}
  }

  function jumpTo(href: string) {
    const f = document.querySelector("iframe.report-frame") as HTMLIFrameElement | null;
    const el = f?.contentDocument?.querySelector(href);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
    setOpen(false);
  }

  return (
    <div className="shell">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <Link href="/" className="brand serif">
          世界杯<span className="brand-dot">·</span>每日玩法
        </Link>

        <Link href="/profit" className={onProfit ? "navitem active" : "navitem"}>
          收益仪表盘
        </Link>

        <div className="navlabel">报告</div>
        <nav>
          {reportDates.length === 0 ? (
            <div className="dim" style={{ fontSize: 13, padding: "7px 12px" }}>暂无报告</div>
          ) : (
            reportDates.map((d) => (
              <Link
                key={d}
                href={`/r/${d}`}
                className={d === currentDate && !onProfit ? "navitem active" : "navitem"}
              >
                <span className="date-num">{d}</span>
                <span className="date-wd">{weekday(d)}</span>
              </Link>
            ))
          )}
        </nav>

        {!onProfit && toc.length > 0 ? (
          <>
            <div className="navlabel">本页目录</div>
            <nav>
              {toc.map((it, i) => (
                <button
                  key={`${it.href}-${i}`}
                  type="button"
                  className="navitem tocitem"
                  onClick={() => jumpTo(it.href)}
                  title={it.label}
                >
                  {it.label}
                </button>
              ))}
            </nav>
          </>
        ) : null}
      </aside>

      {open ? <div className="scrim" onClick={() => setOpen(false)} aria-hidden="true" /> : null}

      <div className="main">
        <div className="topbar">
          <button
            type="button"
            className="iconbtn"
            onClick={toggleNav}
            aria-label="收起 / 展开侧栏"
            title="收起 / 展开侧栏"
          >
            <PanelIcon />
          </button>
          <div style={{ flex: 1 }} />
          <a
            className="iconbtn"
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            aria-label="GitHub 仓库"
            title="GitHub 仓库"
          >
            <GithubIcon />
          </a>
          <button
            type="button"
            className="iconbtn"
            onClick={toggleTheme}
            aria-label="切换深浅色"
            title="切换深浅色"
          >
            {dark ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>
        <div id="main" className="content">
          {children}
        </div>
      </div>
    </div>
  );
}
