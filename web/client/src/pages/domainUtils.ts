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
export function atPeriodByMetric(data: FreqData, metric: string, period: string): MetricPoint[] {
  const out: MetricPoint[] = [];
  const sd = data.series?.data || {};
  for (const bank of Object.keys(sd)) {
    const periods: string[] = sd[bank].periods || [];
    const idx = periods.indexOf(period);
    if (idx < 0) continue;
    const value = (sd[bank][metric] || [])[idx];
    if (value !== null && value !== undefined) out.push({ bank_id: bank, value });
  }
  return out;
}

/** Đơn vị KHÔNG có giá trị của chỉ tiêu ở kỳ `period` -> không được xếp hạng/đánh giá. */
export function notEvaluatedAtPeriod(data: FreqData, metric: string, period: string): string[] {
  const sd = data.series?.data || {};
  return Object.keys(sd)
    .filter((bank) => {
      const periods: string[] = sd[bank].periods || [];
      const idx = periods.indexOf(period);
      const value = idx >= 0 ? (sd[bank][metric] || [])[idx] : null;
      return value === null || value === undefined;
    })
    .sort();
}
