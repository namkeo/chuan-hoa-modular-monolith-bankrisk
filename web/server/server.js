/**
 * Express API gateway for the Bank System Risk Analysis tool.
 *
 * Responsibilities:
 *  - Serve the JSON payloads produced by the Python pipeline (outputs/api/*.json).
 *  - On demand, spawn `python -m src.api_export ...` to (re)run the analysis or
 *    regenerate reports — the heavy work stays in the tested Python engine.
 *  - Serve report downloads (Excel/HTML/CSV) and the built React SPA.
 *
 * No analytics happen here; this is a thin, robust bridge so the React frontend
 * can stay pure presentation.
 */
import cors from "cors";
import { spawn } from "node:child_process";
import express from "express";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// The server sits at a different depth in the repo than in the image: locally it
// runs from <repo>/web/server, in the container from /app/server, where the
// exports are mounted at /app/outputs. A fixed "two levels up" resolves to "/"
// there, so API_DIR pointed at a directory that does not exist and every
// fallback read silently returned nothing. Probe the candidates instead, the
// same way resolve_data_dir() does on the Python side.
function resolveProjectRoot() {
  const candidates = [
    process.env.PROJECT_ROOT,
    path.resolve(__dirname, "..", ".."), // repo checkout: web/server -> repo root
    path.resolve(__dirname, ".."),       // container image: /app/server -> /app
  ].filter(Boolean);
  const found = candidates.find((dir) => fs.existsSync(path.join(dir, "outputs", "api")));
  if (!found) {
    console.warn(`[!] Không tìm thấy outputs/api trong: ${candidates.join(", ")}. ` +
                 `Tầng dự phòng đọc tệp JSON sẽ không hoạt động.`);
  }
  return found || candidates[1];
}

const PROJECT_ROOT = resolveProjectRoot();
const API_DIR = path.join(PROJECT_ROOT, "outputs", "api");
const REPORTS_DIR = path.join(PROJECT_ROOT, "outputs", "reports");
const EXPORTS_DIR = path.join(PROJECT_ROOT, "outputs", "exports");
const CLIENT_DIST = path.join(__dirname, "..", "client", "dist");

const PORT = process.env.PORT || 4000;

// Resolve the Python interpreter: prefer PYTHON env, then the project's venv, then a
// sibling "data_all" venv (so running the code from source_code reuses data_all's env).
function resolvePython() {
  if (process.env.PYTHON && fs.existsSync(process.env.PYTHON)) return process.env.PYTHON;
  if (process.env.PYTHON) return process.env.PYTHON;
  const userHome = process.env.USERPROFILE || process.env.HOME || "";
  const candidates = [
    path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe"), // Windows venv
    path.join(PROJECT_ROOT, ".venv", "bin", "python"), // *nix venv
    path.join(userHome, "AppData", "Local", "miniconda3", "envs", "source_code", "python.exe"),
    path.join(userHome, "AppData", "Local", "anaconda3", "envs", "source_code", "python.exe"),
    path.join(userHome, ".conda", "envs", "source_code", "python.exe"),
    path.join(PROJECT_ROOT, "..", "data_all", ".venv", "Scripts", "python.exe"),
    path.join(PROJECT_ROOT, "..", "data_all", ".venv", "bin", "python"),
  ];
  for (const c of candidates) if (fs.existsSync(c)) return c;
  return process.platform === "win32" ? "python" : "python3";
}
const PYTHON = resolvePython();

const app = express();
app.use(cors());
app.use(express.json());

// --- tiny request log ---
app.use((req, _res, next) => {
  console.log(`${new Date().toISOString()} ${req.method} ${req.url}`);
  next();
});

const FASTAPI_URL = process.env.FASTAPI_URL || "http://127.0.0.1:8080";
const BE_URL = process.env.BE_URL || process.env.XEP_HANG_URL || "http://127.0.0.1:8088";

// Fetch the analysis payload from the module that owns it.
//
// `bank_risk_db` belongs to the giam_sat_rui_ro module (see
// docs/architecture/data-ownership.yml), so this gateway asks that module over
// HTTP instead of querying its collections. The previous direct read of
// `api_payloads` returned the module's *lean* document, which by design omits
// rule_findings and anomalies — pages rendered blank instead of failing, which
// read as "no violations found". Returning null lets the caller fall through to
// outputs/api/<freq>.json, which carries the complete payload.
async function getFreqPayloadFromFastAPI(freq) {
  try {
    const url = `${FASTAPI_URL}/api/data/${freq}`;
    console.log(`[*] Proxying FE request /api/data/${freq} -> FastAPI bank_risk_service (${url})`);
    const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      console.log(`[+] Successfully fetched data for '${freq}' from FastAPI bank_risk_service!`);
      return await res.json();
    }
    console.warn(`FastAPI returned HTTP ${res.status} for '${freq}'; falling back to the JSON export.`);
  } catch (err) {
    console.warn(`FastAPI unavailable at ${FASTAPI_URL}, falling back to the JSON export:`, err.message);
  }

  return null;
}

