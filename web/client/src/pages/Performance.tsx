import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { Card, DataTable, Empty, Kpi, Loader } from "../components/ui";
import { fmt } from "../format";

export default function Performance() {
  const [perf, setPerf] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.performance().then(setPerf).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;
  if (!perf) return <Empty />;
  const log: any[] = perf.log || [];
  const last = log[log.length - 1] || {};
  const fp = perf.feedback_stats || {};

  return (
    <>
      <div className="grid kpi">
        <Kpi label="Số lần chạy" value={fmt(log.length, 0)} color="#2f80ed" />
        <Kpi label="Anomaly rate (gần nhất)" value={`${fmt(last.anomaly_rate_pct)}%`} color="#e0701a" />
        <Kpi label="Silhouette (gần nhất)" value={fmt(last.silhouette, 3)} color="#6b46c1" />
        <Kpi label="Feedback FP rate" value={fp.overall_fp_rate != null ? fmt(fp.overall_fp_rate * 100) + "%" : "—"} meta={`${fp.n_feedback || 0} phản hồi`} color="#c98a00" />
      </div>

      <Card title="Diễn biến qua các lần chạy" style={{ marginTop: 16 }}>
        {log.length > 1 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={log.map((r, i) => ({ ...r, idx: i + 1 }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="idx" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Line type="monotone" dataKey="anomaly_rate_pct" name="Anomaly %" stroke="#e0701a" strokeWidth={2} />
              <Line type="monotone" dataKey="n_critical" name="CRITICAL" stroke="#c62828" strokeWidth={2} />
              <Line type="monotone" dataKey="missing_data_pct" name="Missing %" stroke="#2f80ed" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        ) : <p className="muted">Cần ≥ 2 lần chạy để vẽ diễn biến.</p>}
      </Card>

      <Card title="Đề xuất hiệu chỉnh (iterative improvement)" sub="advisory — không tự áp dụng" className="pad0" style={{ marginTop: 16 }}>
        <DataTable maxHeight={260}
          cols={[
            { key: "target", label: "Mục tiêu" },
            { key: "current", label: "Hiện tại", render: (r) => JSON.stringify(r.current) },
            { key: "suggested", label: "Đề xuất", render: (r) => JSON.stringify(r.suggested) },
            { key: "reason", label: "Lý do" },
          ]}
          rows={perf.suggestions || []} empty="Chưa đủ feedback để đề xuất." />
      </Card>

      <Card title="Nhật ký hiệu năng" className="pad0" style={{ marginTop: 16 }}>
        <DataTable maxHeight={360}
          cols={[
            { key: "run_ts", label: "Thời điểm" },
            { key: "frequency", label: "Tần suất" },
            { key: "n_banks", label: "NH", num: true },
            { key: "n_records_panel", label: "Bản ghi", num: true, render: (r) => fmt(r.n_records_panel, 0) },
            { key: "runtime_sec", label: "Thời gian (s)", num: true },
            { key: "anomaly_rate_pct", label: "Anomaly %", num: true },
            { key: "n_critical", label: "CRITICAL", num: true },
            { key: "silhouette", label: "Silhouette", num: true, render: (r) => fmt(r.silhouette, 3) },
            { key: "model_version", label: "Model ver" },
          ]}
          rows={[...log].reverse()} />
      </Card>
    </>
  );
}
