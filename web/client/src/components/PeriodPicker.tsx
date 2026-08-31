import { useStore } from "../store";

/**
 * Period picker that adapts to the data frequency:
 *  - monthly  -> Year + Month dropdowns
 *  - quarterly-> Year + Quarter
 *  - daily    -> Year + (a single period dropdown for the day)
 *  - yearly   -> Year only
 * Produces the canonical period string and stores it as the global as-of period.
 */
export default function PeriodPicker() {
  const { data, period, setPeriod } = useStore();
  const pinfo = data?.periods;
  if (!pinfo || !pinfo.items?.length) return null;

  const kind = pinfo.kind || "month";
  const items = pinfo.items || [];
  const cur = items.find((i) => i.period === period) || items[items.length - 1] || { year: 2025, period: "2025" };
  const years = pinfo.years || [2025];

  // Sub-periods available within the currently selected year.
  const subsForYear = items.filter((i) => i.year === cur.year && i.sub != null);

  const setYear = (y: number) => {
    const sameSub = items.find((i) => i.year === y && i.sub === cur.sub);
    const fallback = items.filter((i) => i.year === y).pop();
    setPeriod((sameSub || fallback || items[items.length - 1])?.period || String(y));
  };
  const setSub = (subPeriod: string) => setPeriod(subPeriod);

  return (
    <div className="freq-select" style={{ gap: 6 }}>
      <span>Kỳ:</span>
      {years.length > 1 || kind !== "year" ? (
        <select value={cur.year ?? ""} onChange={(e) => setYear(Number(e.target.value))} title="Năm">
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
      ) : null}
      {kind === "month" && subsForYear.length > 0 && (
        <select value={cur.period} onChange={(e) => setSub(e.target.value)} title="Tháng">
          {subsForYear.map((i) => <option key={i.period} value={i.period}>{i.sub_label || `Th${String(i.sub).padStart(2, "0")}`}</option>)}
        </select>
      )}
      {kind === "quarter" && subsForYear.length > 0 && (
        <select value={cur.period} onChange={(e) => setSub(e.target.value)} title="Quý">
          {subsForYear.map((i) => <option key={i.period} value={i.period}>Q{i.sub}</option>)}
        </select>
      )}
      {kind === "day" && (
        <select value={cur.period} onChange={(e) => setSub(e.target.value)} title="Ngày">
          {items.filter((i) => i.year === cur.year).map((i) => <option key={i.period} value={i.period}>{i.period.slice(5)}</option>)}
        </select>
      )}
    </div>
  );
}

/** Hook helper: filter a list of {period} rows to the selected as-of period. */
export function useAsOf() {
  const { period, data } = useStore();
  const latest = data?.periods?.latest || "";
  const sel = period || latest;
  return {
    period: sel,
    isLatest: sel === latest,
    /** Filter rows to the selected period; if none match, return flexible year match or all. */
    filter: <T extends { period?: string }>(rows: T[]): T[] => {
      if (!rows || !rows.length) return [];
      if (!sel) return rows;

      // 1. Try exact period match
      const exact = rows.filter((r) => r.period === sel);
      if (exact.length) return exact;

      // 2. Try year prefix match (e.g. sel="2023" vs r.period="2023-12-31" or "2023Q4")
      const yearStr = sel.slice(0, 4);
      const yearMatches = rows.filter((r) => r.period && String(r.period).startsWith(yearStr));
      if (yearMatches.length) return yearMatches;

      // 3. Fallback to rows matching latest or all
      const latestMatches = rows.filter((r) => r.period === latest || (latest && String(r.period).startsWith(latest.slice(0, 4))));
      return latestMatches.length ? latestMatches : rows;
    },
  };
}
