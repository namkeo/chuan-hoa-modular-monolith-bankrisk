import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { Card, DataTable, Disclaimer, Kpi, Loader } from "../components/ui";
import { fmt } from "../format";
import { useStore } from "../store";

type Model = "isolation_forest" | "kmeans";

export default function FineTuning() {
  const { freq, meta, setMeta, showToast, refresh } = useStore();
  const [model, setModel] = useState<Model>("isolation_forest");
  const [criterion, setCriterion] = useState("auto");
  const [running, setRunning] = useState(false);
  const [applying, setApplying] = useState(false);
  const [result, setResult] = useState<any | null>(null);

  const tuned = meta?.tuned;

  const run = async () => {
    setRunning(true); setResult(null);
    showToast(`Đang tinh chỉnh ${model} (${freq})...`);
    try {
      const r = await api.tune(freq, model, model === "kmeans" ? "silhouette" : criterion);
      if (!r.ok) throw new Error(r.error || "lỗi");
      setResult(r);
      showToast("Đã tinh chỉnh xong.");
    } catch (e: any) {
      showToast(e?.response?.data?.error || e.message || "Tinh chỉnh thất bại", true);
    } finally { setRunning(false); }
  };

  const apply = async () => {
    if (!result?.best) return;
    setApplying(true);
    showToast("Đang áp dụng tham số & chạy lại pipeline...");
    try {
      const body = model === "kmeans" ? { kmeans: result.best } : { isolation_forest: result.best };
      await api.tuneApply(body);
      const m = await api.meta();
      if (m) setMeta(m);
      showToast("Đã áp dụng. Đang tải lại kết quả...");
      await refresh(false);
    } catch (e: any) {
      showToast(e?.response?.data?.error || "Áp dụng thất bại", true);
    } finally { setApplying(false); }
  };

  const reset = async () => {
    setApplying(true);
    showToast("Khôi phục tham số mặc định & chạy lại...");
    try {
      await api.tuneReset();
      await refresh(false);
      showToast("Đã khôi phục mặc định.");
    } catch (e: any) {
      showToast("Khôi phục thất bại", true);
    } finally { setApplying(false); }
  };

  const lb = result?.leaderboard || [];

  return (
    <>
      <Disclaimer text="Tinh chỉnh siêu tham số (fine-tuning) bằng grid-search cho mô hình học máy không giám sát. Isolation Forest tối ưu theo phản hồi KTV (nếu có nhãn) hoặc độ ổn định; K-means tối ưu theo silhouette. Tham số mới chỉ áp dụng khi bạn bấm 'Áp dụng' và có thể khôi phục mặc định." />

      <div className="grid kpi">
        <Kpi label="Trạng thái tinh chỉnh" value={tuned?.applied ? "ĐANG ÁP DỤNG" : "Mặc định"}
          meta={tuned?.applied && tuned?.tuned_at ? tuned.tuned_at : "config/model_config.yaml"}
          color={tuned?.applied ? "#2e7d32" : "#0a2540"} />
        <Kpi label="Isolation Forest (đang dùng)"
          value={tuned?.applied && tuned?.isolation_forest ? `c=${tuned.isolation_forest.contamination}` : "mặc định"}
          meta={tuned?.isolation_forest ? `n=${tuned.isolation_forest.n_estimators}, ms=${tuned.isolation_forest.max_samples}` : ""}
          color="#e0701a" />
        <Kpi label="K-means (đang dùng)"
          value={tuned?.applied && tuned?.kmeans ? `k=${tuned.kmeans.manual_k}` : "tự chọn"}
          color="#6b46c1" />
      </div>

      <Card title="Cấu hình tinh chỉnh" style={{ marginTop: 16 }}>
        <div className="row-flex">
          <div>
            <label className="help">Mô hình</label><br />
            <select value={model} onChange={(e) => setModel(e.target.value as Model)}
              style={{ padding: 8, border: "1px solid var(--line)", borderRadius: 8, minWidth: 200 }}>
              <option value="isolation_forest">Isolation Forest (bất thường)</option>
              <option value="kmeans">K-means (phân cụm)</option>
            </select>
          </div>
          {model === "isolation_forest" && (
            <div>
              <label className="help">Tiêu chí</label><br />
              <select value={criterion} onChange={(e) => setCriterion(e.target.value)}
                style={{ padding: 8, border: "1px solid var(--line)", borderRadius: 8, minWidth: 180 }}>
                <option value="auto">Tự động (feedback nếu có)</option>
                <option value="feedback">Theo phản hồi KTV (F1)</option>
                <option value="stability">Độ ổn định giữa seed</option>
                <option value="separation">Độ tách điểm bất thường</option>
              </select>
            </div>
          )}
          <div style={{ alignSelf: "flex-end" }}>
            <button className="btn primary" disabled={running || applying} onClick={run}>
              {running ? "Đang chạy grid-search..." : "▶ Chạy tinh chỉnh"}
            </button>
          </div>
          <div style={{ alignSelf: "flex-end" }}>
            <button className="btn" disabled={applying} onClick={reset}>↺ Khôi phục mặc định</button>
          </div>
        </div>
        <p className="help">Tần suất: <b>{freq}</b>. Grid-search có thể mất ~10–30s.</p>
      </Card>

      {(running || applying) && <Loader text={applying ? "Đang áp dụng & chạy lại pipeline..." : "Đang grid-search siêu tham số..."} />}

      {result && !running && (
        <>
          <Card title="Kết quả tinh chỉnh" sub={result.note} style={{ marginTop: 16 }}>
            <div className="row-flex" style={{ justifyContent: "space-between" }}>
              <div>
                <div className="help">Cấu hình tốt nhất (đề xuất)</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#2e7d32", marginTop: 4 }}>
                  {Object.entries(result.best).map(([k, v]) => `${k}=${v}`).join(" · ")}
                </div>
                <div className="help" style={{ marginTop: 4 }}>
                  Hiện tại: {Object.entries(result.current).map(([k, v]) => `${k}=${v}`).join(" · ")} · mẫu: {result.n_samples}
                </div>
              </div>
              <button className="btn primary" disabled={applying} onClick={apply}>✓ Áp dụng cấu hình này</button>
            </div>
          </Card>

          {model === "kmeans" ? (
            <Card title="Silhouette theo k" sub="cao = cụm tách tốt" style={{ marginTop: 16 }}>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={[...lb].sort((a, b) => a.k - b.k)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="k" fontSize={11} />
                  <YAxis fontSize={11} />
                  <Tooltip formatter={(v: any) => fmt(v, 3)} />
                  <Line type="monotone" dataKey="silhouette" stroke="#2f80ed" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          ) : (
            <Card title="Điểm tiêu chí theo cấu hình" sub="top theo criterion_score" style={{ marginTop: 16 }}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={lb.slice(0, 12).map((r: any) => ({
                  name: `c${r.contamination}/n${r.n_estimators}/${r.max_samples}`,
                  score: r.criterion_score, rate: r.anomaly_rate_pct,
                }))} margin={{ left: 0, right: 8, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" fontSize={8} angle={-40} textAnchor="end" height={70} interval={0} />
                  <YAxis fontSize={11} />
                  <Tooltip />
                  <Bar dataKey="score" radius={[3, 3, 0, 0]}>
                    {lb.slice(0, 12).map((_: any, i: number) => <Cell key={i} fill={i === 0 ? "#2e7d32" : "#2f80ed"} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          <Card title="Bảng xếp hạng cấu hình (leaderboard)" className="pad0" style={{ marginTop: 16 }}>
            <DataTable maxHeight={400}
              cols={model === "kmeans" ? [
                { key: "k", label: "k", num: true },
                { key: "silhouette", label: "Silhouette", num: true, render: (r) => fmt(r.silhouette, 3) },
                { key: "davies_bouldin", label: "Davies-Bouldin", num: true, render: (r) => fmt(r.davies_bouldin, 3) },
                { key: "calinski_harabasz", label: "Calinski-Harabasz", num: true, render: (r) => fmt(r.calinski_harabasz, 0) },
                { key: "criterion_score", label: "Điểm tiêu chí", num: true, render: (r) => fmt(r.criterion_score, 3) },
              ] : [
                { key: "contamination", label: "contamination", num: true },
                { key: "n_estimators", label: "n_estimators", num: true },
                { key: "max_samples", label: "max_samples" },
                { key: "anomaly_rate_pct", label: "Anomaly %", num: true, render: (r) => fmt(r.anomaly_rate_pct, 1) },
                { key: "stability", label: "Ổn định", num: true, render: (r) => fmt(r.stability, 3) },
                { key: "separation", label: "Tách điểm", num: true, render: (r) => fmt(r.separation, 2) },
                { key: "feedback_f1", label: "Feedback F1", num: true, render: (r) => r.feedback_f1 != null ? fmt(r.feedback_f1, 3) : "—" },
                { key: "criterion_score", label: "Điểm tiêu chí", num: true, render: (r) => fmt(r.criterion_score, 3) },
              ]}
              rows={lb} />
          </Card>
        </>
      )}
    </>
  );
}
