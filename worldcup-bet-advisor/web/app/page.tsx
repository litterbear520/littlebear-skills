import { getIndex, getLatestReportDate } from "@/lib/data";
import TopNav from "./components/TopNav";
import ReportFrame from "./components/ReportFrame";

export const dynamic = "force-static";

export default function Home() {
  const index = getIndex();
  const latest = getLatestReportDate();

  if (!latest) {
    return (
      <main id="main" className="wrap" style={{ paddingTop: 80 }}>
        <h1 className="serif" style={{ fontSize: 26, fontWeight: 500 }}>
          世界杯 · 每日玩法报告
        </h1>
        <p className="muted" style={{ marginTop: 12 }}>
          还没有报告。跑一次 worldcup-bet-advisor 技能、发布后这里会出现当天的报告。
        </p>
      </main>
    );
  }

  return (
    <div id="main" style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <TopNav reportDates={index.reportDates} current={latest} view="report" />
      <ReportFrame date={latest} />
    </div>
  );
}