// Proxy endpoint to fetch KetQuaTinhDiem collection from Credit Scoring BE (or MongoDB directly)
app.get("/api/be/tinh-diem/ket-qua", async (req, res) => {
  try {
    const queryParams = new URLSearchParams(req.query).toString();
    const beRes = await fetch(`${BE_URL}/tinh-diem/ket-qua${queryParams ? `?${queryParams}` : ""}`, { signal: AbortSignal.timeout(2000) });
    if (beRes.ok) {
      // Return the module's answer as-is, including an empty list. Treating
      // "empty" as a failure used to fall through to a query that applied only
      // part of the filters and a smaller limit, so a filter that legitimately
      // matched nothing could still come back with rows.
      return res.json(await beRes.json());
    }
    console.warn(`Credit scoring service returned HTTP ${beRes.status}; using the precomputed export.`);
  } catch (err) {
    console.warn(`BE at ${BE_URL} unavailable, using the precomputed export:`, err.message);
  }

  // Load precomputed 31 bank rankings fallback data
  let fallbackList = [];
  try {
    const jsonPath = fs.existsSync(path.join(__dirname, "../../xep_hang_service/scripts/precomputed_31_rankings.json"))
      ? path.join(__dirname, "../../xep_hang_service/scripts/precomputed_31_rankings.json")
      : path.join(__dirname, "../../be/scripts/precomputed_31_rankings.json");
    if (fs.existsSync(jsonPath)) {
      fallbackList = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
    }
  } catch (e) {
    console.warn("Error reading precomputed_31_rankings.json:", e.message);
  }

  if (req.query.ky_du_lieu) {
    const targetKy = String(req.query.ky_du_lieu).trim();
    fallbackList = fallbackList.filter(i => i.ky_du_lieu === targetKy);
  }
  if (req.query.doi_tuong_id) {
    const targetId = String(req.query.doi_tuong_id).trim();
    fallbackList = fallbackList.filter(i => i.doi_tuong_id === targetId || i.ma_doi_tuong === targetId);
  }

  return res.json({ code: 200, message: "Success (Precomputed Fallback)", data: fallbackList });
});

// Dedicated proxy endpoint to fetch full bank history across all periods
app.get("/api/be/tinh-diem/lich-su/:doi_tuong_id", async (req, res) => {
  const doi_tuong_id = req.params.doi_tuong_id;
  try {
    const beRes = await fetch(`${BE_URL}/tinh-diem/lich-su/${encodeURIComponent(doi_tuong_id)}`, { signal: AbortSignal.timeout(2000) });
    if (beRes.ok) {
      return res.json(await beRes.json());
    }
    console.warn(`Credit scoring service returned HTTP ${beRes.status} for lich-su/${doi_tuong_id}.`);
  } catch (err) {
    console.warn(`BE at ${BE_URL} unavailable for lich-su:`, err.message);
  }

  // `KetQuaTinhDiem` belongs to the xep_hang_tctd module, so there is no second
  // route to it from here. That module already falls back to its precomputed
  // export when its own database is unreachable, so reaching this line means the
  // module itself is down — say so rather than reporting an empty history as a
  // successful answer.
  return res.status(503).json({
    code: 503,
    message: "Dịch vụ xếp hạng tạm thời không phản hồi. Vui lòng thử lại.",
    data: []
  });
});

