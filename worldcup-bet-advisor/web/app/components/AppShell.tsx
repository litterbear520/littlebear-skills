"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
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

function ChartIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <path d="M3 3v18h18" />
      <path d="M7 14l4-4 3 3 5-6" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <rect x="3" y="4.5" width="18" height="16" rx="2" />
      <line x1="3" y1="9.5" x2="21" y2="9.5" />
      <line x1="8" y1="2.5" x2="8" y2="6" />
      <line x1="16" y1="2.5" x2="16" y2="6" />
    </svg>
  );
}

// 报告日期选择器：navitem 质感的触发按钮 + 卡片浮层菜单，替代原生 select
// （原生下拉的选项列表无法主题化，暗色下尤其突兀）。当前项带陶土指示条，
// 最新一期挂「最新」徽章；点外部 / Esc 关闭，日期多了菜单内部滚动。
function ReportDatePicker({
  dates,
  current,
  onPick,
}: {
  dates: string[];
  current: string; // 当前查看的报告日期；仪表盘页传 ""（按钮显示最新但不点亮）
  onPick: (d: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const label = current || dates[0];
  return (
    <div className="dp" ref={ref}>
      <button
        type="button"
        className={current ? "dp-btn active" : "dp-btn"}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="选择报告日期"
      >
        <span className="navicon">
          <CalendarIcon />
        </span>
        <span className="dp-date">{label}</span>
        <span className="dp-wd">{weekday(label)}</span>
        <span className={open ? "dp-chev up" : "dp-chev"} aria-hidden="true" />
      </button>
      {open ? (
        <div className="dp-menu" role="listbox" aria-label="报告日期">
          {dates.map((d, i) => (
            <button
              key={d}
              type="button"
              role="option"
              aria-selected={d === current}
              className={d === current ? "dp-item on" : "dp-item"}
              onClick={() => {
                setOpen(false);
                onPick(d);
              }}
            >
              <span className="dp-date">{d}</span>
              {i === 0 ? <span className="dp-new">最新</span> : null}
              <span className="dp-wd">{weekday(d)}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
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
  const router = useRouter();
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

  const isMobile = () =>
    typeof window !== "undefined" && window.matchMedia("(max-width: 720px)").matches;

  // collapse from inside the sidebar (mobile: close the drawer; desktop: slide the rail away)
  function hideSidebar() {
    if (isMobile()) {
      setOpen(false);
      return;
    }
    document.documentElement.classList.add("nav-collapsed");
    try {
      localStorage.setItem("wc-nav", "collapsed");
    } catch {}
  }

  // expand from the topbar (mobile: open the drawer; desktop: bring the rail back)
  function showSidebar() {
    if (isMobile()) {
      setOpen(true);
      return;
    }
    document.documentElement.classList.remove("nav-collapsed");
    try {
      localStorage.setItem("wc-nav", "open");
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
        <div className="brand-row">
          <Link href="/" className="brand serif">
            世界杯<span className="brand-dot">·</span>每日玩法
          </Link>
          <button
            type="button"
            className="iconbtn nav-collapse"
            onClick={hideSidebar}
            aria-label="收起侧栏"
            title="收起侧栏"
          >
            <PanelIcon />
          </button>
        </div>

        <Link href="/profit" className={onProfit ? "navitem active" : "navitem"}>
          <span className="navicon">
            <ChartIcon />
          </span>
          仪表盘
        </Link>

        <div className="navlabel">报告</div>
        {reportDates.length === 0 ? (
          <div className="dim" style={{ fontSize: 13, padding: "7px 12px" }}>暂无报告</div>
        ) : (
          // 报告不逐日叠列：一个日期选择器，默认当前（最新=今天），可跳任意历史
          <ReportDatePicker
            dates={reportDates}
            current={!onProfit ? currentDate : ""}
            onPick={(d) => router.push(`/r/${d}`)}
          />
        )}

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
            className="iconbtn nav-expand"
            onClick={showSidebar}
            aria-label="展开侧栏"
            title="展开侧栏"
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
