import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAsOf } from "../components/PeriodPicker";
import { Badge, Card, DataTable, Kpi, ScorePill } from "../components/ui";
import { DOMAIN_LABELS, fmt, fmtInt, heatColor } from "../format";
import { useStore } from "../store";

export default function RiskDashboard() {
  const { data } = useStore();
  const asof = useAsOf();
  if (!data || data.empty) return null;
  // As-of ranking for the selected period (deduplicate by bank_id to take latest per bank).
  const rawRanking = asof.filter(data?.scores || []);
  const latestByBank = new Map<string, any>();
  rawRanking.forEach((r: any) => {
    if (!r.bank_id) return;
    if (!latestByBank.has(r.bank_id) || (r.period || "") > (latestByBank.get(r.bank_id).period || "")) {
      latestByBank.set(r.bank_id, r);
    }
  });
  const ranking = Array.from(latestByBank.values())
    .sort((a, b) => (b.final_risk_score || 0) - (a.final_risk_score || 0));
  const lv: Record<string, number> = {};
  ranking.forEach((r) => { lv[r.risk_level] = (lv[r.risk_level] || 0) + 1; });
  const avg = ranking.length
    ? ranking.reduce((a, r) => a + (r.final_risk_score || 0), 0) / ranking.length : 0;

  // Trung bình lĩnh vực: chỉ tính đơn vị ĐÃ đánh giá (điểm khác null). Đơn vị thiếu
  // dữ liệu có điểm null -> bỏ qua, không tính là 0 để khỏi kéo tụt điểm hệ thống.
  const dmean = (col: string) => {
    const vals = ranking.map((r) => r[col]).filter((v) => v != null) as number[];
    return vals.length ? vals.reduce((a, v) => a + v, 0) / vals.length : 0;
  };
  const domainData = [
    { name: "Tín dụng", value: dmean("credit_risk_score") },
    { name: "Thanh khoản", value: dmean("liquidity_risk_score") },
    { name: "Gian lận (proxy)", value: dmean("fraud_risk_proxy_score") },
    { name: "Đổ vỡ (proxy)", value: dmean("failure_risk_proxy_score") },
  ];
  const DOM_COLORS: Record<string, string> = {
    "Tín dụng": "#2f80ed", "Thanh khoản": "#0a9396",
    "Gian lận (proxy)": "#e0701a", "Đổ vỡ (proxy)": "#c62828",
  };

  const hm = data?.heatmap;

  const bankRanking = ranking.filter((r) => !r.bank_id?.startsWith("CTTC_"));
  const top12Banks = bankRanking.length >= 12 ? bankRanking.slice(0, 12) : ranking.slice(0, 12);

  return (
    <>
      <div className="grid kpi">
        <Kpi label="CRITICAL" value={fmtInt(lv.CRITICAL || 0)} color="#c62828" />
        <Kpi label="HIGH" value={fmtInt(lv.HIGH || 0)} color="#e0701a" />
        <Kpi label="MEDIUM" value={fmtInt(lv.MEDIUM || 0)} color="#c98a00" />
        <Kpi label="LOW" value={fmtInt(lv.LOW || 0)} color="#2e7d32" />
        <Kpi label="Điểm rủi ro TB" value={fmt(avg)} meta={`kỳ ${asof.period}${asof.isLatest ? " (gần nhất)" : ""}`} color="#0a2540" />
      </div>

      <Card title="Heatmap rủi ro: ngân hàng × kỳ" sub="final_risk_score 0–100" className="" >
        {hm?.banks && hm.banks.length > 0 ? (
          <>
            <div style={{ overflowX: "auto" }}>
              <div style={{ display: "grid", gridTemplateColumns: `140px repeat(${hm.periods?.length || 0}, minmax(34px, 1fr))`, gap: 2, minWidth: 600 }}>
                <div />
                {(hm.periods || []).map((p) => (
                  <div key={p} style={{ fontSize: 10, color: "#5b6677", textAlign: "center", paddingBottom: 4, transform: "rotate(0deg)" }}>{p}</div>
                ))}
                {hm.banks.map((b, ri) => (
                  <RowCells key={b} bank={b} row={hm.z?.[ri] || []} />
                ))}
              </div>
            </div>
            <div className="heat-legend"><span>An toàn</span><span className="scale" /><span>Rủi ro cao</span></div>
          </>
        ) : <div className="muted">Không có dữ liệu heatmap.</div>}
      </Card>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Rủi ro theo lĩnh vực" sub="điểm TB toàn hệ thống">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={domainData} margin={{ left: 0, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" fontSize={11} />
              <YAxis domain={[0, 100]} fontSize={11} />
              <Tooltip formatter={(v: any) => fmt(v)} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {domainData.map((d, i) => <Cell key={i} fill={DOM_COLORS[d.name] || "#2f80ed"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Top 12 ngân hàng điểm rủi ro cao nhất" sub="rule_violation + anomaly + trend">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={top12Banks} layout="vertical" margin={{ left: 30, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} fontSize={11} />
              <YAxis type="category" dataKey="bank_id" width={90} fontSize={10} />
              <Tooltip formatter={(v: any) => fmt(v)} />
              <Bar dataKey="final_risk_score" radius={[0, 4, 4, 0]}>
                {top12Banks.map((d, i) => <Cell key={i} fill={heatColor(d.final_risk_score)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Xếp hạng ngân hàng theo rủi ro" sub={`kỳ ${asof.period}`} className="pad0">
        <DataTable maxHeight={560}
          cols={[
            { key: "rank", label: "#", render: (_r) => "", width: 0 },
            { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
            { key: "period", label: "Kỳ" },
            { key: "final_risk_score", label: "Điểm", num: true, render: (r) => <ScorePill score={r.final_risk_score} /> },
            { key: "risk_level", label: "Mức", render: (r) => <Badge level={r.risk_level} /> },
            { key: "rule_violation_score", label: "Rule", num: true, render: (r) => fmt(r.rule_violation_score, 0) },
            { key: "anomaly_score_norm", label: "Anomaly", num: true, render: (r) => fmt(r.anomaly_score_norm, 0) },
            { key: "trend_risk_score", label: "Xu hướng", num: true, render: (r) => fmt(r.trend_risk_score, 0) },
            { key: "credit_risk_score", label: "Tín dụng", num: true, render: (r) => fmt(r.credit_risk_score, 0) },
            { key: "liquidity_risk_score", label: "TK", num: true, render: (r) => fmt(r.liquidity_risk_score, 0) },
            { key: "cluster_risk_label", label: "Cụm", render: (r) => <span className="muted">{r.cluster_risk_label || "—"}</span> },
          ]}
          rows={ranking} />
      </Card>
    </>
  );
}

function RowCells({ bank, row }: { bank: string; row: (number | null)[] }) {
  return (
    <>
      <div style={{ fontSize: 11, color: "#1a2433", display: "flex", alignItems: "center", fontWeight: 500, paddingRight: 6 }}>{bank}</div>
      {row.map((v, ci) => (
        <div key={ci} className="hm-cell"
          title={`${bank}: ${v === null ? "—" : fmt(v)}`}
          style={{ background: heatColor(v), minHeight: 22 }} />
      ))}
    </>
  );
}
