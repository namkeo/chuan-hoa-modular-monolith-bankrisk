import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAsOf } from "../components/PeriodPicker";
import { Badge, Card, DataTable, Disclaimer, Empty, Kpi } from "../components/ui";
import { fmt, fmtInt } from "../format";
import { useStore } from "../store";

/** Aggregate stress results for one scenario at one period into a system summary. */
function systemFor(results: any[], scenarioId: string, period: string) {
  const sub = results.filter((r) => r.scenario_id === scenarioId && r.period === period);
  const cap = sub.filter((r) => r.capital_status === "OK");
  const liq = sub.filter((r) => r.liquidity_status === "OK");
  const failCap = cap.filter((r) => !r.passes_capital);
  const failLiq = liq.filter((r) => !r.passes_liquidity);
  const assetsTot = cap.reduce((a, r) => a + (r.total_assets || 0), 0);
  const assetsFail = failCap.reduce((a, r) => a + (r.total_assets || 0), 0);
  return {
    n_assessed_capital: cap.length, n_fail_capital: failCap.length,
    total_capital_shortfall: failCap.reduce((a, r) => a + (r.capital_shortfall || 0), 0),
    min_stressed_car: cap.length ? Math.min(...cap.map((r) => r.stressed_car ?? 999)) : null,
    avg_stressed_car: cap.length ? cap.reduce((a, r) => a + (r.stressed_car || 0), 0) / cap.length : null,
    assets_share_failing: assetsTot ? assetsFail / assetsTot * 100 : 0,
    n_fail_liquidity: failLiq.length, total_liquidity_gap: failLiq.reduce((a, r) => a + (r.liquidity_gap || 0), 0),
  };
}

