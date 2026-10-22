import "server-only";
import fs from "node:fs";
import path from "node:path";
import type { DayData, SiteIndex } from "./types";

const DATA_DIR = path.join(process.cwd(), "data");

const EMPTY_INDEX: SiteIndex = {
  days: [],
  reportDates: [],
  cumulativeProfit: 0,
  totalStake: 0,
  totalTickets: 0,
  winTickets: 0,
  profitSeries: [],
};

function readJson<T>(file: string, fallback: T): T {
  const full = path.join(DATA_DIR, file);
  if (!fs.existsSync(full)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(full, "utf8")) as T;
  } catch {
    return fallback;
  }
}

export function getIndex(): SiteIndex {
  return readJson<SiteIndex>("index.json", EMPTY_INDEX);
}

export function getReportDates(): string[] {
  return getIndex().reportDates;
}

export function getLatestReportDate(): string | null {
  const dates = getIndex().reportDates;
  return dates.length > 0 ? dates[0] : null;
}

export function getDay(date: string): DayData | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  return readJson<DayData | null>(`${date}.json`, null);
}
