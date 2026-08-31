import { useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAsOf } from "../components/PeriodPicker";
import { Badge, Card, DataTable, Disclaimer, Empty, Kpi } from "../components/ui";
import { fmt, fmtInt } from "../format";
import { useStore } from "../store";

const EWS_COLOR: Record<string, string> = {
  NORMAL: "#2e7d32", WATCH: "#c98a00", WARNING: "#e0701a", ALARM: "#c62828",
};
const SIG_LABEL: Record<string, string> = {
  sig_proximity: "Tiệm cận ngưỡng", sig_trend: "Đà xấu đi",
  sig_acceleration: "Gia tốc", sig_volatility: "Biến động",
  sig_breach_streak: "Chuỗi vi phạm", sig_anomaly_persistence: "Bất thường lặp lại",
};

export default function EarlyWarning() {
  const { data, freq } = useStore();
  const asof = useAsOf();
  const [selBank, setSelBank] = useState<string>("");
  if (!data || data.empty) return null;
  const ews = data.ews;
  if (!ews || !ews.latest?.length) return <Empty text="Chưa có dữ liệu EWS cho tần suất này." />;

  // EWS rows as of the selected period (fall back to the latest-snapshot rows).
  const asOfRows = (ews.table || []).filter((r: any) => r.period === asof.period);
  const ewsRows: any[] = asOfRows.length ? asOfRows : ews.latest;
  const lc: Record<string, number> = {};
  ewsRows.forEach((r: any) => { lc[r.ews_level] = (lc[r.ews_level] || 0) + 1; });
  const sys = ews.system_now || {};
  const sysSeries = ews.system || [];
  const traj = ews.trajectory;
  const sortedRows = [...ewsRows].sort((a, b) => (b.ews_score || 0) - (a.ews_score || 0));
  const focusBank = selBank || sortedRows[0]?.bank_id;
  const trajData = traj.periods.map((p, i) => ({ period: p, score: traj.data[focusBank]?.[i] ?? null }));
  const selRow = ewsRows.find((r) => r.bank_id === focusBank);

  const sigBreakdown = selRow ? Object.keys(SIG_LABEL).map((k) => ({
    name: SIG_LABEL[k], value: selRow[k] ?? 0,
  })) : [];

  return (
    <>
      <Disclaimer text={`Hệ thống cảnh báo sớm (EWS) — tần suất ${freq}. Dùng chỉ báo DẪN DẮT (khoảng cách tới ngưỡng, đà xấu đi, dự phóng chạm ngưỡng) để cảnh báo TRƯỚC khi thành vi phạm. Là công cụ hỗ trợ, không khẳng định vi phạm/đổ vỡ.`} />

      <div className="grid kpi">
        <Kpi label="Trạng thái hệ thống" value={<Badge level={sys.system_level || "NORMAL"} />}
          meta={`${sys.period || ""} · ${fmt(sys.share_warning_plus)}% NH ở WARNING+`} color={EWS_COLOR[sys.system_level] || "#0a2540"} />
        <Kpi label="Báo động (ALARM)" value={fmtInt(lc.ALARM || 0)} color="#c62828" />
        <Kpi label="Cảnh báo (WARNING)" value={fmtInt(lc.WARNING || 0)} color="#e0701a" />
        <Kpi label="Theo dõi (WATCH)" value={fmtInt(lc.WATCH || 0)} color="#c98a00" />
        <Kpi label="Điểm EWS hệ thống" value={fmt(sys.mean_ews)} meta={sys.mean_ews_mom != null ? `MoM ${sys.mean_ews_mom > 0 ? "+" : ""}${fmt(sys.mean_ews_mom)}` : ""} color="#2f80ed" />
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Chỉ số EWS hệ thống theo kỳ" sub="% ngân hàng ở mức Cảnh báo trở lên">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={sysSeries}>
              <defs>
                <linearGradient id="ewsg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#c62828" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#c62828" stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" fontSize={10} />
              <YAxis fontSize={11} />
              <Tooltip formatter={(v: any, n: any) => [fmt(v), n === "share_warning_plus" ? "% WARNING+" : "Điểm TB"]} />
              <Legend />
              <Area type="monotone" dataKey="share_warning_plus" name="% WARNING+" stroke="#c62828" fill="url(#ewsg)" strokeWidth={2} />
              <Line type="monotone" dataKey="mean_ews" name="Điểm EWS TB" stroke="#2f80ed" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Phân bố mức EWS (kỳ gần nhất)" sub="traffic-light">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={["NORMAL", "WATCH", "WARNING", "ALARM"].map((l) => ({ level: l, n: lc[l] || 0 }))}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="level" fontSize={11} />
              <YAxis fontSize={11} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="n" radius={[4, 4, 0, 0]}>
                {["NORMAL", "WATCH", "WARNING", "ALARM"].map((l, i) => <Cell key={i} fill={EWS_COLOR[l]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {ews.emerging?.length > 0 && (
        <Card title="⚡ Rủi ro mới nổi (escalating watchlist)" sub="ngân hàng có EWS tăng nhanh / bị nâng mức" className="pad0" style={{ marginTop: 16 }}>
          <DataTable maxHeight={260}
            cols={[
              { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
              { key: "period", label: "Kỳ" },
              { key: "ews_score", label: "Điểm EWS", num: true, render: (r) => fmt(r.ews_score, 1) },
              { key: "ews_level", label: "Mức", render: (r) => <Badge level={r.ews_level} /> },
              { key: "score_delta", label: "Δ vs kỳ trước", num: true, render: (r) => <span style={{ color: r.score_delta > 0 ? "#c62828" : "#2e7d32", fontWeight: 600 }}>{r.score_delta > 0 ? "+" : ""}{fmt(r.score_delta, 1)}</span> },
              { key: "projected_periods_to_breach", label: "Dự phóng chạm ngưỡng", num: true, render: (r) => r.projected_periods_to_breach != null ? `~${fmt(r.projected_periods_to_breach, 1)} kỳ (${r.projected_breach_metric})` : "—" },
              { key: "drivers", label: "Yếu tố chính", render: (r) => <span style={{ fontSize: 12 }}>{r.drivers}</span> },
            ]}
            rows={ews.emerging} />
        </Card>
      )}

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Quỹ đạo điểm EWS theo ngân hàng">
          <select value={focusBank} onChange={(e) => setSelBank(e.target.value)}
            style={{ padding: 8, border: "1px solid var(--line)", borderRadius: 8, marginBottom: 12, minWidth: 180 }}>
            {sortedRows.map((r) => <option key={r.bank_id} value={r.bank_id}>{r.bank_id} — {r.ews_label}</option>)}
          </select>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trajData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" fontSize={10} />
              <YAxis domain={[0, 100]} fontSize={11} />
              <Tooltip formatter={(v: any) => fmt(v, 1)} />
              <ReferenceLine y={75} stroke="#c62828" strokeDasharray="4 4" label={{ value: "ALARM", fontSize: 10, fill: "#c62828" }} />
              <ReferenceLine y={50} stroke="#e0701a" strokeDasharray="4 4" label={{ value: "WARNING", fontSize: 10, fill: "#e0701a" }} />
              <Line type="monotone" dataKey="score" stroke="#2f80ed" strokeWidth={2.5} dot={{ r: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title={`Phân rã tín hiệu EWS — ${focusBank}`} sub={selRow?.ews_label}>
          {selRow ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={sigBreakdown} layout="vertical" margin={{ left: 40, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} fontSize={11} />
                <YAxis type="category" dataKey="name" width={120} fontSize={10} />
                <Tooltip formatter={(v: any) => fmt(v, 1)} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {sigBreakdown.map((d, i) => <Cell key={i} fill={d.value >= 60 ? "#c62828" : d.value >= 30 ? "#e0701a" : "#2f80ed"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty />}
          {selRow?.projected_periods_to_breach != null && (
            <p className="help">⏳ Dự phóng chạm ngưỡng <b>{selRow.projected_breach_metric}</b> sau ~<b>{fmt(selRow.projected_periods_to_breach, 1)}</b> kỳ.</p>
          )}
        </Card>
      </div>

      <Card title="Bảng cảnh báo sớm chi tiết theo ngân hàng" sub="kỳ gần nhất" className="pad0" style={{ marginTop: 16 }}>
        <DataTable maxHeight={500}
          cols={[
            { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
            { key: "period", label: "Kỳ" },
            { key: "ews_score", label: "Điểm EWS", num: true, render: (r) => <span className="score-pill" style={{ background: EWS_COLOR[r.ews_level] + "22", color: EWS_COLOR[r.ews_level] }}>{fmt(r.ews_score, 0)}</span> },
            { key: "ews_level", label: "Mức", render: (r) => <Badge level={r.ews_level} /> },
            { key: "sig_proximity", label: "Tiệm cận", num: true, render: (r) => fmt(r.sig_proximity, 0) },
            { key: "sig_trend", label: "Đà xấu", num: true, render: (r) => fmt(r.sig_trend, 0) },
            { key: "n_breached", label: "CT vượt ngưỡng", num: true },
            { key: "projected_periods_to_breach", label: "Dự phóng (kỳ)", num: true, render: (r) => r.projected_periods_to_breach != null ? fmt(r.projected_periods_to_breach, 1) : "—" },
            { key: "risk_domains", label: "Lĩnh vực" },
          ]}
          rows={sortedRows} />
      </Card>
    </>
  );
}
