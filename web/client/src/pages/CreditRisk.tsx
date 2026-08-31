import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAsOf } from "../components/PeriodPicker";
import { Card, DataTable, Kpi, NotEvaluatedNote } from "../components/ui";
import { fmt } from "../format";
import { useStore } from "../store";
import { atPeriodByMetric, notEvaluatedAtPeriod } from "./domainUtils";

// Cờ đỏ tín dụng bổ sung (readme_explain_bo_sung.docx §13.2).
const CREDIT_FLAG_CATS = [
  "CREDIT_GROWTH_CAPITAL_GAP", "CREDIT_GROWTH_RWA_DIVERGENCE", "NPL_GROUP2_MIGRATION",
  "PROVISION_LAG", "CONCENTRATION_BUILDUP", "ACCRUED_INTEREST_CREDIT_STRESS",
  "HOT_CREDIT_WEAK_SUPPORT",
];

export default function CreditRisk() {
  const { data } = useStore();
  const asof = useAsOf();
  if (!data || data.empty) return null;
  const per = asof.period;
  // Biểu đồ + KPI: giá trị tại ĐÚNG kỳ đang chọn (bỏ đơn vị không có số kỳ đó).
  const npl = atPeriodByMetric(data, "npl_ratio", per).sort((a, b) => b.value - a.value).slice(0, 20);
  const g2 = atPeriodByMetric(data, "group2_ratio", per).sort((a, b) => b.value - a.value).slice(0, 20);
  const nplSkipped = notEvaluatedAtPeriod(data, "npl_ratio", per);
  const g2Skipped = notEvaluatedAtPeriod(data, "group2_ratio", per);
  const avgNpl = npl.length ? npl.reduce((a, b) => a + b.value, 0) / npl.length : 0;
  // Chỉ tiêu bổ sung §13.5: dự phòng/dư nợ và lãi dự thu/dư nợ tại kỳ đang chọn.
  const prov = atPeriodByMetric(data, "provision_to_loans", per).sort((a, b) => a.value - b.value).slice(0, 20);
  const accr = atPeriodByMetric(data, "accrued_interest_to_loans", per).sort((a, b) => b.value - a.value).slice(0, 20);
  // Cờ đỏ tín dụng mở rộng — giữ toàn bộ dòng thời gian (sự kiện có mốc kỳ).
  const creditFlags = data.validation.filter((v) => CREDIT_FLAG_CATS.includes(v.category));

  // Xếp hạng: điểm rủi ro tín dụng của kỳ đang chọn, CHỈ đơn vị được đánh giá.
  const periodScores = asof.filter(data.scores);
  const ranking = periodScores
    .filter((r) => r.credit_risk_score != null)
    .sort((a, b) => (b.credit_risk_score || 0) - (a.credit_risk_score || 0));
  const rankSkipped = periodScores
    .filter((r) => r.credit_risk_score == null).map((r) => r.bank_id).sort();
  const creditMean = ranking.length
    ? ranking.reduce((a, r) => a + (r.credit_risk_score || 0), 0) / ranking.length : 0;
  const periodTag = `kỳ ${per}${asof.isLatest ? " (gần nhất)" : ""}`;

  return (
    <>
      <div className="grid kpi">
        <Kpi label="Điểm rủi ro tín dụng TB" value={fmt(creditMean)} meta={`${ranking.length} đơn vị · ${periodTag}`} color="#2f80ed" />
        <Kpi label="NPL cao nhất" value={`${fmt(npl[0]?.value)}%`} meta={npl[0]?.bank_id} color="#c62828" />
        <Kpi label="Số NH NPL > 3%" value={fmt(npl.filter((n) => n.value > 3).length, 0)} meta={`TB ${fmt(avgNpl)}%`} color="#e0701a" />
        <Kpi label="Cờ đỏ tín dụng" value={fmt(creditFlags.length, 0)} meta="mọi kỳ · 6 nhóm tín hiệu bổ sung" color="#6b46c1" />
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Tỷ lệ nợ xấu (NPL) — top 20" sub={`ngưỡng kiểm soát 3% · ${periodTag}`}>
          <ResponsiveContainer width="100%" height={360}>
            <BarChart data={npl} margin={{ left: 0, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="bank_id" fontSize={9} angle={-45} textAnchor="end" height={70} interval={0} />
              <YAxis fontSize={11} unit="%" />
              <Tooltip formatter={(v: any) => `${fmt(v, 2)}%`} />
              <ReferenceLine y={3} stroke="#c62828" strokeDasharray="4 4" label={{ value: "3%", fontSize: 11 }} />
              <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                {npl.map((d, i) => <Cell key={i} fill={d.value > 5 ? "#c62828" : d.value > 3 ? "#e0701a" : "#2f80ed"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <NotEvaluatedNote banks={nplSkipped} label="tỷ lệ nợ xấu" />
        </Card>
        <Card title="Tỷ lệ nợ nhóm 2 — top 20" sub={`nợ xấu tiềm ẩn · ${periodTag}`}>
          <ResponsiveContainer width="100%" height={360}>
            <BarChart data={g2} margin={{ left: 0, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="bank_id" fontSize={9} angle={-45} textAnchor="end" height={70} interval={0} />
              <YAxis fontSize={11} unit="%" />
              <Tooltip formatter={(v: any) => `${fmt(v, 2)}%`} />
              <Bar dataKey="value" fill="#c98a00" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <NotEvaluatedNote banks={g2Skipped} label="tỷ lệ nợ nhóm 2" />
        </Card>
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Dự phòng / tổng dư nợ — 20 thấp nhất" sub={`đệm dự phòng mỏng = rủi ro (chỉ tiêu bổ sung §13.5) · ${periodTag}`}>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={prov} margin={{ left: 0, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="bank_id" fontSize={9} angle={-45} textAnchor="end" height={70} interval={0} />
              <YAxis fontSize={11} unit="%" />
              <Tooltip formatter={(v: any) => `${fmt(v, 2)}%`} />
              <Bar dataKey="value" fill="#2f80ed" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <NotEvaluatedNote banks={notEvaluatedAtPeriod(data, "provision_to_loans", per)} label="dự phòng/dư nợ" />
        </Card>
        <Card title="Lãi dự thu / tổng dư nợ — top 20" sub={`thu nhập chưa thu tiền gắn với danh mục (§13.5) · ${periodTag}`}>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={accr} margin={{ left: 0, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="bank_id" fontSize={9} angle={-45} textAnchor="end" height={70} interval={0} />
              <YAxis fontSize={11} unit="%" />
              <Tooltip formatter={(v: any) => `${fmt(v, 2)}%`} />
              <Bar dataKey="value" fill="#c98a00" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <NotEvaluatedNote banks={notEvaluatedAtPeriod(data, "accrued_interest_to_loans", per)} label="lãi dự thu/dư nợ" />
        </Card>
      </div>

      <Card title="Xếp hạng điểm rủi ro tín dụng (mở rộng 6 nhóm)" sub={`biến lõi + điểm nhóm: cơ cấu, dự phòng, tập trung, ngoại bảng/lãi dự thu, vốn · ${periodTag}`} className="pad0">
        <DataTable maxHeight={420}
          cols={[
            { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
            { key: "period", label: "Kỳ" },
            { key: "credit_risk_score", label: "Điểm tín dụng", num: true, render: (r) => fmt(r.credit_risk_score, 1) },
            { key: "credit_structure_score", label: "Cơ cấu KH", num: true, render: (r) => fmt(r.credit_structure_score, 0) },
            { key: "credit_provision_score", label: "Dự phòng", num: true, render: (r) => fmt(r.credit_provision_score, 0) },
            { key: "credit_concentration_score", label: "Tập trung", num: true, render: (r) => fmt(r.credit_concentration_score, 0) },
            { key: "credit_offbalance_score", label: "NB/Lãi dự thu", num: true, render: (r) => fmt(r.credit_offbalance_score, 0) },
            { key: "credit_capital_score", label: "Vốn", num: true, render: (r) => fmt(r.credit_capital_score, 0) },
            { key: "credit_flag_clusters", label: "Cụm cờ đỏ", num: true, render: (r) => fmt(r.credit_flag_clusters, 0) },
            { key: "final_risk_score", label: "Điểm tổng", num: true, render: (r) => fmt(r.final_risk_score, 1) },
          ]}
          rows={ranking} />
        <NotEvaluatedNote banks={rankSkipped} label="điểm rủi ro tín dụng" />
      </Card>

      <Card title="Cờ đỏ tín dụng bổ sung (§13.2)" sub="tăng trưởng-vốn, RWA phân kỳ, chuyển nhóm nợ, dự phòng trễ, tập trung, lãi dự thu — toàn bộ dòng thời gian" className="pad0" style={{ marginTop: 16 }}>
        <DataTable maxHeight={400}
          cols={[
            { key: "category", label: "Cờ đỏ", render: (r) => <span className="badge HIGH">{r.category}</span> },
            { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
            { key: "period", label: "Kỳ" },
            { key: "severity", label: "Mức độ" },
            { key: "message", label: "Mô tả" },
          ]}
          rows={creditFlags} empty="Không phát hiện cờ đỏ tín dụng bổ sung." />
      </Card>
    </>
  );
}