export default function StressTest() {
  const { data, freq } = useStore();
  const asof = useAsOf();
  const [scn, setScn] = useState<string>("severe");
  if (!data || data.empty) return null;
  const stress = data.stress;
  if (!stress || !stress.scenarios?.length || !stress.results?.length)
    return <Empty text={`Chưa có dữ liệu stress-test cho tần suất '${freq}'. Khuyến nghị dùng tần suất Tháng.`} />;

  const P = asof.period;
  const scenarios = stress.scenarios;
  const curScn = scenarios.find((s) => s.id === scn) ? scn : scenarios[0].id;
  const scnMeta = scenarios.find((s) => s.id === curScn);
  const sysRow = systemFor(stress.results, curScn, P);
  const sysSevere = systemFor(stress.results, "severe", P);

  const rows = stress.results.filter((r) => r.scenario_id === curScn && r.period === P);
  const capRows = rows.filter((r) => r.capital_status === "OK")
    .sort((a, b) => (a.stressed_car ?? 99) - (b.stressed_car ?? 99));
  const liqRows = rows.filter((r) => r.liquidity_status === "OK" && !r.passes_liquidity)
    .sort((a, b) => (b.liquidity_gap ?? 0) - (a.liquidity_gap ?? 0));

  // System resilience across scenarios (capital fails + shortfall) for selected period.
  const sysChart = scenarios.map((s) => {
    const agg = systemFor(stress.results, s.id, P);
    return { name: s.name, fail: agg.n_fail_capital,
             shortfall: agg.total_capital_shortfall, minCar: agg.min_stressed_car };
  });

  // Breaking points (reverse stress) for the selected period.
  const breaking = stress.breaking_points
    .filter((b) => b.period === P && b.breaking_npl_pp != null)
    .sort((a, b) => a.breaking_npl_pp - b.breaking_npl_pp).slice(0, 15);

  return (
    <>
      <Disclaimer text={`Stress-test (tần suất ${freq}, kỳ ${P}) — phân tích kịch bản GIẢ ĐỊNH đo sức chịu đựng vốn (CAR) & thanh khoản. Không phải dự báo; giả định (LGD, run-off, sốc RWA) cần KTV xem xét phù hợp bối cảnh.`} />

      <div className="grid kpi">
        <Kpi label="Kịch bản nghiêm trọng — NH thiếu vốn" value={fmtInt(sysSevere.n_fail_capital)} meta={`/ ${fmtInt(sysSevere.n_assessed_capital)} NH đánh giá`} color="#c62828" />
        <Kpi label="Tổng thiếu hụt vốn (severe)" value={fmt(sysSevere.total_capital_shortfall, 0)} meta="tỷ đồng (nhu cầu tái cấp vốn)" color="#e0701a" />
        <Kpi label="CAR thấp nhất sau sốc (severe)" value={`${fmt(sysSevere.min_stressed_car)}%`} color="#c98a00" />
        <Kpi label="NH mất thanh khoản (severe)" value={fmtInt(sysSevere.n_fail_liquidity)} color="#6b46c1" />
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Số NH không đạt CAR 8% theo kịch bản" sub="mức độ khắc nghiệt tăng dần">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={sysChart} margin={{ left: 0, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" fontSize={9} angle={-15} textAnchor="end" height={50} interval={0} />
              <YAxis yAxisId="l" fontSize={11} allowDecimals={false} />
              <YAxis yAxisId="r" orientation="right" fontSize={11} />
              <Tooltip formatter={(v: any, n: any) => n === "Thiếu vốn (tỷ)" ? fmt(v, 0) : fmt(v, 0)} />
              <Bar yAxisId="l" dataKey="fail" name="Số NH không đạt" radius={[4, 4, 0, 0]}>
                {sysChart.map((_, i) => <Cell key={i} fill={["#2e7d32", "#c98a00", "#e0701a", "#c62828", "#6b46c1"][i % 5]} />)}
              </Bar>
              <Line yAxisId="r" dataKey="shortfall" name="Thiếu vốn (tỷ)" stroke="#0a2540" strokeWidth={2} dot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </Card>

        <Card title="⏳ Reverse stress — điểm gãy vốn" sub="NPL cần tăng thêm (điểm %) để CAR chạm 8%">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={breaking} layout="vertical" margin={{ left: 30, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" fontSize={11} unit="pp" />
              <YAxis type="category" dataKey="bank_id" width={90} fontSize={10} />
              <Tooltip formatter={(v: any) => `${fmt(v, 2)} điểm %`} />
              <Bar dataKey="breaking_npl_pp" radius={[0, 4, 4, 0]}>
                {breaking.map((d, i) => <Cell key={i} fill={d.breaking_npl_pp < 1 ? "#c62828" : d.breaking_npl_pp < 3 ? "#e0701a" : "#2f80ed"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="help">Càng nhỏ = đệm vốn càng mỏng. &lt;1 điểm %: rất dễ tổn thương.</p>
        </Card>
      </div>

      <Card title="Chọn kịch bản để xem chi tiết" style={{ marginTop: 16 }}>
        <div className="row-flex">
          {scenarios.map((s) => (
            <button key={s.id} className={`btn ${s.id === curScn ? "primary" : ""}`} onClick={() => setScn(s.id)}>
              {s.name}
            </button>
          ))}
        </div>
        {scnMeta && (
          <p className="help" style={{ marginTop: 12 }}>
            <b>{scnMeta.name}:</b> {scnMeta.description} — Giả định: NPL +{fmt(scnMeta.npl_shock_pp)}đ%, RWA +{fmt(scnMeta.rwa_shock * 100)}%,
            LGD {fmt(scnMeta.lgd * 100)}%, rút tiền gửi {fmt(scnMeta.deposit_runoff * 100)}%, rút vốn bán buôn {fmt(scnMeta.wholesale_runoff * 100)}%.
          </p>
        )}
        <div className="grid kpi" style={{ marginTop: 12 }}>
          <Kpi label="NH không đạt CAR" value={fmtInt(sysRow.n_fail_capital)} color="#c62828" />
          <Kpi label="Tổng thiếu hụt vốn" value={fmt(sysRow.total_capital_shortfall, 0)} meta="tỷ đồng" color="#e0701a" />
          <Kpi label="CAR TB sau sốc" value={`${fmt(sysRow.avg_stressed_car)}%`} color="#c98a00" />
          <Kpi label="% tài sản ở NH không đạt" value={`${fmt(sysRow.assets_share_failing)}%`} color="#6b46c1" />
          <Kpi label="NH mất thanh khoản" value={fmtInt(sysRow.n_fail_liquidity)} color="#0a9396" />
        </div>
      </Card>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title={`Sức chịu đựng vốn — ${scnMeta?.name}`} sub="CAR trước → sau sốc (đỏ = không đạt 8%)" className="pad0">
          <DataTable maxHeight={420}
            cols={[
              { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
              { key: "baseline_car", label: "CAR gốc", num: true, render: (r) => fmt(r.baseline_car, 2) },
              { key: "stressed_car", label: "CAR sau sốc", num: true, render: (r) => <span style={{ fontWeight: 700, color: r.stressed_car < 8 ? "#c62828" : "#2e7d32" }}>{fmt(r.stressed_car, 2)}</span> },
              { key: "car_delta", label: "Δ", num: true, render: (r) => <span style={{ color: "#c62828" }}>{fmt(r.car_delta, 2)}</span> },
              { key: "capital_shortfall", label: "Thiếu vốn (tỷ)", num: true, render: (r) => r.capital_shortfall > 0 ? fmt(r.capital_shortfall, 0) : "—" },
              { key: "passes_capital", label: "Kết quả", render: (r) => <Badge level={r.passes_capital ? "NORMAL" : "ALARM"} /> },
            ]}
            rows={capRows} empty="Thiếu dữ liệu CAR/RWA (dùng tần suất Tháng)." />
        </Card>

        <Card title={`Sức chịu đựng thanh khoản — ${scnMeta?.name}`} sub="NH không đạt sau sốc rút tiền" className="pad0">
          <DataTable maxHeight={420}
            cols={[
              { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
              { key: "liq_method", label: "PP", render: (r) => <span className="muted">{r.liq_method}</span> },
              { key: "stressed_ldr", label: "LDR sau sốc", num: true, render: (r) => r.stressed_ldr != null ? `${fmt(r.stressed_ldr, 1)}%` : (r.stressed_lcr != null ? `LCR ${fmt(r.stressed_lcr, 0)}%` : "—") },
              { key: "liquidity_gap", label: "Khe hở TK (tỷ)", num: true, render: (r) => fmt(r.liquidity_gap, 0) },
              { key: "deposit_outflow", label: "Rút ra (tỷ)", num: true, render: (r) => fmt(r.deposit_outflow, 0) },
            ]}
            rows={liqRows} empty="Không có NH mất thanh khoản trong kịch bản này." />
        </Card>
      </div>
    </>
  );
}
