import { FreqData } from "../api";

export type MetricPoint = { bank_id: string; value: number };

/**
 * Giá trị của chỉ tiêu tại ĐÚNG kỳ `period`, cho từng đơn vị (bỏ đơn vị không có số kỳ đó).
 *
 * Khớp giá trị theo kỳ đang chọn, KHÔNG lùi về quá khứ lấy số non-null gần nhất: một
 * đơn vị ngừng phát sinh chỉ tiêu từ lâu sẽ bị lôi số cũ ra xếp cùng số hiện hành,
 * rồi tô đỏ "vượt trần" như thể đang vi phạm (vd LDR 173,92% của CTTC HAFIC là số
 * của T11/2023 — trong khi đơn vị này không còn nhận tiền gửi). Không có số ở kỳ
 * đang xem thì KHÔNG đánh giá; xem thêm notEvaluatedAtPeriod().
 */
function getTargetPeriods(period: string): string[] {
  if (!period) return [];
  const targets = [period];
  if (period.match(/^\d{4}-\d{2}$/)) {
    const [y, m] = period.split("-");
    const q = m === "12" ? "4" : m === "09" || m === "08" || m === "07" ? "3" : m === "06" || m === "05" || m === "04" ? "2" : "1";
    targets.push(`${y}Q${q}`, y);
  } else if (period.includes("Q")) {
    const [y, q] = period.split("Q");
    const m = q === "4" ? "12" : q === "3" ? "09" : q === "2" ? "06" : "03";
    targets.push(`${y}-${m}`, y);
  } else if (period.match(/^\d{4}$/)) {
    targets.push(`${period}-12`, `${period}Q4`);
  }
  return targets;
}

export function atPeriodByMetric(data: FreqData, metric: string, period: string): MetricPoint[] {
  const out: MetricPoint[] = [];
  const sd = data.series?.data || {};
  const targetPeriods = getTargetPeriods(period);
  const yearStr = period ? period.slice(0, 4) : "";

  for (const bank of Object.keys(sd)) {
    const periods: string[] = sd[bank].periods || [];
    if (!periods.length) continue;

    const metricArr = sd[bank][metric] || [];
    let idx = -1;

    // 1. Try target periods (exact, quarterly/monthly equiv) with non-null value
    for (const tp of targetPeriods) {
      const foundIdx = periods.indexOf(tp);
      if (foundIdx >= 0 && metricArr[foundIdx] !== null && metricArr[foundIdx] !== undefined) {
        idx = foundIdx;
        break;
      }
    }

    // 2. Try any period in the same year with non-null value
    if (idx < 0 && yearStr) {
      const matches = periods
        .map((p, i) => ({ p, i, val: metricArr[i] }))
        .filter((x) => String(x.p).startsWith(yearStr) && x.val !== null && x.val !== undefined);
      if (matches.length) {
        idx = matches[matches.length - 1].i;
      }
    }

    if (idx >= 0) {
      const value = metricArr[idx];
      if (value !== null && value !== undefined) out.push({ bank_id: bank, value });
    }
  }
  return out;
}

/** Đơn vị KHÔNG có giá trị của chỉ tiêu ở kỳ `period` -> không được xếp hạng/đánh giá. */
export function notEvaluatedAtPeriod(data: FreqData, metric: string, period: string): string[] {
  const sd = data.series?.data || {};
  const targetPeriods = getTargetPeriods(period);
  const yearStr = period ? period.slice(0, 4) : "";

  return Object.keys(sd)
    .filter((bank) => {
      const periods: string[] = sd[bank].periods || [];
      if (!periods.length) return true;

      const metricArr = sd[bank][metric] || [];
      let idx = -1;

      for (const tp of targetPeriods) {
        const foundIdx = periods.indexOf(tp);
        if (foundIdx >= 0 && metricArr[foundIdx] !== null && metricArr[foundIdx] !== undefined) {
          idx = foundIdx;
          break;
        }
      }

      if (idx < 0 && yearStr) {
        const matches = periods
          .map((p, i) => ({ p, i, val: metricArr[i] }))
          .filter((x) => String(x.p).startsWith(yearStr) && x.val !== null && x.val !== undefined);
        if (matches.length) {
          idx = matches[matches.length - 1].i;
        }
      }

      const value = idx >= 0 ? metricArr[idx] : null;
      return value === null || value === undefined;
    })
    .sort();
}
