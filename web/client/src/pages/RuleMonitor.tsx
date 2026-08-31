import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAsOf } from "../components/PeriodPicker";
import { Badge, Card, DataTable, Kpi } from "../components/ui";
import { fmt, fmtInt } from "../format";
import { useStore } from "../store";

const SEV_COLOR: Record<string, string> = {
  CRITICAL: "#c62828", HIGH: "#e0701a", MEDIUM: "#c98a00", LOW: "#2e7d32", DATA_GAP: "#6b46c1",
};
const SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

function removeAccents(str: string): string {
  if (!str) return "";
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

export default function RuleMonitor() {
  const { data } = useStore();
  const asof = useAsOf();
  const [sevFilter, setSevFilter] = useState<string[]>([]);
  const [bankFilter, setBankFilter] = useState<string>("");
  const [periodFilter, setPeriodFilter] = useState<string>("ALL");
  const [metricFilter, setMetricFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  const PAGE_SIZE = 100;

  if (!data || data.empty) return null;

  // Options for filter selects
  const allFindings = data.rule_findings || [];
  const uniqueBanks = Array.from(new Set(allFindings.map((f) => f.bank_id).filter(Boolean))).sort();
  const uniquePeriods = Array.from(new Set(allFindings.map((f) => f.period).filter(Boolean))).sort().reverse();
  const uniqueMetrics = Array.from(new Set(allFindings.map((f) => f.metric).filter(Boolean))).sort();
  const uniqueTypes = Array.from(new Set(allFindings.map((f) => f.finding_type).filter(Boolean))).sort();

  // Filtered findings by period (if ALL, include all periods; otherwise filter by specific period)
  const periodFindings = useMemo(() => {
    return periodFilter === "ALL" || !periodFilter
      ? allFindings 
      : allFindings.filter((f) => f.period === periodFilter);
  }, [allFindings, periodFilter]);

  // Base findings filtered by active Advanced Filter criteria (Bank, Metric, Finding Type, Search Text) for KPI aggregation
  const kpiBaseFindings = useMemo(() => {
    return periodFindings.filter((f) => {
      if (bankFilter && f.bank_id !== bankFilter) return false;
      if (metricFilter && f.metric !== metricFilter) return false;
      if (typeFilter && f.finding_type !== typeFilter) return false;
      if (searchQuery) {
        const q = removeAccents(searchQuery);
        const text = removeAccents(`${f.bank_id} ${f.rule_name} ${f.metric} ${f.legal_source} ${f.article_reference || ""}`);
        if (!text.includes(q)) return false;
      }
      return true;
    });
  }, [periodFindings, bankFilter, metricFilter, typeFilter, searchQuery]);

  const sevCounts: Record<string, number> = {};
  kpiBaseFindings.forEach((f) => { sevCounts[f.severity] = (sevCounts[f.severity] || 0) + 1; });

  const filtered = useMemo(() => {
    return kpiBaseFindings.filter((f) => {
      if (sevFilter.length && !sevFilter.includes(f.severity)) return false;
      return true;
    });
  }, [kpiBaseFindings, sevFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pagedRows = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, page]);

  const violByBank = useMemo(() => {
    const m: Record<string, { bank_id: string; CRITICAL: number; HIGH: number; MEDIUM: number; LOW: number; total: number }> = {};
    filtered.filter((f) => SEV_ORDER.includes(f.severity)).forEach((f) => {
      const sev = f.severity;
      if (!sev) return;
      const row = m[f.bank_id] || (m[f.bank_id] = { bank_id: f.bank_id, CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, total: 0 });
      if (sev in row) {
        row[sev as "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"] += 1;
        row.total += 1;
      }
    });
    return Object.values(m).sort((a, b) => b.total - a.total).slice(0, 15);
  }, [filtered]);

  const toggleSev = (s: string) => {
    setPage(1);
    setSevFilter((p) => p.includes(s) ? p.filter((x) => x !== s) : [...p, s]);
  };

  const resetFilters = () => {
    setSevFilter([]);
    setBankFilter("");
    setPeriodFilter("ALL");
    setMetricFilter("");
    setTypeFilter("");
    setSearchQuery("");
    setPage(1);
  };

  const filteredRulesConfig = useMemo(() => {
    return (data.rules_config || []).filter((r) => {
      if (metricFilter && r.metric !== metricFilter) return false;
      if (sevFilter.length && !sevFilter.includes(r.severity)) return false;
      if (searchQuery) {
        const q = removeAccents(searchQuery);
        const text = removeAccents(`${r.rule_id} ${r.rule_name} ${r.metric} ${r.legal_source} ${r.article_reference || ""}`);
        if (!text.includes(q)) return false;
      }
      return true;
    });
  }, [data.rules_config, metricFilter, sevFilter, searchQuery]);

  return (
    <>
      <div className="grid kpi">
        {["CRITICAL", "HIGH", "MEDIUM", "LOW", "DATA_GAP"].map((s) => (
          <Kpi key={s} label={s} value={fmtInt(sevCounts[s] || 0)} color={SEV_COLOR[s]} />
        ))}
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Vi phạm theo ngân hàng & mức độ">
          {violByBank.length ? (
            <ResponsiveContainer width="100%" height={360}>
              <BarChart data={violByBank} layout="vertical" margin={{ left: 10, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" fontSize={11} allowDecimals={false} />
                <YAxis type="category" dataKey="bank_id" width={115} fontSize={10} interval={0} />
                <Tooltip />
                <Legend fontSize={11} />
                {SEV_ORDER.map((s, i) => (
                  <Bar key={s} dataKey={s} stackId="sev" fill={SEV_COLOR[s]}
                    radius={i === SEV_ORDER.length - 1 ? [0, 4, 4, 0] : undefined} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          ) : <div className="empty-state">📭 Không có dữ liệu</div>}
        </Card>

        <Card title="Bộ lọc vi phạm nâng cao" sub="Lọc chi tiết theo ngân hàng, kỳ báo cáo, chỉ tiêu và mức độ vi phạm">
          {/* 1. Tag Mức độ (Severity) */}
          <div style={{ marginBottom: 16, background: "#f8fafc", padding: "12px 14px", borderRadius: 10, border: "1px solid #e2e8f0" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", marginBottom: 8, letterSpacing: "0.5px", textTransform: "uppercase" }}>
              🎯 Mức độ cảnh báo (Severity)
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {["CRITICAL", "HIGH", "MEDIUM", "LOW", "DATA_GAP"].map((s) => {
                const active = sevFilter.includes(s);
                return (
                  <button
                    key={s}
                    style={{
                      border: active ? `1.5px solid ${SEV_COLOR[s]}` : "1px solid #cbd5e1",
                      color: active ? "#ffffff" : SEV_COLOR[s],
                      backgroundColor: active ? SEV_COLOR[s] : "#ffffff",
                      fontWeight: active ? 700 : 600,
                      fontSize: 11,
                      padding: "5px 13px",
                      borderRadius: 20,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                      boxShadow: active ? `0 2px 6px ${SEV_COLOR[s]}40` : "0 1px 2px rgba(0,0,0,0.05)",
                    }}
                    onClick={() => toggleSev(s)}
                  >
                    {active ? "✓ " : ""}{s}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. Grid bộ lọc chi tiết */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: "#475569", display: "block", marginBottom: 5 }}>
                🏦 NGÂN HÀNG (bank_id)
              </label>
              <select 
                style={{
                  width: "100%", fontSize: 12, padding: "8px 12px", borderRadius: 8,
                  border: "1px solid #cbd5e1", background: "#f8fafc", color: "#1e293b", fontWeight: 500,
                  outline: "none"
                }}
                value={bankFilter} 
                onChange={(e) => {
                  setBankFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">-- Tất cả ngân hàng --</option>
                {uniqueBanks.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: "#475569", display: "block", marginBottom: 5 }}>
                📅 KỲ BÁO CÁO (period)
              </label>
              <select 
                style={{
                  width: "100%", fontSize: 12, padding: "8px 12px", borderRadius: 8,
                  border: "1px solid #cbd5e1", background: "#f8fafc", color: "#1e293b", fontWeight: 500,
                  outline: "none"
                }}
                value={periodFilter} 
                onChange={(e) => {
                  setPeriodFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="ALL">-- Tất cả các kỳ --</option>
                {uniquePeriods.map((p) => (
                  <option key={p} value={p}>Kỳ {p}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: "#475569", display: "block", marginBottom: 5 }}>
                📊 CHỈ TIÊU (metric)
              </label>
              <select 
                style={{
                  width: "100%", fontSize: 12, padding: "8px 12px", borderRadius: 8,
                  border: "1px solid #cbd5e1", background: "#f8fafc", color: "#1e293b", fontWeight: 500,
                  outline: "none"
                }}
                value={metricFilter} 
                onChange={(e) => {
                  setMetricFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">-- Tất cả chỉ tiêu --</option>
                {uniqueMetrics.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: "#475569", display: "block", marginBottom: 5 }}>
                ⚠️ LOẠI VI PHẠM (finding_type)
              </label>
              <select 
                style={{
                  width: "100%", fontSize: 12, padding: "8px 12px", borderRadius: 8,
                  border: "1px solid #cbd5e1", background: "#f8fafc", color: "#1e293b", fontWeight: 500,
                  outline: "none"
                }}
                value={typeFilter} 
                onChange={(e) => {
                  setTypeFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">-- Tất cả loại --</option>
                {uniqueTypes.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          </div>

          {/* 3. Ô Tìm kiếm Căn cứ & Rule */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: "#475569", display: "block", marginBottom: 5 }}>
              🔍 CĂN CỨ VĂN BẢN / TÊN RULE (legal_source / rule_name)
            </label>
            <input 
              type="text" 
              style={{
                width: "100%", fontSize: 12, padding: "8px 12px", borderRadius: 8,
                border: "1px solid #cbd5e1", background: "#ffffff", color: "#1e293b",
                outline: "none"
              }}
              placeholder="Nhập tên Thông tư, Điều khoản, Tên rule cần tra cứu..." 
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
            />
          </div>

          {/* 4. Nút bấm Đặt lại bộ lọc */}
          <div style={{ display: "flex", justifyContent: "flex-end", borderTop: "1px solid #f1f5f9", paddingTop: 12 }}>
            <button
              style={{
                background: "#f1f5f9", color: "#475569", border: "1px solid #cbd5e1",
                borderRadius: 8, padding: "6px 16px", fontSize: 12, fontWeight: 600,
                cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
                transition: "all 0.15s ease"
              }}
              onClick={resetFilters}
            >
              🔄 Đặt lại bộ lọc
            </button>
          </div>
        </Card>
      </div>

      <Card title="Danh sách vi phạm / cảnh báo" className="pad0">
        <DataTable maxHeight={460}
          cols={[
            { key: "bank_id", label: "Ngân hàng", render: (r) => <span className="b">{r.bank_id}</span> },
            { key: "period", label: "Kỳ" },
            { key: "rule_name", label: "Rule" },
            { key: "metric", label: "Chỉ tiêu" },
            { key: "metric_value", label: "Giá trị", num: true, render: (r) => fmt(r.metric_value, 2) },
            { key: "operator", label: "", render: (r) => <span className="muted">{r.operator} {r.threshold}</span> },
            { key: "severity", label: "Mức", render: (r) => <Badge level={r.severity} /> },
            { key: "finding_type", label: "Loại", render: (r) => (
              <span className="muted" title={r.description || ""}>{r.finding_type}</span>) },
            { key: "legal_source", label: "Căn cứ", render: (r) => <span className="muted" title={r.article_reference}>{r.legal_source}</span> },
          ]}
          rows={pagedRows} />

        {/* Thanh phân trang 100 bản ghi/trang */}
        {filtered.length > 0 && (
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "10px 16px",
            borderTop: "1px solid #e2e8f0",
            fontSize: 12,
            color: "#475569",
            backgroundColor: "#f8fafc"
          }}>
            <div>
              Hiển thị <b>{(page - 1) * PAGE_SIZE + 1}</b> - <b>{Math.min(page * PAGE_SIZE, filtered.length)}</b> trên tổng số <b>{fmtInt(filtered.length)}</b> vi phạm
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <button 
                className="btn" 
                style={{ padding: "4px 8px", fontSize: 11 }} 
                disabled={page === 1}
                onClick={() => setPage(1)}
              >
                ⏮ Đầu
              </button>
              <button 
                className="btn" 
                style={{ padding: "4px 10px", fontSize: 11 }} 
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ◀ Trước
              </button>
              <span style={{ margin: "0 6px", fontWeight: 600 }}>
                Trang {page} / {totalPages}
              </span>
              <button 
                className="btn" 
                style={{ padding: "4px 10px", fontSize: 11 }} 
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Sau ▶
              </button>
              <button 
                className="btn" 
                style={{ padding: "4px 8px", fontSize: 11 }} 
                disabled={page >= totalPages}
                onClick={() => setPage(totalPages)}
              >
                Cuối ⏭
              </button>
            </div>
          </div>
        )}
      </Card>

      <Card title="Căn cứ văn bản — rule đang áp dụng" sub={`${filteredRulesConfig.length} / ${data.rules_config.length} rule`} className="pad0">
        <DataTable maxHeight={420}
          cols={[
            { key: "rule_id", label: "ID" },
            { key: "rule_name", label: "Tên rule" },
            { key: "severity", label: "Severity", render: (r) => <Badge level={r.severity} /> },
            { key: "status", label: "Trạng thái", render: (r) => <Badge level={r.status} /> },
            { key: "metric", label: "Chỉ tiêu" },
            { key: "threshold", label: "Ngưỡng", render: (r) => `${r.operator} ${Array.isArray(r.threshold) ? `[${r.threshold.join(", ")}]` : r.threshold}` },
            { key: "legal_source", label: "Văn bản" },
            { key: "article_reference", label: "Điều/khoản" },
          ]}
          rows={filteredRulesConfig} />
      </Card>
    </>
  );
}
