import { useState } from "react";
import { FREQ_LABEL, type FreqData } from "../api";
import { Card, DataTable, Disclaimer, Kpi } from "../components/ui";
import { fmt, fmtInt } from "../format";
import { useStore } from "../store";

const SRC_COLOR: Record<string, string> = {
  monthly: "#2f80ed", quarterly: "#6b46c1", yearly: "#e0701a", daily: "#0a9396",
};

const COLLAPSED_ROWS = 12;

function missColor(p: number) {
  return p > 60 ? "#c62828" : p > 30 ? "#e0701a" : "#2f80ed";
}

/** Danh sách chỉ tiêu GỐC còn thiếu (tên đúng như trong file dữ liệu nguồn).
 *  Biến phái sinh (__qoq/__yoy/__accel…) không liệt kê ở đây vì chỉ là biến thể
 *  tính toán của cùng một chỉ tiêu — chúng vẫn được dùng làm feature cho ML. */
function MissingMetrics({ rows }: { rows: FreqData["missing_by_metric"] }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? rows : rows.slice(0, COLLAPSED_ROWS);
  const hidden = rows.length - shown.length;

  return (
    <Card title="Chỉ tiêu còn thiếu"
      sub={`${rows.length} chỉ tiêu gốc · đã gộp biến phái sinh`}>
      <DataTable maxHeight={expanded ? 620 : 360} empty="Không có chỉ tiêu nào thiếu"
        cols={[
          {
            key: "label", label: "Chỉ tiêu (theo dữ liệu gốc)",
            render: (r) => (
              <span title={`${r.metric}${r.unit ? ` · ĐVT: ${r.unit}` : ""}`}>
                {r.label}
                {r.is_derived_ratio && <span className="help"> · tính toán</span>}
              </span>
            ),
          },
          { key: "camels_group", label: "CAMELS", width: 90 },
          { key: "n_missing", label: "Số kỳ thiếu", num: true, width: 100,
            render: (r) => `${fmtInt(r.n_missing)}/${fmtInt(r.n_total)}` },
          {
            key: "missing_pct", label: "Tỷ lệ thiếu", num: true, width: 130,
            render: (r) => (
              <span className="miss-cell">
                <span className="miss-bar">
                  <span style={{ width: `${r.missing_pct}%`, background: missColor(r.missing_pct) }} />
                </span>
                <b style={{ color: missColor(r.missing_pct) }}>{fmt(r.missing_pct)}%</b>
              </span>
            ),
          },
        ]}
        rows={shown} />
      {rows.length > COLLAPSED_ROWS && (
        <button className="link-btn" onClick={() => setExpanded(!expanded)}>
          {expanded ? "▲ Thu gọn" : `▼ Xem toàn bộ (còn ${hidden} chỉ tiêu)`}
        </button>
      )}
    </Card>
  );
}

export default function Overview() {
  const { data } = useStore();
  if (!data || data.empty) return null;
  const s = data.summary || {};
  const lv = s.level_counts || {};
  const comb = data.combined;

  return (
    <>
      <Disclaimer text={data.disclaimer} />

      {comb?.is_combined && (
        <Card title="🔗 Tích hợp đa tần suất (combined)" sub="lấy gần nhất theo thời điểm (as-of), không nhìn trước"
          style={{ marginBottom: 16 }}>
          <p className="help" style={{ marginTop: 0 }}>
            Mỗi bank-tháng được làm giàu bằng giá trị gần nhất từ tần suất Quý & Năm.
            Mô hình (rule, Isolation Forest, K-means, EWS, stress) dùng bộ chỉ tiêu hợp nhất này.
            {comb.meta?.enriched_from?.map((e: any) => ` +${e.metrics_added} chỉ tiêu từ ${FREQ_LABEL[e.frequency] || e.frequency}.`)}
          </p>
          <div className="row-flex" style={{ marginBottom: 12 }}>
            {Object.entries(comb.by_source || {}).map(([f, n]) => (
              <span key={f} className="inline-stat">
                <span className="dot" style={{ background: SRC_COLOR[f] || "#888" }} />
                <span className="n">{n as number}</span> chỉ tiêu nguồn {FREQ_LABEL[f] || f}
              </span>
            ))}
          </div>
          <DataTable maxHeight={240}
            cols={[
              { key: "metric", label: "Chỉ tiêu" },
              { key: "primary_frequency", label: "Tần suất nguồn", render: (r) => (
                <span className="badge" style={{ background: (SRC_COLOR[r.primary_frequency] || "#888") + "22", color: SRC_COLOR[r.primary_frequency] || "#555" }}>
                  {FREQ_LABEL[r.primary_frequency] || r.primary_frequency}</span>) },
              { key: "sources", label: "Có ở tần suất" },
              { key: "is_cross_frequency", label: "Liên tần suất", render: (r) => r.is_cross_frequency ? "✓" : "" },
            ]}
            rows={comb.source_map || []} />
        </Card>
      )}
      <div className="grid kpi">
        <Kpi label="Số ngân hàng" value={fmtInt(s.n_banks)} meta={`${(data.files || []).length} file đã đọc`} color="#2f80ed" />
        <Kpi label="Số kỳ báo cáo" value={fmtInt(s.n_periods)} meta={`Tần suất: ${data.frequency}`} color="#0a2540" />
        <Kpi label="Tỷ lệ thiếu dữ liệu" value={`${fmt(s.missing_pct)}%`} color="#c98a00" />
        <Kpi label="NH mức CRITICAL" value={fmtInt(lv.CRITICAL || 0)} meta="kỳ gần nhất" color="#c62828" />
        <Kpi label="Bất thường (ML)" value={`${fmt(s.anomaly_rate)}%`} meta={`${s.n_anomalies || 0} bank-period`} color="#e0701a" />
        <Kpi label="Số cụm K-means" value={fmtInt(s.cluster_k)} meta={`silhouette ${fmt(s.silhouette, 3)}`} color="#6b46c1" />
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <MissingMetrics rows={data.missing_by_metric || []} />

        <Card title="Các file đã đọc" sub={`${(data.files || []).length} workbook`}>
          <DataTable maxHeight={360}
            cols={[
              { key: "bank_id", label: "Ngân hàng" },
              { key: "frequencies", label: "Tần suất", render: (r) => (r.frequencies || []).join(", ") },
              { key: "metrics", label: "Chỉ tiêu", num: true },
              { key: "rows", label: "Dòng panel", num: true, render: (r) => fmtInt(r.rows) },
              { key: "size_kb", label: "KB", num: true },
            ]}
            rows={data.files || []} />
        </Card>
      </div>

      {(data.unmapped_labels || []).length > 0 && (
        <Card title="Nhãn chỉ tiêu CHƯA map" sub="cần bổ sung config/column_mapping.yaml" className="">
          <div style={{ marginTop: -6 }}>
            <DataTable maxHeight={240}
              cols={[
                { key: "label", label: "Nhãn trong file" },
                { key: "count", label: "Số lần", num: true },
              ]}
              rows={data.unmapped_labels || []} />
          </div>
        </Card>
      )}
    </>
  );
}
