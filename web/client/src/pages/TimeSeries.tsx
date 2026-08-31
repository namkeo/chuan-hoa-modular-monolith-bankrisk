import { useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Card, DataTable, Empty } from "../components/ui";
import { fmt } from "../format";
import { useStore } from "../store";

const METRIC_LABEL: Record<string, string> = {
  npl_ratio: "Tỷ lệ nợ xấu (NPL)", ldr: "LDR", car_solo: "CAR riêng lẻ",
  roa: "ROA", liquidity_reserve_ratio: "Dự trữ thanh khoản",
  group2_ratio: "Nợ nhóm 2", st_funding_for_mlt_loans: "Vốn NH cho vay TDH",
  credit_growth_yoy: "Tăng trưởng tín dụng",
};

export default function TimeSeries() {
  const { data } = useStore();
  const [bank, setBank] = useState<string>("");
  const [metric, setMetric] = useState<string>("npl_ratio");
  if (!data || data.empty) return null;

  const banks = data.banks || Object.keys(data.series?.data || {});
  const curBank = bank || banks[0] || "";
  const series = data.series || { metrics: [], data: {} };
  const metrics = (series.metrics || []).filter((m) => METRIC_LABEL[m]);
  const curMetric = metrics.includes(metric) ? metric : (metrics[0] || "npl_ratio");
  const bd = (series.data || {})[curBank];
  const chartData = bd ? (bd.periods || []).map((p: string, i: number) => ({ period: p, value: bd[curMetric]?.[i] ?? null })) : [];

  const hrp = data.high_risk_periods || [];
  const stress = data.systemic_stress || [];

  return (
    <>
      <Card>
        <div className="row-flex">
          <div>
            <label className="help">Ngân hàng</label><br />
            <select value={curBank} onChange={(e) => setBank(e.target.value)}
              style={{ padding: 8, border: "1px solid var(--line)", borderRadius: 8, minWidth: 180 }}>
              {banks.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <label className="help">Chỉ tiêu</label><br />
            <select value={curMetric} onChange={(e) => setMetric(e.target.value)}
              style={{ padding: 8, border: "1px solid var(--line)", borderRadius: 8, minWidth: 220 }}>
              {metrics.map((m) => <option key={m} value={m}>{METRIC_LABEL[m] || m}</option>)}
            </select>
          </div>
        </div>
        <div style={{ marginTop: 16 }}>
          {chartData.length ? (
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" fontSize={11} />
                <YAxis fontSize={11} />
                <Tooltip formatter={(v: any) => fmt(v, 2)} />
                <Line type="monotone" dataKey="value" name={METRIC_LABEL[curMetric] || curMetric}
                  stroke="#2f80ed" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : <Empty text="Không có chuỗi cho lựa chọn này." />}
        </div>
      </Card>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Chỉ số căng thẳng hệ thống" sub="systemic stress index theo kỳ">
          {stress.length ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={stress}>
                <defs>
                  <linearGradient id="stress" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#c62828" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#c62828" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" fontSize={11} />
                <YAxis fontSize={11} />
                <Tooltip formatter={(v: any) => fmt(v, 3)} />
                <Area type="monotone" dataKey="systemic_stress_index" stroke="#c62828" fill="url(#stress)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </Card>

        <Card title="Điểm rủi ro theo kỳ (toàn hệ thống)" sub="đỏ = kỳ rủi ro cao">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={hrp}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="period" fontSize={11} />
              <YAxis domain={[0, 100]} fontSize={11} />
              <Tooltip formatter={(v: any) => fmt(v, 1)} />
              <Bar dataKey="period_risk_score" radius={[3, 3, 0, 0]}>
                {hrp.map((d, i) => <Cell key={i} fill={d.is_high_risk ? "#c62828" : "#90a4ae"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Giai đoạn rủi ro cao" sub="lý do & trọng tâm kiểm toán" className="pad0">
        <DataTable maxHeight={380}
          cols={[
            { key: "period", label: "Kỳ", render: (r) => <span className="b">{r.period}</span> },
            { key: "period_risk_score", label: "Điểm", num: true, render: (r) => fmt(r.period_risk_score, 0) },
            { key: "is_high_risk", label: "Cao?", render: (r) => r.is_high_risk ? <Badge level="CRITICAL" /> : <span className="muted">—</span> },
            { key: "n_critical_banks", label: "NH CRITICAL", num: true },
            { key: "risk_domains", label: "Lĩnh vực" },
            { key: "reason", label: "Lý do", render: (r) => <span style={{ fontSize: 12 }}>{r.reason}</span> },
            { key: "recommended_audit_focus", label: "Trọng tâm kiểm toán", render: (r) => <span style={{ fontSize: 12 }} className="muted">{r.recommended_audit_focus}</span> },
          ]}
          rows={hrp.filter((p) => p.is_high_risk)} empty="Không có kỳ rủi ro cao." />
      </Card>
    </>
  );
}
