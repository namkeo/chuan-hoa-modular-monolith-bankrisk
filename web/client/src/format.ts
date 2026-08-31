/** Number / value formatting helpers shared across pages. */
export function fmt(v: any, digits = 1): string {
  if (v === null || v === undefined || v === "" || Number.isNaN(v)) return "—";
  if (typeof v === "number") {
    return v.toLocaleString("vi-VN", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
  }
  return String(v);
}

export function fmtInt(v: any): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 0 });
}

/** Risk-score -> background+text colour for the score pill. */
export function scoreColor(score: number | null | undefined): { bg: string; fg: string } {
  if (score === null || score === undefined) return { bg: "#eef1f5", fg: "#8a94a6" };
  if (score >= 75) return { bg: "#fbe4e4", fg: "#c62828" };
  if (score >= 50) return { bg: "#fceadb", fg: "#e0701a" };
  if (score >= 25) return { bg: "#fdf3dc", fg: "#c98a00" };
  return { bg: "#e7f4e8", fg: "#2e7d32" };
}

/** Heatmap colour ramp for a 0..100 risk score. */
export function heatColor(v: number | null): string {
  if (v === null || v === undefined) return "#eef1f5";
  const stops: [number, [number, number, number]][] = [
    [0, [231, 244, 232]],
    [40, [253, 243, 220]],
    [65, [252, 234, 219]],
    [100, [198, 40, 40]],
  ];
  const c = Math.max(0, Math.min(100, v));
  for (let i = 0; i < stops.length - 1; i++) {
    const [p0, c0] = stops[i];
    const [p1, c1] = stops[i + 1];
    if (c >= p0 && c <= p1) {
      const t = (c - p0) / (p1 - p0 || 1);
      const ch = (a: number, b: number) => Math.round(a + (b - a) * t);
      return `rgb(${ch(c0[0], c1[0])},${ch(c0[1], c1[1])},${ch(c0[2], c1[2])})`;
    }
  }
  return "#c62828";
}

export const LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
export const DOMAIN_LABELS: Record<string, string> = {
  credit: "Tín dụng", liquidity: "Thanh khoản", capital: "Vốn",
  profitability: "Sinh lời", market: "Thị trường",
  fraud: "Gian lận (proxy)", failure: "Đổ vỡ (proxy)",
};