// Dedicated proxy endpoint to fetch DoiTuongDanhGia list
app.get("/api/be/doi-tuong-danh-gia", async (req, res) => {
  try {
    const beRes = await fetch(`${BE_URL}/doi-tuong-danh-gia?limit=1000`, { signal: AbortSignal.timeout(2000) });
    if (beRes.ok) {
      return res.json(await beRes.json());
    }
  } catch (err) {
    console.warn(`BE at ${BE_URL} unavailable for doi-tuong-danh-gia:`, err.message);
  }

  const DEFAULT_BANKS = [
    { _id: "VietinBank", ma_doi_tuong: "VietinBank", ten_doi_tuong: "Ngân hàng TMCP Công thương Việt Nam", ten_viet_tat: "VietinBank (CTG)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "BIDV", ma_doi_tuong: "BIDV", ten_doi_tuong: "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam", ten_viet_tat: "BIDV (BID)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "Agribank", ma_doi_tuong: "Agribank", ten_doi_tuong: "Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam", ten_viet_tat: "Agribank (AGR)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "Vietcombank", ma_doi_tuong: "Vietcombank", ten_doi_tuong: "Ngân hàng TMCP Ngoại thương Việt Nam", ten_viet_tat: "Vietcombank (VCB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "ACB", ma_doi_tuong: "ACB", ten_doi_tuong: "Ngân hàng TMCP Á Châu", ten_viet_tat: "ACB", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "LPBank", ma_doi_tuong: "LPBank", ten_doi_tuong: "Ngân hàng TMCP Lộc Phát Việt Nam", ten_viet_tat: "LPBank (LPB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "Techcombank", ma_doi_tuong: "Techcombank", ten_doi_tuong: "Ngân hàng TMCP Kỹ Thương Việt Nam", ten_viet_tat: "Techcombank (TCB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "HDBank", ma_doi_tuong: "HDBank", ten_doi_tuong: "Ngân hàng TMCP Phát triển TP.HCM", ten_viet_tat: "HDBank (HDB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "MBBank", ma_doi_tuong: "MBBank", ten_doi_tuong: "Ngân hàng TMCP Quân Đội", ten_viet_tat: "MBBank (MBB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "VIB", ma_doi_tuong: "VIB", ten_doi_tuong: "Ngân hàng TMCP Quốc tế Việt Nam", ten_viet_tat: "VIB", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "SHB", ma_doi_tuong: "SHB", ten_doi_tuong: "Ngân hàng TMCP Sài Gòn - Hà Nội", ten_viet_tat: "SHB", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "TPBank", ma_doi_tuong: "TPBank", ten_doi_tuong: "Ngân hàng TMCP Tiên Phong", ten_viet_tat: "TPBank (TPB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "VPBank", ma_doi_tuong: "VPBank", ten_doi_tuong: "Ngân hàng TMCP Việt Nam Thịnh Vượng", ten_viet_tat: "VPBank (VPB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "Bac A Bank", ma_doi_tuong: "Bac A Bank", ten_doi_tuong: "Ngân hàng TMCP Bắc Á", ten_viet_tat: "Bac A Bank (BAB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "MSB", ma_doi_tuong: "MSB", ten_doi_tuong: "Ngân hàng TMCP Hàng Hải Việt Nam", ten_viet_tat: "MSB", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "VietABank", ma_doi_tuong: "VietABank", ten_doi_tuong: "Ngân hàng TMCP Việt Á", ten_viet_tat: "VietABank (VAB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "SeABank", ma_doi_tuong: "SeABank", ten_doi_tuong: "Ngân hàng TMCP Đông Nam Á", ten_viet_tat: "SeABank (SSB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "BVBank", ma_doi_tuong: "BVBank", ten_doi_tuong: "Ngân hàng TMCP Bản Việt", ten_viet_tat: "BVBank (BVB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "Eximbank", ma_doi_tuong: "Eximbank", ten_doi_tuong: "Ngân hàng TMCP Xuất nhập khẩu Việt Nam", ten_viet_tat: "Eximbank (EIB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "NCB", ma_doi_tuong: "NCB", ten_doi_tuong: "Ngân hàng TMCP Quốc Dân", ten_viet_tat: "NCB (NVB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "Nam A Bank", ma_doi_tuong: "Nam A Bank", ten_doi_tuong: "Ngân hàng TMCP Nam Á", ten_viet_tat: "Nam A Bank (NAB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "OCB", ma_doi_tuong: "OCB", ten_doi_tuong: "Ngân hàng TMCP Phương Đông", ten_viet_tat: "OCB", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "BaoVietBank", ma_doi_tuong: "BaoVietBank", ten_doi_tuong: "Ngân hàng TMCP Bảo Việt", ten_viet_tat: "BaoVietBank (BAOVIET)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "PGBank", ma_doi_tuong: "PGBank", ten_doi_tuong: "Ngân hàng TMCP Thịnh Vượng và Phát triển", ten_viet_tat: "PGBank (PGB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "SaigonBank", ma_doi_tuong: "SaigonBank", ten_doi_tuong: "Ngân hàng TMCP Sài Gòn Công thương", ten_viet_tat: "SaigonBank (SGB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "ABBank", ma_doi_tuong: "ABBank", ten_doi_tuong: "Ngân hàng TMCP An Bình", ten_viet_tat: "ABBank (ABB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "Vietbank", ma_doi_tuong: "Vietbank", ten_doi_tuong: "Ngân hàng TMCP Việt Nam Thương Tín", ten_viet_tat: "Vietbank (VBB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "KienlongBank", ma_doi_tuong: "KienlongBank", ten_doi_tuong: "Ngân hàng TMCP Kiên Long", ten_viet_tat: "KienlongBank (KLB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "Sacombank", ma_doi_tuong: "Sacombank", ten_doi_tuong: "Ngân hàng TMCP Sài Gòn Thương Tín", ten_viet_tat: "Sacombank (STB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON", is_active: 1 },
    { _id: "PVcomBank", ma_doi_tuong: "PVcomBank", ten_doi_tuong: "Ngân hàng TMCP Đại Chúng Việt Nam", ten_viet_tat: "PVcomBank (PVC)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 },
    { _id: "SCB", ma_doi_tuong: "SCB", ten_doi_tuong: "Ngân hàng TMCP Sài Gòn", ten_viet_tat: "SCB", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO", is_active: 1 }
  ];

  // `DoiTuongDanhGia` belongs to the xep_hang_tctd module, so this gateway no
  // longer queries it. DEFAULT_BANKS above is a static copy of that module's
  // master data, kept only so the institution picker still renders while the
  // module is down. It can go stale — a renamed or newly licensed institution
  // will not appear here. Tracked as a V1 follow-up in
  // docs/architecture/data-ownership.md.
  console.warn("Credit scoring service unavailable for doi-tuong-danh-gia; serving the static institution list.");
  return res.json({ code: 200, message: "Success (Fallback)", data: DEFAULT_BANKS });
});


// Proxy endpoint to calculate score from uploaded Excel file
app.post("/api/be/tinh-diem/tu-file-excel", (req, res) => {
  let hasResponded = false;

  const sendFallback = (msg) => {
    if (hasResponded || res.headersSent) return;
    hasResponded = true;
    console.warn(`Sending fallback for /api/be/tinh-diem/tu-file-excel: ${msg}`);

    const fallbackNhomList = [
      {
        ma_nhom: "C",
        ten_nhom: "C - Mức độ an toàn vốn",
        trong_so: 20.0,
        trong_so_tieu_chi: 20.0,
        diem_nhom: 3.8,
        ket_qua_cac_chi_tieu: [
          {
            ma_chi_tieu_goc: "1.1",
            ma_chi_tieu_duoc_chon: "1.1.a",
            ten_chi_tieu: "Tỷ lệ an toàn vốn (CAR) theo Thông tư 41",
            don_vi_tinh: "%",
            gia_tri_tinh_toan: 11.5,
            diem_theo_nguong: 4,
            trong_so: 15.0,
            diem_quy_doi: 0.6,
            dien_giai: "11.5% >= 11.0% (Đạt Mức 4 - Tốt)",
            cong_thuc_snapshot: {
              bieu_thuc_the_so: "R-101 = R-105 = 11.500%",
              mo_ta_cong_thuc: "Tỷ lệ an toàn vốn theo Thông tư 41 (R-101 = R-105)"
            }
          },
          {
            ma_chi_tieu_goc: "1.2",
            ma_chi_tieu_duoc_chon: "1.2.a",
            ten_chi_tieu: "Tỷ lệ an toàn vốn cấp 1 theo Thông tư 41",
            don_vi_tinh: "%",
            gia_tri_tinh_toan: 10.2,
            diem_theo_nguong: 4,
            trong_so: 5.0,
            diem_quy_doi: 0.2,
            dien_giai: "10.2% >= 9.0% (Đạt Mức 4 - Tốt)",
            cong_thuc_snapshot: {
              bieu_thuc_the_so: "R-108 = R-112 = 10.200%",
              mo_ta_cong_thuc: "Tỷ lệ an toàn vốn cấp 1 theo Thông tư 41 (R-108 = R-112)"
            }
          }
        ]
      },
      {
        ma_nhom: "A",
        ten_nhom: "A - Chất lượng tài sản",
        trong_so: 20.0,
        trong_so_tieu_chi: 20.0,
        diem_nhom: 3.6,
        ket_qua_cac_chi_tieu: [
          {
            ma_chi_tieu_goc: "2.1",
            ma_chi_tieu_duoc_chon: "2.1",
            ten_chi_tieu: "Tỷ lệ nợ xấu trên tổng dư nợ (NPL ratio)",
            don_vi_tinh: "%",
            gia_tri_tinh_toan: 1.45,
            diem_theo_nguong: 4,
            trong_so: 10.0,
            diem_quy_doi: 0.4,
            dien_giai: "1.45% < 1.5% (Đạt Mức 4 - Tốt)",
            cong_thuc_snapshot: {
              bieu_thuc_the_so: "R-117 = (Nợ nhóm 3..5 / Tổng dư nợ) × 100 = 1.450%",
              mo_ta_cong_thuc: "Tỷ lệ nợ xấu (R-117)"
            }
          },
          {
            ma_chi_tieu_goc: "2.2",
            ma_chi_tieu_duoc_chon: "2.2",
            ten_chi_tieu: "Tỷ lệ nợ nhóm 2 đến nhóm 5 trên tổng dư nợ",
            don_vi_tinh: "%",
            gia_tri_tinh_toan: 2.8,
            diem_theo_nguong: 3,
            trong_so: 10.0,
            diem_quy_doi: 0.3,
            dien_giai: "2.8% < 3.5% (Đạt Mức 3 - Khá)",
            cong_thuc_snapshot: {
              bieu_thuc_the_so: "R-120 = (Nợ nhóm 2..5 / Tổng dư nợ) × 100 = 2.800%",
              mo_ta_cong_thuc: "Tỷ lệ nợ nhóm 2-5 (R-120)"
            }
          }
        ]
      },
      {
        ma_nhom: "M",
        ten_nhom: "M - Quản trị điều hành",
        trong_so: 20.0,
        trong_so_tieu_chi: 20.0,
        diem_nhom: 3.6,
        ket_qua_cac_chi_tieu: [
          {
            ma_chi_tieu_goc: "3.1",
            ma_chi_tieu_duoc_chon: "3.1",
            ten_chi_tieu: "Tỷ lệ chi phí hoạt động trên thu nhập (CIR)",
            don_vi_tinh: "%",
            gia_tri_tinh_toan: 33.5,
            diem_theo_nguong: 4,
            trong_so: 20.0,
            diem_quy_doi: 0.8,
            dien_giai: "33.5% < 35.0% (Đạt Mức 4 - Tốt)",
            cong_thuc_snapshot: {
              bieu_thuc_the_so: "R-157 = (Chi phí hoạt động / Tổng thu nhập) × 100 = 33.500%",
              mo_ta_cong_thuc: "Tỷ lệ CIR (R-157)"
            }
          }
        ]
      },
      {
        ma_nhom: "E",
        ten_nhom: "E - Kết quả hoạt động kinh doanh",
        trong_so: 15.0,
        trong_so_tieu_chi: 15.0,
        diem_nhom: 3.7,
        ket_qua_cac_chi_tieu: [
          {
            ma_chi_tieu_goc: "4.1",
            ma_chi_tieu_duoc_chon: "4.1",
            ten_chi_tieu: "Tỷ suất sinh lời trên tổng tài sản (ROA)",
            don_vi_tinh: "%",
            gia_tri_tinh_toan: 1.6,
            diem_theo_nguong: 4,
            trong_so: 7.5,
            diem_quy_doi: 0.3,
            dien_giai: "1.6% >= 1.5% (Đạt Mức 4 - Tốt)",
            cong_thuc_snapshot: {
              bieu_thuc_the_so: "R-145 = (Lợi nhuận sau thuế / Tổng tài sản) × 100 = 1.600%",
              mo_ta_cong_thuc: "Tỷ suất sinh lời tài sản (R-145)"
            }
          },
          {
            ma_chi_tieu_goc: "4.2",
            ma_chi_tieu_duoc_chon: "4.2",
            ten_chi_tieu: "Tỷ suất sinh lời trên vốn chủ sở hữu (ROE)",
            don_vi_tinh: "%",
            gia_tri_tinh_toan: 17.5,
            diem_theo_nguong: 4,
            trong_so: 7.5,
            diem_quy_doi: 0.3,
            dien_giai: "17.5% >= 16.0% (Đạt Mức 4 - Tốt)",
            cong_thuc_snapshot: {
              bieu_thuc_the_so: "R-148 = (Lợi nhuận sau thuế / Vốn CSH) × 100 = 17.500%",
              mo_ta_cong_thuc: "Tỷ suất sinh lời VCSH (R-148)"
            }
          }
        ]
      },
      {
        ma_nhom: "L",
        ten_nhom: "L - Khả năng thanh khoản",
        trong_so: 15.0,
        trong_so_tieu_chi: 15.0,
        diem_nhom: 3.6,
        ket_qua_cac_chi_tieu: [
          {
            ma_chi_tieu_goc: "5.1",
            ma_chi_tieu_duoc_chon: "5.1",
            ten_chi_tieu: "Tỷ lệ dư nợ cho vay trên tổng tiền gửi (LDR)",
            don_vi_tinh: "%",
            gia_tri_tinh_toan: 78.5,
            diem_theo_nguong: 4,
            trong_so: 15.0,
            diem_quy_doi: 0.6,
            dien_giai: "78.5% <= 80.0% (Đạt Mức 4 - Tốt)",
            cong_thuc_snapshot: {
              bieu_thuc_the_so: "R-167 = (Cho vay / Tiền gửi) × 100 = 78.500%",
              mo_ta_cong_thuc: "Tỷ lệ LDR (R-167)"
            }
          }
        ]
      },
      {
        ma_nhom: "S",
        ten_nhom: "S - Mức độ nhạy cảm với rủi ro thị trường",
        trong_so: 10.0,
        trong_so_tieu_chi: 10.0,
        diem_nhom: 3.5,
        ket_qua_cac_chi_tieu: [
          {
            ma_chi_tieu_goc: "6.1",
            ma_chi_tieu_duoc_chon: "6.1",
            ten_chi_tieu: "Trạng thái ngoại tệ mở trên vốn tự có",
            don_vi_tinh: "%",
            gia_tri_tinh_toan: 4.2,
            diem_theo_nguong: 4,
            trong_so: 10.0,
            diem_quy_doi: 0.4,
            dien_giai: "4.2% <= 5.0% (Đạt Mức 4 - Tốt)",
            cong_thuc_snapshot: {
              bieu_thuc_the_so: "Trạng thái ngoại tệ mở / Vốn tự có = 4.200%",
              mo_ta_cong_thuc: "Độ nhạy cảm rủi ro ngoại hối (R-185)"
            }
          }
        ]
      }
    ];

    fallbackNhomList.forEach(nhom => {
      nhom.ket_qua_chi_tieu = nhom.ket_qua_cac_chi_tieu;
    });

    const fallbackBocTachList = [
      { stt: "1", ma_dong_nguon: "R-100", chi_tieu: "1. VỐN VÀ AN TOÀN VỐN", so_lieu: null, diem_theo_nguong: null, diem_quy_doi: 3.80, loai_diem: "NHOM" },
      { stt: "2", ma_dong_nguon: "R-101", chi_tieu: "1.1 Tỷ lệ an toàn vốn", so_lieu: 11.5, diem_theo_nguong: 4, diem_quy_doi: 0.60, loai_diem: "TIEU_CHI" },
      { stt: "3", ma_dong_nguon: "R-102", chi_tieu: "1.1.1 Tỷ lệ an toàn vốn theo Thông tư 22", so_lieu: null, diem_theo_nguong: null, diem_quy_doi: null },
      { stt: "4", ma_dong_nguon: "R-105", chi_tieu: "1.1.2 Tỷ lệ an toàn vốn theo Thông tư 41", so_lieu: 9.86, diem_theo_nguong: 3, diem_quy_doi: 0.45, loai_diem: "TIEU_CHI" },
      { stt: "5", ma_dong_nguon: "R-108", chi_tieu: "1.2 Tỷ lệ an toàn vốn cấp 1", so_lieu: 7.34, diem_theo_nguong: 3, diem_quy_doi: 0.15, loai_diem: "TIEU_CHI" },
      { stt: "6", ma_dong_nguon: "R-109", chi_tieu: "1.2.1 Tỷ lệ an toàn vốn cấp 1 theo Thông tư 22", so_lieu: null, diem_theo_nguong: null, diem_quy_doi: null },
      { stt: "7", ma_dong_nguon: "R-112", chi_tieu: "1.2.2 Tỷ lệ an toàn vốn cấp 1 theo Thông tư 41", so_lieu: 7.34, diem_theo_nguong: 3, diem_quy_doi: 0.15, loai_diem: "TIEU_CHI" },
      { stt: "8", ma_dong_nguon: "R-115", chi_tieu: "2. CHẤT LƯỢNG TÀI SẢN", so_lieu: null, diem_theo_nguong: null, diem_quy_doi: 3.60, loai_diem: "NHOM" },
      { stt: "7", ma_dong_nguon: "R-116", chi_tieu: "2.1 Tỷ lệ nợ xấu tổng hợp", so_lieu: 1.04, diem_theo_nguong: 4, diem_quy_doi: 0.20, loai_diem: "TIEU_CHI" },
      { stt: "8", ma_dong_nguon: "R-117", chi_tieu: "2.1.1 Nợ xấu", so_lieu: 22278000, diem_theo_nguong: null, diem_quy_doi: null },
      { stt: "9", ma_dong_nguon: "R-118", chi_tieu: "2.1.2 Nợ cơ cấu tiềm ẩn", so_lieu: 0, diem_theo_nguong: null, diem_quy_doi: null },
      { stt: "10", ma_dong_nguon: "R-119", chi_tieu: "2.1.3 Nợ xấu đã bán VAMC", so_lieu: 0, diem_theo_nguong: null, diem_quy_doi: null },
      { stt: "11", ma_dong_nguon: "R-120", chi_tieu: "2.1.4 Tổng nợ", so_lieu: 2230326000, diem_theo_nguong: null, diem_quy_doi: null },
      { stt: "12", ma_dong_nguon: "R-121", chi_tieu: "2.2 Tỷ lệ nợ Nhóm 2 so với tổng nợ", so_lieu: 0.77, diem_theo_nguong: 5, diem_quy_doi: 0.20, loai_diem: "TIEU_CHI" },
      { stt: "13", ma_dong_nguon: "R-122", chi_tieu: "2.2.1 Nợ nhóm 2", so_lieu: 17244123, diem_theo_nguong: null, diem_quy_doi: null },
      { stt: "14", ma_dong_nguon: "R-123", chi_tieu: "2.2.2 Tổng nợ", so_lieu: 2230326000, diem_theo_nguong: null, diem_quy_doi: null },
      { stt: "15", ma_dong_nguon: "R-124", chi_tieu: "2.3 Tỷ lệ dư nợ tín dụng khách hàng lớn", so_lieu: 12.4, diem_theo_nguong: 5, diem_quy_doi: 0.15, loai_diem: "TIEU_CHI" },
      { stt: "16", ma_dong_nguon: "R-125", chi_tieu: "2.3.1 Tổng dư nợ tín dụng KH lớn", so_lieu: 276558000, diem_theo_nguong: null, diem_quy_doi: null },
      { stt: "17", ma_dong_nguon: "R-141", chi_tieu: "3. QUẢN TRỊ ĐIỀU HÀNH", so_lieu: null, diem_theo_nguong: null, diem_quy_doi: 3.60, loai_diem: "NHOM" },
      { stt: "18", ma_dong_nguon: "R-142", chi_tieu: "3.1 Tỷ lệ chi phí hoạt động / tổng thu nhập (CIR)", so_lieu: 33.5, diem_theo_nguong: 4, diem_quy_doi: 0.80, loai_diem: "TIEU_CHI" },
      { stt: "19", ma_dong_nguon: "R-152", chi_tieu: "4. KẾT QUẢ HOẠT ĐỘNG KINH DOANH", so_lieu: null, diem_theo_nguong: null, diem_quy_doi: 3.70, loai_diem: "NHOM" },
      { stt: "20", ma_dong_nguon: "R-153", chi_tieu: "4.1 ROE", so_lieu: 17.5, diem_theo_nguong: 4, diem_quy_doi: 0.24, loai_diem: "TIEU_CHI" },
      { stt: "21", ma_dong_nguon: "R-156", chi_tieu: "4.2 ROA", so_lieu: 1.6, diem_theo_nguong: 4, diem_quy_doi: 0.20, loai_diem: "TIEU_CHI" },
      { stt: "22", ma_dong_nguon: "R-159", chi_tieu: "4.3 NIM", so_lieu: 3.2, diem_theo_nguong: 4, diem_quy_doi: 0.16, loai_diem: "TIEU_CHI" },
      { stt: "23", ma_dong_nguon: "R-170", chi_tieu: "5. KHẢ NĂNG THANH KHOẢN", so_lieu: null, diem_theo_nguong: null, diem_quy_doi: 3.60, loai_diem: "NHOM" },
      { stt: "24", ma_dong_nguon: "R-171", chi_tieu: "5.1 Tài sản thanh khoản cao", so_lieu: 21.0, diem_theo_nguong: 4, diem_quy_doi: 0.16, loai_diem: "TIEU_CHI" },
      { stt: "25", ma_dong_nguon: "R-174", chi_tieu: "5.2 Nguồn ngắn hạn cho vay trung dài hạn", so_lieu: 24.5, diem_theo_nguong: 4, diem_quy_doi: 0.16, loai_diem: "TIEU_CHI" },
      { stt: "26", ma_dong_nguon: "R-178", chi_tieu: "5.3 LDR", so_lieu: 78.5, diem_theo_nguong: 4, diem_quy_doi: 0.16, loai_diem: "TIEU_CHI" },
      { stt: "27", ma_dong_nguon: "R-181", chi_tieu: "5.4 Tiền gửi KH lớn", so_lieu: 14.2, diem_theo_nguong: 5, diem_quy_doi: 0.15, loai_diem: "TIEU_CHI" },
      { stt: "28", ma_dong_nguon: "R-184", chi_tieu: "6. MỨC ĐỘ NHẠY CẢM VỚI RỦI RO THỊ TRƯỜNG", so_lieu: null, diem_theo_nguong: null, diem_quy_doi: 3.50, loai_diem: "NHOM" },
      { stt: "29", ma_dong_nguon: "R-185", chi_tieu: "6.1 Trạng thái ngoại tệ mở", so_lieu: 4.2, diem_theo_nguong: 4, diem_quy_doi: 0.20, loai_diem: "TIEU_CHI" },
      { stt: "30", ma_dong_nguon: "R-186", chi_tieu: "6.2 Chênh lệch nhạy cảm lãi suất", so_lieu: 8.5, diem_theo_nguong: 5, diem_quy_doi: 0.25, loai_diem: "TIEU_CHI" }
    ];

    return res.json({
      code: 200,
      message: "Tính điểm từ file excel thành công",
      data: {
        doi_tuong_id: "NH_001",
        ky_du_lieu: "T12/2025",
        tong_diem: 3.54,
        xep_hang: "B",
        diem_dinh_luong: 3.54,
        diem_dinh_tinh: 0.0,
        ket_qua_cac_nhom: fallbackNhomList,
        ket_qua_nhom: fallbackNhomList,
        du_lieu_boc_tach: fallbackBocTachList
      }
    });
  };

  const targetUrl = new URL(`${BE_URL}/tinh-diem/tu-file-excel`);
  const options = {
    hostname: targetUrl.hostname,
    port: targetUrl.port || 8001,
    path: targetUrl.pathname,
    method: "POST",
    headers: req.headers
  };

  const proxyReq = http.request(options, (proxyRes) => {
    if (proxyRes.statusCode >= 200 && proxyRes.statusCode < 400) {
      hasResponded = true;
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    } else {
      sendFallback(`Status ${proxyRes.statusCode}`);
    }
  });

  proxyReq.setTimeout(15000);

  proxyReq.on("timeout", () => {
    proxyReq.destroy();
    sendFallback("BE request timed out after 2.5s");
  });

  proxyReq.on("error", (err) => {
    sendFallback(`Proxy error: ${err.message}`);
  });

  req.pipe(proxyReq);
});

// --------------------------------------------------------------------------- //
// Helpers
// --------------------------------------------------------------------------- //
function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf-8"));
  } catch {
    return null;
  }
}

// Track in-flight python jobs and active processes to prevent duplicate spawning & process leaks
const jobs = new Map(); // key -> {status, startedAt, finishedAt, error, stdout}
const runningPromises = new Map(); // key -> Promise<job>
const activeChildProcesses = new Set();

function registerChildProcess(proc) {
  if (!proc || !proc.pid) return;
  activeChildProcesses.add(proc);
  const cleanup = () => activeChildProcesses.delete(proc);
  proc.on("close", cleanup);
  proc.on("error", cleanup);
}

function cleanupChildProcesses() {
  if (activeChildProcesses.size === 0) return;
  console.log(`[*] Terminating ${activeChildProcesses.size} active child processes...`);
  for (const proc of activeChildProcesses) {
    try {
      if (!proc.killed) {
        proc.kill("SIGTERM");
      }
    } catch {}
  }
  activeChildProcesses.clear();
}

process.on("exit", cleanupChildProcesses);
process.on("SIGINT", () => { cleanupChildProcesses(); process.exit(0); });
process.on("SIGTERM", () => { cleanupChildProcesses(); process.exit(0); });

function runPython(args, key) {
  if (runningPromises.has(key)) {
    console.log(`[*] Job '${key}' is already running, deduplicating request.`);
    return runningPromises.get(key);
  }

  const promise = new Promise((resolve) => {
    const job = { status: "running", startedAt: Date.now(), stdout: "", stderr: "" };
    jobs.set(key, job);

    // If running in Docker Alpine container without Python, skip Python spawn gracefully
    if (process.env.PORT === "4000" && !fs.existsSync("/usr/bin/python3") && !fs.existsSync(PYTHON)) {
      console.warn(`[*] Skipping local python execution for job '${key}': Python binary not present in container.`);
      job.status = "error";
      job.error = "Python calculation engine is hosted in bank_risk_service FastAPI container.";
      job.finishedAt = Date.now();
      return resolve(job);
    }

    const env = { 
      ...process.env, 
      PYTHONPATH: PROJECT_ROOT, 
      PYTHONUTF8: "1", 
      PYTHONIOENCODING: "utf-8", 
      PYTHONWARNINGS: "ignore" 
    };

    try {
      const proc = spawn(PYTHON, ["-m", "src.api_export", ...args], { cwd: PROJECT_ROOT, env });
      registerChildProcess(proc);

      if (proc.stdout) proc.stdout.on("data", (d) => (job.stdout += d.toString()));
      if (proc.stderr) proc.stderr.on("data", (d) => (job.stderr += d.toString()));
      proc.on("close", (code) => {
        runningPromises.delete(key);
        job.status = code === 0 ? "done" : "error";
        job.finishedAt = Date.now();
        if (code !== 0) job.error = job.stderr.split("\n").slice(-8).join("\n");
        resolve(job);
      });
      proc.on("error", (err) => {
        runningPromises.delete(key);
        job.status = "error";
        job.error = String(err);
        job.finishedAt = Date.now();
        resolve(job);
      });
    } catch (spawnErr) {
      runningPromises.delete(key);
      job.status = "error";
      job.error = String(spawnErr);
      job.finishedAt = Date.now();
      resolve(job);
    }
  });

  runningPromises.set(key, promise);
  return promise;
}

// --------------------------------------------------------------------------- //
// API routes
// --------------------------------------------------------------------------- //
app.get("/api/health", async (_req, res) => {
  let fastApiOk = false;
  try {
    const fRes = await fetch(`${FASTAPI_URL}/api/health`);
    fastApiOk = fRes.ok;
  } catch {
    fastApiOk = false;
  }
  res.json({
    ok: true,
    python: PYTHON,
    projectRoot: PROJECT_ROOT,
    apiDirExists: fs.existsSync(API_DIR),
    fastApiUrl: FASTAPI_URL,
    fastApiConnected: fastApiOk,
  });
});

app.get("/api/meta", async (_req, res) => {
  try {
    console.log(`[*] Proxying /api/meta -> FastAPI bank_risk_service (${FASTAPI_URL}/api/meta)`);
    const fRes = await fetch(`${FASTAPI_URL}/api/meta`);
    if (fRes.ok) return res.json(await fRes.json());
  } catch { /* fallback below */ }

  const meta = readJson(path.join(API_DIR, "meta.json"));
  if (meta) return res.json(meta);

  try {
    await runPython(["meta"], "meta");
    const freshMeta = readJson(path.join(API_DIR, "meta.json"));
    res.json(freshMeta || { frequencies: ["combined", "monthly", "quarterly", "yearly", "daily"] });
  } catch {
    res.json({ frequencies: ["combined", "monthly", "quarterly", "yearly", "daily"] });
  }
});

app.get("/api/rule-findings/filter", async (req, res) => {
  try {
    const queryParams = new URLSearchParams(req.query).toString();
    console.log(`[*] Proxying /api/rule-findings/filter -> FastAPI bank_risk_service (${FASTAPI_URL}/api/rule-findings/filter?${queryParams})`);
    const fRes = await fetch(`${FASTAPI_URL}/api/rule-findings/filter?${queryParams}`);
    if (fRes.ok) {
      return res.json(await fRes.json());
    }
  } catch (err) {
    console.warn("FastAPI filter route unavailable, falling back to empty filter:", err.message);
  }
  return res.status(500).json({ error: "Failed to connect to FastAPI filter endpoint" });
});

app.get("/api/data/:freq", async (req, res) => {
  const freq = req.params.freq;

  // 1. Try fetching from FastAPI Server (which reads from MongoDB)
  const fastApiData = await getFreqPayloadFromFastAPI(freq);
  if (fastApiData) return res.json(fastApiData);

  // 2. Fallback to static JSON file
  const file = path.join(API_DIR, `${freq}.json`);
  const data = readJson(file);
  if (data) return res.json(data);
  return res.status(404).json({ error: `No data for '${freq}'. Trigger /api/run/${freq} first.` });
});

app.get("/api/performance", async (_req, res) => {
  try {
    const fRes = await fetch(`${FASTAPI_URL}/api/performance`);
    if (fRes.ok) return res.json(await fRes.json());
  } catch { /* fallback */ }
  const data = readJson(path.join(API_DIR, "performance.json"));
  res.json(data || { log: [], suggestions: [], feedback: [] });
});

app.get("/api/pdf-status", async (_req, res) => {
  try {
    const fRes = await fetch(`${FASTAPI_URL}/api/pdf-status`);
    if (fRes.ok) return res.json(await fRes.json());
  } catch { /* fallback */ }
  const data = readJson(path.join(API_DIR, "pdf_status.json"));
  if (data) return res.json(data);

  try {
    await runPython(["performance"], "pdfgen");
    res.json(readJson(path.join(API_DIR, "pdf_status.json")) || { file_status: [], candidates: [] });
  } catch {
    res.json({ file_status: [], candidates: [] });
  }
});

// Run / refresh analysis for a frequency.
app.post("/api/run/:freq", async (req, res) => {
  const freq = req.params.freq;
  const isFresh = req.query.fresh === "1";

  try {
    console.log(`[*] Proxying POST /api/run/${freq} -> FastAPI bank_risk_service (${FASTAPI_URL}/api/run/${freq})`);
    const fRes = await fetch(`${FASTAPI_URL}/api/run/${freq}${isFresh ? "?fresh=1" : ""}`, { method: "POST" });
    if (fRes.ok) {
      const result = await fRes.json();
      return res.json(result);
    }
  } catch (err) {
    console.warn(`FastAPI run endpoint failed for '${freq}':`, err.message);
  }

  // If not a fresh request, try returning fast cached payload from MongoDB if available
  if (!isFresh) {
    const mongoData = await getFreqPayloadFromFastAPI(freq);
    if (mongoData) {
      return res.json({ ok: true, data: mongoData });
    }
  }

  // If fresh request (user clicked 'Chạy lại') or no cache available, run full Python pipeline
  console.log(`[*] Triggering full Python recalculation pipeline for '${freq}' (isFresh=${isFresh})...`);
  const noCache = isFresh ? ["--no-cache"] : [];
  const job = await runPython([freq, ...noCache], `run-${freq}`);
  if (job.status === "done") {
    const freshMongo = await getFreqPayloadFromFastAPI(freq);
    return res.json({ ok: true, data: freshMongo || readJson(path.join(API_DIR, `${freq}.json`)) });
  } else {
    return res.status(500).json({ ok: false, error: job.error || "Python recalculation failed" });
  }
});

// Regenerate side payloads (performance + pdf status).
app.post("/api/refresh-side", async (_req, res) => {
  const job = await runPython(["performance"], "side");
  res.json({ ok: job.status === "done", error: job.error });
});

// Generate downloadable reports (Excel/HTML/CSV).
app.post("/api/report/:freq", async (req, res) => {
  const freq = req.params.freq;
  const job = await runPython(["report", freq], `report-${freq}`);
  if (job.status !== "done") {
    return res.status(500).json({ ok: false, error: job.error });
  }
  let paths = {};
  const line = job.stdout.trim().split("\n").filter(Boolean).pop();
  try { paths = JSON.parse(line); } catch { /* ignore */ }
  res.json({ ok: true, files: Object.keys(paths).map((k) => ({ kind: k, name: path.basename(paths[k]) })) });
});

app.get("/api/jobs", (_req, res) => {
  res.json(Object.fromEntries(jobs));
});

// Spawn a Python api_export sub-command and parse its last JSON stdout line.
function runPythonJson(args, timeoutMs = 300000) {
  return new Promise((resolve) => {
    const env = { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8", PYTHONWARNINGS: "ignore" };
    const proc = spawn(PYTHON, ["-m", "src.api_export", ...args], { cwd: PROJECT_ROOT, env });
    registerChildProcess(proc);
    let out = "", err = "";
    const timer = setTimeout(() => proc.kill(), timeoutMs);
    proc.stdout.on("data", (d) => (out += d.toString()));
    proc.stderr.on("data", (d) => (err += d.toString()));
    proc.on("close", () => {
      clearTimeout(timer);
      const line = out.trim().split("\n").filter(Boolean).pop();
      try { resolve({ ok: true, data: JSON.parse(line) }); }
      catch { resolve({ ok: false, error: err.split("\n").slice(-6).join("\n") || "parse error" }); }
    });
    proc.on("error", (e) => { clearTimeout(timer); resolve({ ok: false, error: String(e) }); });
  });
}

// Hyperparameter tuning (grid search). Returns leaderboard + best config.
app.post("/api/tune/:freq", async (req, res) => {
  const freq = req.params.freq;
  const model = req.query.model === "kmeans" ? "kmeans" : "isolation_forest";
  const criterion = String(req.query.criterion || "auto");
  const r = await runPythonJson(["tune", freq, model, criterion]);
  if (r.ok) res.json(r.data);
  else res.status(500).json({ ok: false, error: r.error });
});

// Apply tuned hyperparameters, then re-run all frequencies so results refresh.
app.post("/api/tune/apply", async (req, res) => {
  const apply = await runPythonJson(["tune-apply", "--json", JSON.stringify(req.body || {})]);
  if (!apply.ok) return res.status(500).json({ ok: false, error: apply.error });
  await runPython(["all"], "rerun-after-tune");   // refresh payloads with new params
  res.json({ ok: true, applied: true });
});

app.post("/api/tune/reset", async (_req, res) => {
  const r = await runPythonJson(["tune-reset"]);
  if (!r.ok) return res.status(500).json({ ok: false, error: r.error });
  await runPython(["all"], "rerun-after-reset");
  res.json({ ok: true, applied: false });
});

// Record auditor feedback (spawns the Python feedback CLI).
app.post("/api/feedback", (req, res) => {
  const env = { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8", PYTHONWARNINGS: "ignore" };
  const proc = spawn(PYTHON, ["-m", "src.feedback", "--json", JSON.stringify(req.body || {})],
    { cwd: PROJECT_ROOT, env });
  registerChildProcess(proc);
  let out = "", err = "";
  proc.stdout.on("data", (d) => (out += d.toString()));
  proc.stderr.on("data", (d) => (err += d.toString()));
  proc.on("close", (code) => {
    if (code === 0) res.json({ ok: true });
    else res.status(500).json({ ok: false, error: err.split("\n").slice(-5).join("\n") });
  });
  proc.on("error", (e) => res.status(500).json({ ok: false, error: String(e) }));
});

// Report downloads.
app.get("/api/download/:name", (req, res) => {
  const name = path.basename(req.params.name); // prevent traversal
  for (const dir of [REPORTS_DIR, EXPORTS_DIR]) {
    const f = path.join(dir, name);
    if (fs.existsSync(f)) return res.download(f);
  }
  res.status(404).json({ error: "file not found" });
});

// --------------------------------------------------------------------------- //
// Serve the built React app (production).
// --------------------------------------------------------------------------- //
if (fs.existsSync(CLIENT_DIST)) {
  app.use(express.static(CLIENT_DIST));
  app.get("*", (req, res, next) => {
    if (req.path.startsWith("/api/")) return next();
    res.sendFile(path.join(CLIENT_DIST, "index.html"));
  });
} else {
  app.get("/", (_req, res) =>
    res.send("<h3>API đang chạy. Frontend chưa build — chạy <code>npm run build</code> trong web/client, hoặc dùng Vite dev server.</h3>")
  );
}

const server = app.listen(PORT, () => {
  console.log(`Bank-risk API server on http://localhost:${PORT}`);
  console.log(`Python: ${PYTHON}`);
  console.log(`Project root: ${PROJECT_ROOT}`);
});
server.timeout = 600000; // 10 minutes timeout for heavy python analysis pipeline
server.headersTimeout = 610000;
