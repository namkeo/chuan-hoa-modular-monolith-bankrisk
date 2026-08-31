import { useEffect, useState } from "react";
import { api } from "../api";
import { Badge, Card, DataTable, Disclaimer } from "../components/ui";
import { fmt } from "../format";
import { useStore } from "../store";

const KIND_LABEL: Record<string, string> = {
  excel: "📊 Excel (.xlsx)", html: "🌐 Báo cáo HTML", critical_csv: "📋 Danh sách CRITICAL (.csv)",
};

export default function Reports() {
  const { freq, data, showToast } = useStore();
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<{ kind: string; name: string }[]>([]);
  const [pdf, setPdf] = useState<any | null>(null);

  useEffect(() => { api.pdfStatus().then(setPdf).catch(() => {}); }, []);

  const generate = async () => {
    setBusy(true);
    showToast(`Đang sinh báo cáo (${freq})...`);
    try {
      const res = await api.report(freq);
      setFiles(res.files || []);
      showToast("Đã sinh báo cáo.");
    } catch (e: any) {
      showToast(e?.response?.data?.error || "Sinh báo cáo thất bại", true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {data && <Disclaimer text={data.disclaimer} />}
      <Card title="Xuất báo cáo kiểm toán" sub={`tần suất ${freq}`}>
        <p className="help" style={{ marginTop: 0, marginBottom: 14 }}>
          Sinh báo cáo gồm: Executive summary, Top 10 NH rủi ro cao, CRITICAL pháp lý,
          bất thường ML, phân cụm, giai đoạn rủi ro cao, nhận định tín dụng/thanh khoản/proxy,
          phụ lục rule & công thức.
        </p>
        <button className="btn primary" disabled={busy} onClick={generate}>
          {busy ? "Đang sinh..." : "📄 Sinh báo cáo Excel + HTML + CSV"}
        </button>
        {files.length > 0 && (
          <div className="row-flex" style={{ marginTop: 16 }}>
            {files.map((f) => (
              <a key={f.name} className="btn" href={api.downloadUrl(f.name)} download>
                ⬇ {KIND_LABEL[f.kind] || f.kind}
              </a>
            ))}
          </div>
        )}
      </Card>

      <Card title="Trích xuất rule từ PDF quy định" sub="review — confidence < 0.8 = REVIEW_REQUIRED" className="pad0" style={{ marginTop: 16 }}>
        <div style={{ padding: 18, paddingBottom: 0 }}>
          <p className="help" style={{ marginTop: 0 }}>
            File scan/ảnh sẽ bị gắn <b>PDF_PARSE_LOW_CONFIDENCE</b>. Khi đó cấu hình thủ công
            trong <code>config/regulatory_rules.yaml</code> là nguồn chân lý.
          </p>
        </div>
        <DataTable maxHeight={240}
          cols={[
            { key: "pdf_file", label: "File PDF" },
            { key: "n_pages", label: "Trang", num: true },
            { key: "pages_with_text", label: "Trang có text", num: true },
            { key: "status", label: "Trạng thái", render: (r) => r.status?.startsWith("OK") ? <Badge level="ACTIVE" /> : <span className="badge REVIEW_REQUIRED" title={r.status}>{r.status?.split("(")[0]}</span> },
            { key: "n_candidates", label: "Candidate", num: true },
          ]}
          rows={pdf?.file_status || []} empty="Chưa quét PDF." />
      </Card>

      {pdf?.candidates?.length > 0 && (
        <Card title="Candidate rule (cần KTV review)" className="pad0" style={{ marginTop: 16 }}>
          <DataTable maxHeight={300}
            cols={[
              { key: "pdf_file", label: "File" },
              { key: "page", label: "Trang", num: true },
              { key: "candidate_metric", label: "Chỉ tiêu" },
              { key: "candidate_threshold", label: "Ngưỡng", num: true, render: (r) => r.candidate_threshold ?? "—" },
              { key: "confidence", label: "Conf.", num: true, render: (r) => fmt(r.confidence, 2) },
              { key: "suggested_rule_id", label: "Rule gợi ý" },
              { key: "status", label: "Trạng thái", render: (r) => <Badge level={r.status} /> },
            ]}
            rows={pdf.candidates} />
        </Card>
      )}
    </>
  );
}
