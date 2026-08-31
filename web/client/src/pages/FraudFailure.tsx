import { useAsOf } from "../components/PeriodPicker";
import { Card, DataTable, Disclaimer, Kpi, NotEvaluatedNote } from "../components/ui";
import { fmt } from "../format";
import { useStore } from "../store";

const REDFLAG_CATS = [
  // Cờ đỏ gốc
  "NPL_DROP_DIVERGENCE", "PROFIT_UP_OPS_DOWN", "HOT_CREDIT_WEAK_SUPPORT", "LDR_HIGH_DEPOSIT_STRESS",
  // Bộ cờ đỏ gian lận BCTC mở rộng (readme_explain_bo_sung.docx §13.4.1)
  "ACCRUED_INTEREST_PROFIT_DIVERGENCE", "NPL_GROUP2_PROVISION_DIVERGENCE",
  "OFFBALANCE_RISK_SHIFT", "YEAR_END_LIQUIDITY_WINDOW_DRESSING",
  "CAPITAL_COMPONENT_MISMATCH", "CREDIT_GROWTH_RWA_DIVERGENCE", "FUNDING_SOURCE_SWAP",
];

export default function FraudFailure() {
  const { data } = useStore();
  const asof = useAsOf();
  if (!data || data.empty) return null;

  // Điểm proxy của kỳ đang chọn; CHỈ đơn vị được đánh giá (đủ dữ liệu/lịch sử).
  const periodScores = asof.filter(data.scores);
  const fraud = periodScores
    .filter((r) => r.fraud_risk_proxy_score != null)
    .sort((a, b) => (b.fraud_risk_proxy_score || 0) - (a.fraud_risk_proxy_score || 0)).slice(0, 15);
  const failure = periodScores
    .filter((r) => r.failure_risk_proxy_score != null)
    .sort((a, b) => (b.failure_risk_proxy_score || 0) - (a.failure_risk_proxy_score || 0)).slice(0, 15);
  const fraudSkipped = periodScores.filter((r) => r.fraud_risk_proxy_score == null).map((r) => r.bank_id).sort();
  const failureSkipped = periodScores.filter((r) => r.failure_risk_proxy_score == null).map((r) => r.bank_id).sort();

  const mean = (rows: any[], key: string) => rows.length
    ? rows.reduce((a, r) => a + (r[key] || 0), 0) / rows.length : 0;
  const fraudMean = mean(periodScores.filter((r) => r.fraud_risk_proxy_score != null), "fraud_risk_proxy_score");
  const failMean = mean(periodScores.filter((r) => r.failure_risk_proxy_score != null), "failure_risk_proxy_score");

  // Cờ đỏ đặc biệt: sự kiện có mốc thời gian -> giữ toàn bộ dòng thời gian (không lọc kỳ).
  const redflags = data.validation.filter((v) => REDFLAG_CATS.includes(v.category));
  const periodTag = `kỳ ${asof.period}${asof.isLatest ? " (gần nhất)" : ""}`;

  return (
    <>
      <Disclaimer text="Đây là CHỈ BÁO NGUY CƠ (proxy) dựa trên bất thường, pattern và vi phạm rule — KHÔNG khẳng định gian lận/đổ vỡ. Bài toán không có nhãn lịch sử; kết quả cần KTV kiểm tra hồ sơ thực tế." />
      <div className="grid kpi">
        <Kpi label="Điểm gian lận (proxy) TB" value={fmt(fraudMean)} meta={`${fraud.length ? periodScores.filter((r) => r.fraud_risk_proxy_score != null).length : 0} đơn vị · ${periodTag}`} color="#e0701a" />
        <Kpi label="Điểm đổ vỡ (proxy) TB" value={fmt(failMean)} meta={periodTag} color="#c62828" />
        <Kpi label="Cờ đỏ đặc biệt" value={fmt(redflags.length, 0)} meta="mọi kỳ · special-case detection" color="#6b46c1" />
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Top nghi ngờ gian lận (proxy)" sub={`điểm ưu tiên SỐ CỤM phân kỳ kích hoạt (§13.6: gom cờ cùng bản chất) · ${periodTag}`} className="pad0">
          <DataTable maxHeight={400}
            cols={[
              { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
              { key: "period", label: "Kỳ" },
              { key: "fraud_risk_proxy_score", label: "Điểm", num: true, render: (r) => fmt(r.fraud_risk_proxy_score, 1) },
              { key: "fraud_flag_clusters", label: "Cụm phân kỳ", num: true, render: (r) => fmt(r.fraud_flag_clusters, 0) },
              { key: "fraud_flags", label: "Cờ kích hoạt", render: (r) => <span style={{ fontSize: 11 }}>{r.fraud_flags || "—"}</span> },
            ]}
            rows={fraud} />
          <NotEvaluatedNote banks={fraudSkipped} label="điểm gian lận (proxy)" />
        </Card>
        <Card title="Top nguy cơ đổ vỡ (proxy)" sub={periodTag} className="pad0">
          <DataTable maxHeight={400}
            cols={[
              { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
              { key: "period", label: "Kỳ" },
              { key: "failure_risk_proxy_score", label: "Điểm", num: true, render: (r) => fmt(r.failure_risk_proxy_score, 1) },
            ]}
            rows={failure} />
          <NotEvaluatedNote banks={failureSkipped} label="điểm đổ vỡ (proxy)" />
        </Card>
      </div>

      <Card title="Cờ đỏ đặc biệt (special-case detection)" sub="dấu hiệu che giấu / căng thẳng — toàn bộ dòng thời gian" className="pad0">
        <DataTable maxHeight={400}
          cols={[
            { key: "category", label: "Loại", render: (r) => <span className="badge HIGH">{r.category}</span> },
            { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
            { key: "period", label: "Kỳ" },
            { key: "message", label: "Mô tả" },
          ]}
          rows={redflags} empty="Không phát hiện cờ đỏ đặc biệt." />
      </Card>
    </>
  );
}
