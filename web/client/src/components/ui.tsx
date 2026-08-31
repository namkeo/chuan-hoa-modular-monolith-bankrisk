import React from "react";
import { fmt, scoreColor } from "../format";

export function Loader({ text = "Đang tải..." }: { text?: string }) {
  return (
    <div className="loader-wrap">
      <div className="spinner" />
      <div>{text}</div>
    </div>
  );
}

export function Card({ title, sub, children, className = "", style }: {
  title?: string; sub?: string; children: React.ReactNode;
  className?: string; style?: React.CSSProperties;
}) {
  return (
    <div className={`card ${className}`} style={style}>
      {title && <h3>{title}{sub && <span className="sub">· {sub}</span>}</h3>}
      {children}
    </div>
  );
}

/**
 * Chú thích các đơn vị KHÔNG có giá trị của chỉ tiêu ở kỳ đang xem.
 *
 * Ô trống trong bảng xếp hạng dễ bị hiểu là "không có cờ = an toàn". Nói rõ đơn vị
 * nào không được đánh giá và vì sao, đúng như rule engine làm với SPECIAL_CONTROL /
 * DATA_GAP thay vì bỏ qua im lặng.
 */
export function NotEvaluatedNote({ banks, label }: { banks: string[]; label: string }) {
  if (!banks.length) return null;
  const shown = banks.slice(0, 8).join(", ") + (banks.length > 8 ? "…" : "");
  return (
    <div className="note-muted">
      ⚠️ {banks.length} đơn vị không có giá trị {label} ở kỳ này nên không được xếp
      hạng/đánh giá: {shown}. Lý do xem trang <b>Validation &amp; chất lượng</b>.
    </div>
  );
}

export function Kpi({ label, value, meta, color }: {
  label: string; value: React.ReactNode; meta?: string; color?: string;
}) {
  return (
    <div className="card kpi-card">
      {color && <span className="bar" style={{ background: color }} />}
      <div style={{ paddingLeft: color ? 10 : 0 }}>
        <div className="label">{label}</div>
        <div className="value">{value}</div>
        {meta && <div className="meta">{meta}</div>}
      </div>
    </div>
  );
}

export function Badge({ level }: { level: string }) {
  const l = (level || "INFO").toUpperCase().replace(/\s/g, "_");
  return <span className={`badge ${l}`}>{level}</span>;
}

export function ScorePill({ score }: { score: number | null | undefined }) {
  const c = scoreColor(score);
  return (
    <span className="score-pill" style={{ background: c.bg, color: c.fg }}>
      {score === null || score === undefined ? "—" : fmt(score, 0)}
    </span>
  );
}

export function Empty({ text = "Không có dữ liệu" }: { text?: string }) {
  return <div className="empty-state"><div className="big">📭</div>{text}</div>;
}

export function Disclaimer({ text }: { text: string }) {
  return <div className="disclaimer">⚠️ {text}</div>;
}

/** Lightweight, dependency-free data table with optional column renderers. */
export interface Col {
  key: string;
  label: string;
  num?: boolean;
  render?: (row: any) => React.ReactNode;
  width?: number | string;
}
export function DataTable({ cols, rows, maxHeight = 520, empty = "Không có dữ liệu" }: {
  cols: Col[]; rows: any[]; maxHeight?: number; empty?: string;
}) {
  if (!rows || rows.length === 0) return <Empty text={empty} />;
  return (
    <div className="table-wrap">
      <div className="table-scroll" style={{ maxHeight }}>
        <table className="tbl">
          <thead>
            <tr>{cols.map((c) => (
              <th key={c.key} style={{ width: c.width, textAlign: c.num ? "right" : "left" }}>{c.label}</th>
            ))}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {cols.map((c) => (
                  <td key={c.key} className={c.num ? "num" : ""}>
                    {c.render ? c.render(r) : (r[c.key] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
