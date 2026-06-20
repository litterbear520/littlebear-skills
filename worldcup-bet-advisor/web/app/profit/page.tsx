import { getIndex, getDay } from "@/lib/data";
import TopNav from "../components/TopNav";
import Dashboard from "../components/Dashboard";

export const dynamic = "force-static";

export default function ProfitPage() {
  const index = getIndex();
  const settledDates = index.days.filter((d) => d.status === "settled").map((d) => d.date);
  const latestSettled = settledDates[0] ? getDay(settledDates[0]) : null;

  return (
    <div>
      <TopNav reportDates={index.reportDates} current="" view="profit" />
      <Dashboard index={index} latestSettled={latestSettled} />
    </div>
  );
}
