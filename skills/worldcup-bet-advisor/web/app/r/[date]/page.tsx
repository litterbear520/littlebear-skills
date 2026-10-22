import { notFound } from "next/navigation";
import { getIndex, getReportDates } from "@/lib/data";
import AppShell from "../../components/AppShell";
import ReportFrame from "../../components/ReportFrame";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return getReportDates().map((date) => ({ date }));
}

export default async function ReportPage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  const index = getIndex();
  if (!index.reportDates.includes(date)) notFound();

  return (
    <AppShell reportDates={index.reportDates}>
      <ReportFrame date={date} />
    </AppShell>
  );
}
