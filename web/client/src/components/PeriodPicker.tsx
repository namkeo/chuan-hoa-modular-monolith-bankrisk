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

      // 2. Map quarterly/monthly equivalences
      let equiv = sel;
      if (sel.includes("Q")) {
        const [y, q] = sel.split("Q");
        const m = q === "4" ? "12" : q === "3" ? "09" : q === "2" ? "06" : "03";
        equiv = `${y}-${m}`;
      } else if (sel.match(/^\d{4}-\d{2}$/)) {
        const [y, m] = sel.split("-");
        const q = m === "12" ? "4" : m === "09" || m === "08" || m === "07" ? "3" : m === "06" || m === "05" || m === "04" ? "2" : "1";
        equiv = `${y}Q${q}`;
      }
      const matchEquiv = rows.filter((r) => r.period === equiv);
      if (matchEquiv.length) return matchEquiv;

      // 3. Try year prefix match -> pick the latest sub-period in that year
      const yearStr = sel.slice(0, 4);
      const yearMatches = rows.filter((r) => r.period && String(r.period).startsWith(yearStr));
      if (yearMatches.length) {
        const maxP = yearMatches.reduce((max, r) => ((r.period || "") > max ? (r.period || "") : max), "");
        return yearMatches.filter((r) => r.period === maxP);
      }

      // 4. Fallback to latest available period in rows
      const allP = rows.map((r) => r.period || "").filter(Boolean);
      const maxP = allP.reduce((max, p) => (p > max ? p : max), "");
      return rows.filter((r) => r.period === maxP);
    },
  };
}
