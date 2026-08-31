import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAsOf } from "../components/PeriodPicker";
import { Card, DataTable, Kpi, NotEvaluatedNote } from "../components/ui";
import { fmt } from "../format";
import { useStore } from "../store";
import { atPeriodByMetric, notEvaluatedAtPeriod } from "./domainUtils";

// Cờ đỏ thanh khoản bổ sung (readme_explain_bo_sung.docx §13.3).
const LIQ_FLAG_CATS = [
  "HQLA_OUTFLOW_STRESS", "DEPOSIT_CASA_STRESS", "WHOLESALE_FUNDING_SUBSTITUTION",
  "MATURITY_MISMATCH_BUILDUP", "FX_LIQUIDITY_DIVERGENCE", "INTEREST_RATE_GAP_LIQUIDITY",
  "LDR_HIGH_DEPOSIT_STRESS",
];

export default function LiquidityRisk() {
  const { data } = useStore();
  const asof = useAsOf();
  if (!data || data.empty) return null;
  const per = asof.period;
  // Biểu đồ + KPI: giá trị tại ĐÚNG kỳ đang chọn (bỏ đơn vị không có số kỳ đó).
  const ldr = atPeriodByMetric(data, "ldr", per).sort((a, b) => b.value - a.value).slice(0, 20);
  const stf = atPeriodByMetric(data, "st_funding_for_mlt_loans", per).sort((a, b) => b.value - a.value).slice(0, 20);
  const ldrSkipped = notEvaluatedAtPeriod(data, "ldr", per);
  const stfSkipped = notEvaluatedAtPeriod(data, "st_funding_for_mlt_loans", per);
  // Chỉ tiêu bổ sung §13.5: phụ thuộc vốn bán buôn + CASA tại kỳ đang chọn.
  const wfs = atPeriodByMetric(data, "wholesale_funding_share", per).sort((a, b) => b.value - a.value).slice(0, 20);
  const casa = atPeriodByMetric(data, "casa", per).sort((a, b) => a.value - b.value).slice(0, 20);
  // Cờ đỏ thanh khoản mở rộng — giữ toàn bộ dòng thời gian (sự kiện có mốc kỳ).
  const liqFlags = data.validation.filter((v) => LIQ_FLAG_CATS.includes(v.category));

  // Xếp hạng: điểm rủi ro thanh khoản của kỳ đang chọn, CHỈ đơn vị được đánh giá.
  const periodScores = asof.filter(data.scores);
  const ranking = periodScores
    .filter((r) => r.liquidity_risk_score != null)
    .sort((a, b) => (b.liquidity_risk_score || 0) - (a.liquidity_risk_score || 0));
  const rankSkipped = periodScores
    .filter((r) => r.liquidity_risk_score == null).map((r) => r.bank_id).sort();
  const liqMean = ranking.length
    ? ranking.reduce((a, r) => a + (r.liquidity_risk_score || 0), 0) / ranking.length : 0;
  const periodTag = `kỳ ${per}${asof.isLatest ? " (gần nhất)" : ""}`;

  return (
    <>
      <div className="grid kpi">
        <Kpi label="Điểm rủi ro thanh khoản TB" value={fmt(liqMean)} meta={`${ranking.length} đơn vị · ${periodTag}`} color="#0a9396" />
        <Kpi label="LDR cao nhất" value={`${fmt(ldr[0]?.value)}%`} meta={ldr[0]?.bank_id} color="#c62828" />
        <Kpi label="Số NH LDR > 85%" value={fmt(ldr.filter((n) => n.value > 85).length, 0)} meta="vượt trần TT22" color="#e0701a" />
        <Kpi label="Cờ đỏ thanh khoản" value={fmt(liqFlags.length, 0)} meta="mọi kỳ · 6 nhóm tín hiệu bổ sung" color="#6b46c1" />
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="LDR — top 20" sub={`trần quy định 85% · ${periodTag}`}>
          <ResponsiveContainer width="100%" height={360}>
            <BarChart data={ldr} margin={{ left: 0, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="bank_id" fontSize={9} angle={-45} textAnchor="end" height={70} interval={0} />
              <YAxis fontSize={11} unit="%" />
              <Tooltip formatter={(v: any) => `${fmt(v, 2)}%`} />
              <ReferenceLine y={85} stroke="#c62828" strokeDasharray="4 4" label={{ value: "85%", fontSize: 11 }} />
              <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                {ldr.map((d, i) => <Cell key={i} fill={d.value > 85 ? "#c62828" : d.value > 80 ? "#e0701a" : "#0a9396"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <NotEvaluatedNote banks={ldrSkipped} label="LDR" />
        </Card>
        <Card title="Vốn ngắn hạn cho vay trung-dài hạn — top 20" sub={`trần hiện hành 30% · ${periodTag}`}>
          <ResponsiveContainer width="100%" height={360}>
            <BarChart data={stf} margin={{ left: 0, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="bank_id" fontSize={9} angle={-45} textAnchor="end" height={70} interval={0} />
              <YAxis fontSize={11} unit="%" />
              <Tooltip formatter={(v: any) => `${fmt(v, 2)}%`} />
              <ReferenceLine y={30} stroke="#c62828" strokeDasharray="4 4" label={{ value: "30%", fontSize: 11 }} />
              <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                {stf.map((d, i) => <Cell key={i} fill={d.value > 30 ? "#c62828" : "#0a9396"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <NotEvaluatedNote banks={stfSkipped} label="vốn ngắn hạn cho vay TDH" />
        </Card>
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Phụ thuộc vốn bán buôn — top 20" sub={`(vay TCTD + GTCG) / tổng nguồn huy động (§13.5) · ${periodTag}`}>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={wfs} margin={{ left: 0, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="bank_id" fontSize={9} angle={-45} textAnchor="end" height={70} interval={0} />
              <YAxis fontSize={11} unit="%" />
              <Tooltip formatter={(v: any) => `${fmt(v, 2)}%`} />
              <Bar dataKey="value" fill="#e0701a" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <NotEvaluatedNote banks={notEvaluatedAtPeriod(data, "wholesale_funding_share", per)} label="phụ thuộc vốn bán buôn" />
        </Card>
        <Card title="CASA — 20 thấp nhất" sub={`độ ổn định tiền gửi: CASA thấp = nguồn vốn đắt/kém ổn định · ${periodTag}`}>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={casa} margin={{ left: 0, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="bank_id" fontSize={9} angle={-45} textAnchor="end" height={70} interval={0} />
              <YAxis fontSize={11} unit="%" />
              <Tooltip formatter={(v: any) => `${fmt(v, 2)}%`} />
              <Bar dataKey="value" fill="#0a9396" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <NotEvaluatedNote banks={notEvaluatedAtPeriod(data, "casa", per)} label="CASA" />
        </Card>
      </div>

      <Card title="Xếp hạng điểm rủi ro thanh khoản (mở rộng 5 nhóm)" sub={`biến lõi + điểm nhóm: ổn định tiền gửi/CASA, vốn bán buôn, đệm thứ cấp, nhạy cảm thị trường · ${periodTag}`} className="pad0">
        <DataTable maxHeight={420}
          cols={[
            { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
            { key: "period", label: "Kỳ" },
            { key: "liquidity_risk_score", label: "Điểm thanh khoản", num: true, render: (r) => fmt(r.liquidity_risk_score, 1) },
            { key: "liq_deposit_score", label: "Ổn định TG/CASA", num: true, render: (r) => fmt(r.liq_deposit_score, 0) },
            { key: "liq_wholesale_score", label: "Vốn bán buôn", num: true, render: (r) => fmt(r.liq_wholesale_score, 0) },
            { key: "liq_secondary_score", label: "Đệm thứ cấp", num: true, render: (r) => fmt(r.liq_secondary_score, 0) },
            { key: "liq_market_score", label: "Nhạy cảm TT", num: true, render: (r) => fmt(r.liq_market_score, 0) },
            { key: "liq_flag_clusters", label: "Cụm cờ đỏ", num: true, render: (r) => fmt(r.liq_flag_clusters, 0) },
            { key: "final_risk_score", label: "Điểm tổng", num: true, render: (r) => fmt(r.final_risk_score, 1) },
          ]}
          rows={ranking} />
        <NotEvaluatedNote banks={rankSkipped} label="điểm rủi ro thanh khoản" />
      </Card>

      <Card title="Cờ đỏ thanh khoản bổ sung (§13.3)" sub="HQLA-dòng tiền ra, tiền gửi/CASA, thay thế vốn bán buôn, lệch kỳ hạn, ngoại tệ, lãi suất — toàn bộ dòng thời gian" className="pad0" style={{ marginTop: 16 }}>
        <DataTable maxHeight={400}
          cols={[
            { key: "category", label: "Cờ đỏ", render: (r) => <span className="badge HIGH">{r.category}</span> },
            { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
            { key: "period", label: "Kỳ" },
            { key: "severity", label: "Mức độ" },
            { key: "message", label: "Mô tả" },
          ]}
          rows={liqFlags} empty="Không phát hiện cờ đỏ thanh khoản bổ sung." />
      </Card>
    </>
  );
}
