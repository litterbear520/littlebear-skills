import { getIndex, getLatestReportDate } from "@/lib/data";
import AppShell from "./components/AppShell";
import ReportFrame from "./components/ReportFrame";

export const dynamic = "force-static";

export default function Home() {
  const index = getIndex();
  const latest = getLatestReportDate();

  return (
    <AppShell reportDates={index.reportDates}>
      {latest ? (
        <ReportFrame date={latest} />
      ) : (
        <div className="wrap" style={{ paddingTop: 60 }}>
          <h1 className="serif" style={{ fontSize: 24, fontWeight: 500 }}>还没有报告</h1>
          <p className="muted" style={{ marginTop: 12 }}>
            跑一次 worldcup-bet-advisor 技能、发布后这里会出现当天的报告。
          </p>
        </div>
      )}
    </AppShell>
  );
}
