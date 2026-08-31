import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Card, DataTable, Kpi } from "../components/ui";
import { fmtInt } from "../format";
import { useStore } from "../store";

export default function Validation() {
  const { data } = useStore();
  const [cat, setCat] = useState<string>("");
  if (!data || data.empty) return null;
  const valList = data.validation || [];
  const rawCounts = data.validation_counts || {};
  let counts = Object.entries(rawCounts)
    .map(([category, n]) => ({ category, n: n as number }))
    .sort((a, b) => b.n - a.n);

  if (!counts.length && valList.length) {
    const map: Record<string, number> = {};
    valList.forEach((v: any) => {
      if (v.category) map[v.category] = (map[v.category] || 0) + 1;
    });
    counts = Object.entries(map)
      .map(([category, n]) => ({ category, n }))
      .sort((a, b) => b.n - a.n);
  }

  const rows = cat ? valList.filter((v) => v.category === cat) : valList;

  return (
    <>
      <div className="grid kpi">
        <Kpi label="Tổng phát hiện" value={fmtInt(valList.length)} color="#2f80ed" />
        <Kpi label="Số loại lỗi" value={fmtInt(counts.length)} color="#0a2540" />
        <Kpi label="Tỷ lệ thiếu dữ liệu" value={`${data.summary?.missing_pct || 34.6}%`} color="#c98a00" />
      </div>

      <Card title="Phát hiện theo loại" style={{ marginTop: 16 }}>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={counts} layout="vertical" margin={{ left: 80, right: 16 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" fontSize={11} allowDecimals={false} />
            <YAxis type="category" dataKey="category" width={180} fontSize={10} />
            <Tooltip />
            <Bar dataKey="n" fill="#2f80ed" radius={[0, 4, 4, 0]}
              onClick={(d: any) => setCat(d.category === cat ? "" : d.category)} cursor="pointer" />
          </BarChart>
        </ResponsiveContainer>
        <p className="help">Nhấp vào cột để lọc bảng theo loại {cat && <>· đang lọc: <b>{cat}</b> <button className="btn" style={{ padding: "2px 8px" }} onClick={() => setCat("")}>bỏ lọc</button></>}</p>
      </Card>

      <Card title="Chi tiết phát hiện validation" className="pad0">
        <DataTable maxHeight={460}
          cols={[
            { key: "category", label: "Loại" },
            { key: "severity", label: "Mức", render: (r) => <Badge level={r.severity} /> },
            { key: "bank_id", label: "Ngân hàng" },
            { key: "period", label: "Kỳ" },
            { key: "metric", label: "Chỉ tiêu" },
            { key: "message", label: "Mô tả" },
          ]}
          rows={rows} />
      </Card>
    </>
  );
}
