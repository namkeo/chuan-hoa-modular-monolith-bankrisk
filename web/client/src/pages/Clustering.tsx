import { CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { Card, DataTable, Empty, Kpi } from "../components/ui";
import { fmt, fmtInt } from "../format";
import { useStore } from "../store";

const CLUSTER_COLORS = ["#2f80ed", "#e0701a", "#2e7d32", "#6b46c1", "#c62828", "#0a9396", "#c98a00", "#d6336c"];

export default function Clustering() {
  const { data } = useStore();
  if (!data || data.empty) return null;
  const cl = data.clusters;
  if (!cl || cl.k === 0) return <Empty text="Không đủ dữ liệu để phân cụm." />;

  const sil = cl.metrics?.[String(cl.k)]?.silhouette;
  const kMetrics = Object.entries(cl.metrics || {}).map(([k, m]) => ({
    k: Number(k), silhouette: m.silhouette, davies_bouldin: m.davies_bouldin,
  })).sort((a, b) => a.k - b.k);

  // Group projection points by cluster for coloured scatter series.
  const byCluster: Record<number, any[]> = {};
  (cl.projection || []).forEach((p) => {
    (byCluster[p.cluster_id] = byCluster[p.cluster_id] || []).push(p);
  });

  return (
    <>
      <div className="grid kpi">
        <Kpi label="Số cụm (k)" value={fmtInt(cl.k)} color="#6b46c1" />
        <Kpi label="Silhouette" value={fmt(sil, 3)} meta="cao = cụm tách tốt" color="#2f80ed" />
        <Kpi label="Số ngân hàng" value={fmtInt(data.summary.n_banks)} color="#0a2540" />
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Trực quan hóa cụm (PCA 2D)" sub="chỉ để minh họa">
          {cl.projection?.length ? (
            <ResponsiveContainer width="100%" height={340}>
              <ScatterChart margin={{ left: 0, right: 16, top: 10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="x" name="PC1" fontSize={11} />
                <YAxis type="number" dataKey="y" name="PC2" fontSize={11} />
                <ZAxis range={[60, 60]} />
                <Tooltip cursor={{ strokeDasharray: "3 3" }}
                  formatter={(v: any, n: any) => [fmt(v, 2), n]}
                  labelFormatter={() => ""}
                  content={({ payload }) => payload?.[0] ? (
                    <div className="card" style={{ padding: 8, fontSize: 12 }}>
                      <b>{payload[0].payload.bank_id}</b><br />Cụm {payload[0].payload.cluster_id}
                    </div>) : null} />
                <Legend />
                {Object.entries(byCluster).map(([cid, pts]) => (
                  <Scatter key={cid} name={`Cụm ${cid}`} data={pts} fill={CLUSTER_COLORS[Number(cid) % CLUSTER_COLORS.length]} />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          ) : <Empty text="Không có projection." />}
        </Card>

        <Card title="Chỉ số chọn k" sub="silhouette ↑ tốt · Davies-Bouldin ↓ tốt">
          <ResponsiveContainer width="100%" height={340}>
            <LineChart data={kMetrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="k" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip formatter={(v: any) => fmt(v, 3)} />
              <Legend />
              <Line type="monotone" dataKey="silhouette" stroke="#2f80ed" strokeWidth={2} />
              <Line type="monotone" dataKey="davies_bouldin" stroke="#e0701a" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Hồ sơ cụm rủi ro" sub="điểm rủi ro & nhãn mô tả" className="pad0">
        <DataTable maxHeight={300}
          cols={[
            { key: "cluster_id", label: "Cụm", render: (r) => (
              <span className="row-flex"><span className="dot" style={{ background: CLUSTER_COLORS[r.cluster_id % CLUSTER_COLORS.length] }} /> {r.cluster_id}</span>) },
            { key: "n_banks", label: "Số NH", num: true },
            { key: "cluster_risk_score", label: "Điểm rủi ro cụm", num: true, render: (r) => fmt(r.cluster_risk_score, 1) },
            { key: "cluster_risk_label", label: "Đặc điểm", render: (r) => <span className="b">{r.cluster_risk_label}</span> },
          ]}
          rows={cl.profiles} />
      </Card>

      <Card title="Ngân hàng theo cụm" className="pad0">
        <DataTable maxHeight={360}
          cols={[
            { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
            { key: "cluster_id", label: "Cụm", render: (r) => (
              <span className="row-flex"><span className="dot" style={{ background: CLUSTER_COLORS[r.cluster_id % CLUSTER_COLORS.length] }} /> {r.cluster_id}</span>) },
            { key: "cluster_risk_label", label: "Đặc điểm cụm" },
            { key: "cluster_risk_score", label: "Điểm rủi ro", num: true, render: (r) => fmt(r.cluster_risk_score, 1) },
          ]}
          rows={cl.assignment} />
      </Card>
    </>
  );
}
