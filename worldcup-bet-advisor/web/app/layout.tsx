import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "世界杯 · 每日玩法报告",
  description: "多 agent 预测 × 实时倍率，每日报告与收益仪表盘。",
};

// Same theme bootstrap as the report: read localStorage["wc-theme"], set
// data-theme before paint. Keeps the dashboard and the embedded report in sync.
const themeScript = `(function(){try{var t=localStorage.getItem("wc-theme");if(!t){t=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";}document.documentElement.setAttribute("data-theme",t);if(localStorage.getItem("wc-nav")==="collapsed"){document.documentElement.classList.add("nav-collapsed");}}catch(e){document.documentElement.setAttribute("data-theme","light");}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#faf8f3" media="(prefers-color-scheme: light)" />
        <meta name="theme-color" content="#1f1f1e" media="(prefers-color-scheme: dark)" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&display=swap"
          rel="stylesheet"
        />
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <a href="#main" className="skip-link">
          跳到正文
        </a>
        {children}
      </body>
    </html>
  );
}
