import { getIndex, getDay } from "@/lib/data";
import type { DayData } from "@/lib/types";
import AppShell from "../components/AppShell";
import Dashboard from "../components/Dashboard";

export const dynamic = "force-static";

export default function ProfitPage() {
  const index = getIndex();
  // 所有已结算的期（新→旧），各带自己的票——按期分组展示，往期不丢
  const settledDays = index.days
    .filter((d) => d.status === "settled")
    .map((d) => getDay(d.date))
    .filter((d): d is DayData => d != null);

  return (
    <AppShell reportDates={index.reportDates}>
      <Dashboard index={index} settledDays={settledDays} />
    </AppShell>
  );
}
