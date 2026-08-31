import axios from "axios";

const http = axios.create({ baseURL: "/api", timeout: 600000 });

export interface Meta {
  frequencies: string[];
  generated_at: string;
  disclaimer: string;
  versions: Record<string, string>;
  tuned?: { applied: boolean; tuned_at?: string; isolation_forest?: any; kmeans?: any };
}

export interface PeriodItem {
  period: string; year: number | null; sub: number | null;
  sub_label: string | null; kind: string;
}

export interface FreqData {
  frequency: string;
  empty: boolean;
  generated_at: string;
  disclaimer: string;
  summary: any;
  files: any[];
  unmapped_labels: { label: string; count: number }[];
  missing_by_metric: {
    metric: string; label: string; unit: string | null;
    camels_group: string | null; is_derived_ratio: boolean;
    n_missing: number; n_total: number; missing_pct: number;
  }[];
  ranking: any[];
  scores: any[];
  heatmap: { banks: string[]; periods: string[]; z: (number | null)[][] };
  domain_means: Record<string, number>;
  rule_findings: any[];
  rules_config: any[];
  anomalies: any[];
  anomaly_features: string[];
  clusters: {
    k: number;
    metrics: Record<string, Record<string, number>>;
    profiles: any[];
    projection: any[];
    assignment: any[];
  };
  systemic_stress: any[];
  high_risk_periods: any[];
  validation: any[];
  validation_counts: Record<string, number>;
  series: { metrics: string[]; data: Record<string, any> };
  base_metrics: string[];
  banks: string[];
  periods: { kind: string; items: PeriodItem[]; years: number[]; latest: string | null };
  ews: {
    metrics_used: string[];
    level_counts: Record<string, number>;
    system_now: any;
    latest: any[];
    system: any[];
    emerging: any[];
    trajectory: { periods: string[]; data: Record<string, (number | null)[]> };
    table: any[];
  };
  stress: {
    snapshot_period: string | null;
    scenarios: any[];
    system: any[];
    results: any[];
    breaking_points: any[];
  };
  combined: {
    is_combined: boolean;
    meta?: { base_frequency?: string; enriched_from?: any[] };
    by_source?: Record<string, number>;
    source_map?: any[];
  };
}

export const api = {
  meta: () => http.get<Meta>("/meta").then((r) => r.data),
  data: (freq: string) =>
    http.get<FreqData>(`/data/${freq}`).then((r) => r.data),
  filterRuleFindings: (params: Record<string, any>) =>
    http.get("/rule-findings/filter", { params }).then((r) => r.data),
  run: (freq: string, fresh = false) =>
    http.post(`/run/${freq}${fresh ? "?fresh=1" : ""}`).then((r) => r.data),
  performance: () => http.get("/performance").then((r) => r.data),
  pdfStatus: () => http.get("/pdf-status").then((r) => r.data),
  report: (freq: string) => http.post(`/report/${freq}`).then((r) => r.data),
  refreshSide: () => http.post("/refresh-side").then((r) => r.data),
  downloadUrl: (name: string) => `/api/download/${encodeURIComponent(name)}`,
  tune: (freq: string, model: string, criterion = "auto") =>
    http.post(`/tune/${freq}?model=${model}&criterion=${criterion}`).then((r) => r.data),
  tuneApply: (body: any) => http.post("/tune/apply", body).then((r) => r.data),
  tuneReset: () => http.post("/tune/reset").then((r) => r.data),
  ketQuaTinhDiem: (ky_du_lieu?: string) =>
    http.get("/be/tinh-diem/ket-qua", { params: { ky_du_lieu, limit: 10000 } })
      .then((r) => r.data)
      .catch(() =>
        axios.get("http://127.0.0.1:8088/tinh-diem/ket-qua", { params: { ky_du_lieu, limit: 10000 } })
          .then((r) => r.data)
      ),
  ketQuaTinhDiemByBank: (doi_tuong_id: string) =>
    http.get("/be/tinh-diem/ket-qua", { params: { doi_tuong_id, limit: 10000 } })
      .then((r) => r.data)
      .catch(() =>
        axios.get("http://127.0.0.1:8088/tinh-diem/ket-qua", { params: { doi_tuong_id, limit: 10000 } })
          .then((r) => r.data)
      ),
  lichSuBank: (doi_tuong_id: string) =>
    http.get(`/be/tinh-diem/lich-su/${encodeURIComponent(doi_tuong_id)}`)
      .then((r) => r.data)
      .catch(() =>
        axios.get(`http://127.0.0.1:8088/tinh-diem/lich-su/${encodeURIComponent(doi_tuong_id)}`)
          .then((r) => r.data)
      ),
  doiTuongList: () =>
    http.get("/be/doi-tuong-danh-gia")
      .then((r) => r.data)
      .catch(() =>
        axios.get("http://127.0.0.1:8088/doi-tuong-danh-gia?limit=1000")
          .then((r) => r.data)
      ),
  tinhDiemTuExcel: (formData: FormData) =>
    axios.post("/api/be/tinh-diem/tu-file-excel", formData)
      .then((r) => r.data)
      .catch(() =>
        axios.post("http://127.0.0.1:8088/tinh-diem/tu-file-excel", formData)
          .then((r) => r.data)
      ),
};

export const FREQ_LABEL: Record<string, string> = {
  combined: "Kết hợp (đa tần suất)", daily: "Ngày", monthly: "Tháng",
  quarterly: "Quý", yearly: "Năm",
};
