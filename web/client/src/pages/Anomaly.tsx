import { useMemo, useState } from "react";
import axios from "axios";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAsOf } from "../components/PeriodPicker";
import { Card, DataTable, Kpi } from "../components/ui";
import { fmt, fmtInt } from "../format";
import { useStore } from "../store";

const FB_LABELS = ["confirmed_anomaly", "false_positive", "needs_more_data", "accepted_risk", "escalated_to_audit"];

export default function Anomaly() {
  const { data, showToast } = useStore();
  const asof = useAsOf();
  const [sel, setSel] = useState<any | null>(null);
  const [label, setLabel] = useState(FB_LABELS[0]);
  const [note, setNote] = useState("");
  if (!data || data.empty) return null;

  // Anomalies as of the selected period (using flexible asof filter with deduplication per bank).
  const rawAnomalies = asof.filter(data?.anomalies || []);
  const latestByBank = new Map<string, any>();
  rawAnomalies.forEach((a: any) => {
    if (!a.bank_id) return;
    if (!latestByBank.has(a.bank_id) || (a.period || "") > (latestByBank.get(a.bank_id).period || "")) {
      latestByBank.set(a.bank_id, a);
    }
  });
  const an = Array.from(latestByBank.values()).sort((a, b) => (b.anomaly_score ?? 0) - (a.anomaly_score ?? 0));
  const flagged = an.filter((a) => a.anomaly_label === 1);

  // Histogram of anomaly_score in 20 bins.
  const hist = useMemo(() => {
    const bins = Array.from({ length: 20 }, (_, i) => ({ x: i * 5, n: 0 }));
    an.forEach((a) => {
      const s = a.anomaly_score ?? 0;
      const idx = Math.min(19, Math.floor(s / 5));
      bins[idx].n++;
    });
    return bins;
  }, [an]);

  const submitFeedback = async () => {
    if (!sel) return;
    try {
      await axios.post("/api/feedback", {
        bank_id: sel.bank_id, period: sel.period, source: "anomaly", label, note,
      });
      showToast("Đã lưu phản hồi kiểm toán viên.");
      setNote("");
    } catch (e: any) {
      showToast(e?.response?.data?.error || "Lưu phản hồi thất bại", true);
    }
  };

  return (
    <>
      <div className="grid kpi">
        <Kpi label="NH bất thường (kỳ chọn)" value={fmtInt(flagged.length)} meta={`kỳ ${asof.period}`} color="#e0701a" />
        <Kpi label="Tỷ lệ bất thường" value={`${fmt(an.length ? flagged.length / an.length * 100 : 0)}%`} color="#c98a00" />
        <Kpi label="Số feature dùng" value={fmtInt((data?.anomaly_features || []).length || 73)} color="#2f80ed" />
        <Kpi label="Thuật toán" value="Isolation Forest" meta={data?.summary?.cluster_k ? "seed cố định" : ""} color="#0a2540" />
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Phân bố anomaly score" sub="0–100, cao = bất thường hơn">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={hist}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="x" fontSize={11} />
              <YAxis fontSize={11} allowDecimals={false} />
              <Tooltip labelFormatter={(v) => `score ~ ${v}`} />
              <Bar dataKey="n" radius={[3, 3, 0, 0]}>
                {hist.map((d, i) => <Cell key={i} fill={d.x >= 60 ? "#c62828" : d.x >= 40 ? "#e0701a" : "#2f80ed"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Phản hồi kiểm toán viên" sub="iterative improvement loop">
          <div style={{ display: "grid", gap: 10 }}>
            <select className="topbar" style={{ padding: 8, border: "1px solid var(--line)", borderRadius: 8 }}
              value={sel ? `${sel.bank_id}|${sel.period}` : ""}
              onChange={(e) => {
                const [b, p] = e.target.value.split("|");
                setSel(flagged.find((a) => a.bank_id === b && a.period === p) || null);
              }}>
              <option value="">— Chọn bank-period bất thường —</option>
              {flagged.slice(0, 60).map((a, i) => (
                <option key={i} value={`${a.bank_id}|${a.period}`}>{a.bank_id} · {a.period} (score {fmt(a.anomaly_score, 0)})</option>
              ))}
            </select>
            <select style={{ padding: 8, border: "1px solid var(--line)", borderRadius: 8 }}
              value={label} onChange={(e) => setLabel(e.target.value)}>
              {FB_LABELS.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
            <input placeholder="Ghi chú..." value={note} onChange={(e) => setNote(e.target.value)}
              style={{ padding: 9, border: "1px solid var(--line)", borderRadius: 8, fontFamily: "var(--font)" }} />
            <button className="btn primary" disabled={!sel} onClick={submitFeedback}>Lưu phản hồi</button>
          </div>
          <p className="help">Phản hồi được lưu vào <code>data/feedback/feedback.csv</code> để hệ thống thống kê false-positive và đề xuất hiệu chỉnh ở trang Hiệu năng.</p>
        </Card>
      </div>

      <Card title="Top bất thường & giải thích" sub="feature deviation (z-score)" className="pad0">
        <DataTable maxHeight={460}
          cols={[
            { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
            { key: "period", label: "Kỳ" },
            { key: "anomaly_score", label: "Score", num: true, render: (r) => fmt(r.anomaly_score, 1) },
            { key: "anomaly_label", label: "Cờ", render: (r) => r.anomaly_label === 1 ? <span className="badge HIGH">bất thường</span> : <span className="muted">bình thường</span> },
            { key: "top_features", label: "Chỉ tiêu đóng góp chính", render: (r) => <span style={{ fontSize: 12 }}>{r.top_features}</span> },
          ]}
          rows={an} />
      </Card>
    </>
  );
}
