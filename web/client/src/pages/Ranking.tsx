import React, { useState, useMemo, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { api } from "../api";
import RankingBankDetail from "./RankingBankDetail";
import { CalculateScoreModal } from "../components/CalculateScoreModal";

export interface BankRankingItem {
  stt: number;
  code: string;
  name: string;
  type: string;
  score: number;
  grade: "A" | "B" | "C" | "D" | "E";
  overallScore?: number;
  overallGrade?: "A" | "B" | "C" | "D" | "E";
  overallRankStr?: string;
  rankStr: string;
  rawItem?: any;
}

export const GRADE_CONFIG: Record<string, { color: string; bg: string; text: string }> = {
  A: { color: "#10b981", bg: "#ecfdf5", text: "Tốt" },       // Xanh lá cây
  B: { color: "#0284c7", bg: "#f0f9ff", text: "Khá" },       // Xanh da trời
  C: { color: "#eab308", bg: "#fefce8", text: "Trung bình" }, // Vàng
  D: { color: "#f97316", bg: "#fff7ed", text: "Yếu" },       // Cam
  E: { color: "#ef4444", bg: "#fef2f2", text: "Kém" },       // Đỏ
};

export const OBJECT_TYPE_LABEL_MAP: Record<string, string> = {
  "NHTM_QUY_MO_LON": "Ngân hàng thương mại có quy mô lớn",
  "NHTM_QUY_MO_NHO": "Ngân hàng thương mại có quy mô nhỏ",
  "NHTM_VUA_VA_NHO": "Ngân hàng thương mại có quy mô nhỏ",
  "NHTM_CP": "Ngân hàng thương mại có quy mô nhỏ",
  "NHTM_NHA_NUOC": "Ngân hàng thương mại có quy mô lớn",
  "CN_NGAN_HANG_NUOC_NGOAI": "Chi nhánh ngân hàng nước ngoài",
  "CHI_NHANH_NGAN_HANG_NUOC_NGOAI": "Chi nhánh ngân hàng nước ngoài",
  "CONG_TY_TAI_CHINH": "Công ty tài chính",
  "CONG_TY_CHO_THUE_TAI_CHINH": "Công ty cho thuê tài chính",
  "NGAN_HANG_HOP_TAC_XA": "Ngân hàng hợp tác xã",
};

export const FIXED_CLASSIFICATIONS = [
  "Ngân hàng thương mại có quy mô lớn",
  "Ngân hàng thương mại có quy mô nhỏ",
  "Chi nhánh ngân hàng nước ngoài",
  "Công ty tài chính",
  "Công ty cho thuê tài chính",
  "Ngân hàng hợp tác xã",
];

interface GroupWithCriteria {
  ma_nhom: string;
  ten_nhom: string;
  items: { ma_chi_tieu: string; ten_chi_tieu: string }[];
}

export default function Ranking() {
  // Raw data from KetQuaTinhDiem collection (Credit Scoring BE)
  const [ketQuaList, setKetQuaList] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Filters State
  const [period, setPeriod] = useState("2025");
  const [unitType, setUnitType] = useState("ALL");
  const [rankBy, setRankBy] = useState("total"); // "total" | "group_XXX" | "crit_YYY"
  const [gradeFilter, setGradeFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  // Selected bank for detail popup modal
  const [selectedBank, setSelectedBank] = useState<BankRankingItem | null>(null);

  // Calculate score modal state
  const [isCalculateModalOpen, setIsCalculateModalOpen] = useState(false);

  // Helper to parse TMM/YYYY or YYYY into a sortable number (e.g. T12/2025 -> 202512)
const DEFAULT_PERIODS = ["2025"];

  const parsePeriodValue = (p: string) => {
    const match = p.match(/T?(\d+)\/(\d{4})/i);
    if (match) {
      return parseInt(match[2], 10) * 100 + parseInt(match[1], 10);
    }
    const yrMatch = p.match(/^(\d{4})$/);
    if (yrMatch) {
      return parseInt(yrMatch[1], 10) * 100 + 13;
    }
    return 0;
  };

  const [allPeriods, setAllPeriods] = useState<string[]>(DEFAULT_PERIODS);

  // Re-fetch KetQuaTinhDiem specifically for selected period
  useEffect(() => {
    setLoading(true);
    api.ketQuaTinhDiem(period === "ALL" ? undefined : period)
      .then((res: any) => {
        const items = Array.isArray(res) ? res : (res?.data || []);
        setKetQuaList(items);
      })
      .catch((err: any) => {
        console.warn("Failed to load KetQuaTinhDiem from BE API:", err);
      })
      .finally(() => setLoading(false));
  }, [period]);

  // Dynamically available periods from KetQuaTinhDiem (sorted chronologically descending: T12/2025 -> T11/2025 ...)
  const availablePeriods = useMemo<string[]>(() => {
    const fromList = (Array.from(new Set(ketQuaList.map((s: any) => String(s.ky_du_lieu)))) as string[])
      .filter(Boolean);
    const combined = Array.from(new Set([...allPeriods, ...fromList]));
    return combined.sort((a, b) => parsePeriodValue(b) - parsePeriodValue(a));
  }, [allPeriods, ketQuaList]);

  // Nested hierarchy of Groups -> Criteria of each group
  const groupsWithCriteria = useMemo<GroupWithCriteria[]>(() => {
    const groupMap = new Map<string, { ten_nhom: string; critMap: Map<string, string> }>();

    ketQuaList.forEach((item: any) => {
      (item.ket_qua_cac_nhom || []).forEach((g: any) => {
        const ma_nhom = String(g.ma_nhom || "");
        if (!ma_nhom) return;

        if (!groupMap.has(ma_nhom)) {
          groupMap.set(ma_nhom, {
            ten_nhom: g.ten_nhom || `Nhóm ${ma_nhom}`,
            critMap: new Map<string, string>(),
          });
        }

        const entry = groupMap.get(ma_nhom)!;
        (g.ket_qua_cac_chi_tieu || []).forEach((c: any) => {
          const code = String(c.ma_chi_tieu_goc || c.ma_chi_tieu_duoc_chon || "");
          if (code && !entry.critMap.has(code)) {
            entry.critMap.set(code, c.ten_chi_tieu || code);
          }
        });
      });
    });

    return Array.from(groupMap.entries()).map(([ma_nhom, val]) => ({
      ma_nhom,
      ten_nhom: val.ten_nhom,
      items: Array.from(val.critMap.entries()).map(([ma_chi_tieu, ten_chi_tieu]) => ({
        ma_chi_tieu,
        ten_chi_tieu,
      })),
    }));
  }, [ketQuaList]);

  // Map KetQuaTinhDiem items to BankRankingItem (DYNAMIC SORTING & SCORING BY rankBy)
  const bankList = useMemo(() => {
    if (!ketQuaList || ketQuaList.length === 0) return [];

    // Filter by period first if selected
    const periodFiltered = period === "ALL" 
      ? ketQuaList 
      : ketQuaList.filter((s: any) => String(s.ky_du_lieu) === period);

    // Compute overall rank map based on s.tong_diem descending across all banks in period
    const overallSorted = [...periodFiltered].sort((a: any, b: any) => (b.tong_diem ?? 0) - (a.tong_diem ?? 0));
    const overallRankMap = new Map<string, { rankStr: string; overallScore: number; overallGrade: "A" | "B" | "C" | "D" | "E" }>();
    
    overallSorted.forEach((s: any, idx: number) => {
      const code = s.ma_doi_tuong || s.doi_tuong_id;
      const rawTot = s.tong_diem ?? 0;
      const ovScore = Math.round(rawTot * 100) / 100;
      let ovGrade: "A" | "B" | "C" | "D" | "E" = (s.xep_hang as any) || "C";
      if (!["A", "B", "C", "D", "E"].includes(ovGrade)) {
        if (ovScore >= 4.5) ovGrade = "A";
        else if (ovScore >= 4.0) ovGrade = "B";
        else if (ovScore >= 3.0) ovGrade = "C";
        else if (ovScore >= 2.0) ovGrade = "D";
        else ovGrade = "E";
      }
      if (code) {
        overallRankMap.set(code, {
          rankStr: `${idx + 1}/${overallSorted.length}`,
          overallScore: ovScore,
          overallGrade: ovGrade,
        });
      }
    });

    // Calculate score for each document depending on rankBy choice
    const mapped = periodFiltered.map((s: any, idx: number) => {
      let rawScore = 0;

      if (rankBy === "total") {
        rawScore = s.tong_diem ?? 0;
      } else if (rankBy.startsWith("group_")) {
        const groupCode = rankBy.replace("group_", "");
        const groupObj = (s.ket_qua_cac_nhom || []).find((g: any) => String(g.ma_nhom) === groupCode);
        rawScore = groupObj?.diem_nhom ?? 0;
      } else if (rankBy.startsWith("crit_")) {
        const critCode = rankBy.replace("crit_", "");
        let foundCrit: any = null;
        for (const g of s.ket_qua_cac_nhom || []) {
          for (const c of g.ket_qua_cac_chi_tieu || []) {
            if (String(c.ma_chi_tieu_goc) === critCode || String(c.ma_chi_tieu_duoc_chon) === critCode) {
              foundCrit = c;
              break;
            }
          }
          if (foundCrit) break;
        }
        rawScore = foundCrit?.diem_quy_doi ?? foundCrit?.diem_theo_nguong ?? foundCrit?.gia_tri_tinh_toan ?? 0;
      }

      // Score rounded to 2 decimals
      const score = Math.round(rawScore * 100) / 100;

      // Grade classification based on overall tong_diem
      const overallScore = s.tong_diem ?? score;
      let grade: "A" | "B" | "C" | "D" | "E" = (s.xep_hang as any) || "C";
      if (!["A", "B", "C", "D", "E"].includes(grade)) {
        if (overallScore >= 4.5) grade = "A";
        else if (overallScore >= 4.0) grade = "B";
        else if (overallScore >= 3.0) grade = "C";
        else if (overallScore >= 2.0) grade = "D";
        else grade = "E";
      }

      const bankCode = s.ma_doi_tuong || s.doi_tuong_id || `NH_${idx + 1}`;
      const shortBrandName = s.ma_doi_tuong || bankCode;
      const fullName = s.ten_doi_tuong || bankCode;
      
      // Map classification label from Figure 2
      const rawType = s.ma_loai_doi_tuong || "";
      const typeStr = OBJECT_TYPE_LABEL_MAP[rawType] || rawType || "Ngân hàng thương mại có quy mô lớn";

      const ovInfo = overallRankMap.get(bankCode) || {
        rankStr: `${idx + 1}/${periodFiltered.length}`,
        overallScore: Math.round((s.tong_diem ?? score) * 100) / 100,
        overallGrade: grade,
      };

      return {
        code: bankCode,
        name: shortBrandName,
        fullName: fullName,
        type: typeStr,
        score,
        grade,
        overallScore: ovInfo.overallScore,
        overallGrade: ovInfo.overallGrade,
        overallRankStr: ovInfo.rankStr,
        rawItem: s,
      };
    });

    // Sort descending by score
    const sorted = [...mapped].sort((a, b) => b.score - a.score);

    return sorted.map((b, idx) => ({
      ...b,
      stt: idx + 1,
      rankStr: `${idx + 1}/${sorted.length}`,
    }));
  }, [ketQuaList, period, rankBy]);

  // Available classifications for filter
  const availableClassifications = useMemo<string[]>(() => {
    const fromData = Array.from(new Set(bankList.map((b) => b.type))).filter(Boolean);
    return Array.from(new Set([...FIXED_CLASSIFICATIONS, ...fromData]));
  }, [bankList]);

  // Filtered dataset
  const filteredBanks = useMemo(() => {
    return bankList.filter((b) => {
      const matchSearch =
        !search ||
        b.code.toLowerCase().includes(search.toLowerCase()) ||
        b.name.toLowerCase().includes(search.toLowerCase());
      const matchType = unitType === "ALL" || b.type === unitType;
      // Only apply grade filter when rankBy is "total"
      const matchGrade = rankBy !== "total" || gradeFilter === "ALL" || b.grade === gradeFilter;
      return matchSearch && matchType && matchGrade;
    });
  }, [bankList, search, unitType, gradeFilter, rankBy]);

  // Grade counts
  const gradeCounts = useMemo(() => {
    const counts: Record<string, number> = { A: 0, B: 0, C: 0, D: 0, E: 0 };
    filteredBanks.forEach((b) => {
      if (counts[b.grade] !== undefined) counts[b.grade]++;
    });
    return counts;
  }, [filteredBanks]);

  // Pagination State (25 items per page)
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 25;

  // Reset to page 1 when any filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [period, unitType, rankBy, gradeFilter, search]);

  const paginatedBanks = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredBanks.slice(start, start + pageSize);
  }, [filteredBanks, currentPage, pageSize]);

  const totalPages = Math.max(1, Math.ceil(filteredBanks.length / pageSize));

  // Top 10 for bar chart
  const top10Chart = useMemo(() => {
    return [...filteredBanks].sort((a, b) => b.score - a.score).slice(0, 10);
  }, [filteredBanks]);

  // Function to export detailed ranking table to Excel
  const handleExportExcel = () => {
    if (!filteredBanks || filteredBanks.length === 0) {
      alert("Không có dữ liệu để xuất Excel!");
      return;
    }

    const periodStr = period === "ALL" ? "Tất cả các kỳ" : `Kỳ ${period}`;

    let tableHtml = `
      <html xmlns:o="urn:schemas-microsoft-microsoft-com:office:office" 
            xmlns:x="urn:schemas-microsoft-microsoft-com:office:excel" 
            xmlns="http://www.w3.org/TR/REC-html40">
      <head>
        <meta charset="utf-8"/>
        <!--[if gte mso 9]>
        <xml>
          <x:ExcelWorkbook>
            <x:ExcelWorksheets>
              <x:ExcelWorksheet>
                <x:Name>XepHang_TCTD</x:Name>
                <x:WorksheetOptions>
                  <x:DisplayGridlines/>
                </x:WorksheetOptions>
              </x:ExcelWorksheet>
            </x:ExcelWorksheets>
          </x:ExcelWorkbook>
        </xml>
        <![endif]-->
        <style>
          table { border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 13px; }
          th { background-color: #0f172a; color: #ffffff; font-weight: bold; border: 1px solid #cbd5e1; padding: 8px 12px; text-align: center; }
          td { border: 1px solid #cbd5e1; padding: 6px 10px; text-align: left; }
          .num { text-align: right; }
          .center { text-align: center; }
          .txt { mso-number-format: "\\@"; }
          .title { font-size: 16px; font-weight: bold; text-align: center; margin-bottom: 6px; color: #0f172a; }
          .sub { font-size: 12px; color: #64748b; margin-bottom: 12px; text-align: center; }
        </style>
      </head>
      <body>
        <div class="title">BÁO CÁO XẾP HẠNG TỔ CHỨC TÍN DỤNG</div>
        <div class="sub">Kỳ đánh giá: ${periodStr} | Tiêu chí: ${rankByLabel} | Số lượng: ${filteredBanks.length} đơn vị</div>
        <table>
          <thead>
            <tr>
              <th style="width: 50px;">STT</th>
              <th style="width: 110px;">KỲ ĐÁNH GIÁ</th>
              <th style="width: 120px;">MÃ ĐƠN VỊ</th>
              <th style="width: 280px;">TÊN TỔ CHỨC TÍN DỤNG</th>
              <th style="width: 260px;">PHÂN LOẠI</th>
              <th style="width: 120px;">${tableScoreHeader}</th>
              <th style="width: 110px;">XẾP HẠNG A–E</th>
              <th style="width: 100px;">THỨ HẠNG</th>
            </tr>
          </thead>
          <tbody>
    `;

    filteredBanks.forEach((item, index) => {
      const pVal = item.rawItem?.ky_du_lieu ? `Kỳ ${item.rawItem.ky_du_lieu}` : periodStr;
      const scoreVal = typeof item.score === "number" ? item.score.toFixed(2) : item.score;
      const gradeColor = GRADE_CONFIG[item.grade]?.color || "#000000";
      tableHtml += `
        <tr>
          <td class="center">${index + 1}</td>
          <td class="center txt" style="mso-number-format:'\\@';">${pVal}</td>
          <td class="center txt" style="mso-number-format:'\\@';">${item.code}</td>
          <td>${item.name}</td>
          <td>${item.type}</td>
          <td class="num">${scoreVal}</td>
          <td class="center" style="font-weight: bold; color: ${gradeColor};">${item.grade}</td>
          <td class="center txt" style="mso-number-format:'\\@';" x:str="${item.rankStr}">${item.rankStr}</td>
        </tr>
      `;
    });

    tableHtml += `
          </tbody>
        </table>
      </body>
      </html>
    `;

    const blob = new Blob(["\uFEFF" + tableHtml], { type: "application/vnd.ms-excel;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const safePeriod = period.replace(/[\/\\?%*:|"<>]/g, "_");
    link.href = url;
    link.download = `Bang_Xep_Hang_TCTD_${safePeriod}.xls`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Custom Y-Axis tick renderer preventing text clipping at left boundary
  const renderCustomYAxisTick = ({ x, y, payload }: any) => {
    const fullText = String(payload.value || "");
    // Truncate cleanly if > 34 chars to guarantee zero left-side clipping
    const displayVal = fullText.length > 34 ? fullText.substring(0, 32) + "..." : fullText;
    return (
      <g transform={`translate(${x},${y})`}>
        <text
          x={-10}
          y={4}
          textAnchor="end"
          fill="#334155"
          fontSize={13}
          fontWeight={600}
        >
          {displayVal}
        </text>
      </g>
    );
  };

  // Title label for RankBy selection
  const rankByLabel = useMemo(() => {
    if (rankBy === "total") return "Theo Tổng điểm";
    if (rankBy.startsWith("group_")) {
      const gCode = rankBy.replace("group_", "");
      let gTitle = gCode;
      for (const g of groupsWithCriteria) {
        if (g.ma_nhom === gCode) {
          gTitle = g.ten_nhom;
          break;
        }
      }
      return `Theo Nhóm tiêu chí: ${gTitle}`;
    }
    if (rankBy.startsWith("crit_")) {
      const cCode = rankBy.replace("crit_", "");
      let cTitle = cCode;
      for (const g of groupsWithCriteria) {
        const found = g.items.find((item) => item.ma_chi_tieu === cCode);
        if (found) {
          cTitle = found.ten_chi_tieu;
          break;
        }
      }
      return `Theo Chỉ tiêu: ${cTitle}`;
    }
    return "Theo Tổng điểm";
  }, [rankBy, groupsWithCriteria]);

  // Column header for score in data table
  const tableScoreHeader = useMemo(() => {
    if (rankBy === "total") return "TỔNG ĐIỂM";
    if (rankBy.startsWith("group_")) return "ĐIỂM NHÓM";
    if (rankBy.startsWith("crit_")) return "GIÁ TRỊ CHỈ TIÊU";
    return "TỔNG ĐIỂM";
  }, [rankBy]);

  return (
    <div style={{ fontFamily: "Inter, system-ui, sans-serif", color: "#1e293b" }}>
      {/* Top Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
        }}
      >
        <h2 style={{ fontSize: 24, fontWeight: 800, margin: 0, letterSpacing: "-0.02em", color: "#0f172a" }}>
          XẾP HẠNG TỔ CHỨC TÍN DỤNG
        </h2>
        <button
          onClick={() => setIsCalculateModalOpen(true)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 20px",
            background: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
            color: "#ffffff",
            borderRadius: 10,
            border: "none",
            fontSize: 14,
            fontWeight: 700,
            cursor: "pointer",
            boxShadow: "0 4px 12px rgba(37, 99, 235, 0.25)",
            transition: "all 0.2s ease",
          }}
        >
          <span style={{ fontSize: 16 }}>⚡</span> Tính điểm
        </button>
      </div>

      {/* Filter Control Bar */}
      <div
        style={{
          background: "#ffffff",
          borderRadius: 12,
          padding: "16px 20px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
          marginBottom: 20,
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: rankBy === "total" ? "repeat(auto-fit, minmax(220px, 1fr))" : "repeat(auto-fit, minmax(260px, 1fr))",
            gap: 16,
            marginBottom: 16,
          }}
        >
          {/* Kỳ đánh giá */}
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#475569", marginBottom: 6, letterSpacing: "0.04em" }}>
              KỲ ĐÁNH GIÁ
            </label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              style={{
                width: "100%",
                padding: "9px 13px",
                borderRadius: 8,
                border: "1px solid #cbd5e1",
                fontSize: 14,
                fontWeight: 500,
                outline: "none",
                background: "#f8fafc",
              }}
            >
              {availablePeriods.map((p) => (
                <option key={p} value={p}>
                  Kỳ {p}
                </option>
              ))}
            </select>
          </div>

          {/* PHÂN LOẠI (Hình 2) */}
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#475569", marginBottom: 6, letterSpacing: "0.04em" }}>
              PHÂN LOẠI
            </label>
            <select
              value={unitType}
              onChange={(e) => setUnitType(e.target.value)}
              style={{
                width: "100%",
                padding: "9px 13px",
                borderRadius: 8,
                border: "1px solid #cbd5e1",
                fontSize: 14,
                fontWeight: 500,
                outline: "none",
                background: "#f8fafc",
              }}
            >
              <option value="ALL">Tất cả phân loại</option>
              {availableClassifications.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* XẾP HẠNG THEO */}
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#475569", marginBottom: 6, letterSpacing: "0.04em" }}>
              XẾP HẠNG THEO
            </label>
            <select
              value={rankBy}
              onChange={(e) => setRankBy(e.target.value)}
              style={{
                width: "100%",
                padding: "9px 13px",
                borderRadius: 8,
                border: "1px solid #cbd5e1",
                fontSize: 14,
                fontWeight: 500,
                outline: "none",
                background: "#f8fafc",
              }}
            >
              <option value="total">Tổng điểm</option>
              
              {groupsWithCriteria.map((g) => (
                <optgroup key={"group_hdr_" + g.ma_nhom} label={`NHÓM: ${g.ten_nhom.toUpperCase()}`}>
                  <option value={"group_" + g.ma_nhom}>
                    -- Tổng điểm nhóm: {g.ten_nhom}
                  </option>
                  {g.items.map((c) => (
                    <option key={"crit_" + c.ma_chi_tieu} value={"crit_" + c.ma_chi_tieu}>
                      &nbsp;&nbsp;&nbsp;• {c.ten_chi_tieu}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          {/* MỨC XẾP HẠNG - INVISIBLE WHEN RANKING BY GROUP OR CRITERION */}
          {rankBy === "total" && (
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#475569", marginBottom: 6, letterSpacing: "0.04em" }}>
                MỨC XẾP HẠNG
              </label>
              <select
                value={gradeFilter}
                onChange={(e) => setGradeFilter(e.target.value)}
                style={{
                  width: "100%",
                  padding: "9px 13px",
                  borderRadius: 8,
                  border: "1px solid #cbd5e1",
                  fontSize: 14,
                  fontWeight: 500,
                  outline: "none",
                  background: "#f8fafc",
                }}
              >
                <option value="ALL">Tất cả mức xếp hạng</option>
                <option value="A">Hạng A</option>
                <option value="B">Hạng B</option>
                <option value="C">Hạng C</option>
                <option value="D">Hạng D</option>
                <option value="E">Hạng E</option>
              </select>
            </div>
          )}
        </div>

        {/* Search Line */}
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <div style={{ position: "relative", flex: 1, maxWidth: 360 }}>
            <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8", fontSize: 14 }}>
              🔍
            </span>
            <input
              type="text"
              placeholder="Tìm tên hoặc mã đơn vị..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px 8px 36px",
                borderRadius: 8,
                border: "1px solid #cbd5e1",
                fontSize: 13,
                outline: "none",
              }}
            />
          </div>
        </div>
      </div>

      {/* GRADE COUNTER BADGES ROW - INVISIBLE WHEN RANKING BY GROUP OR CRITERION */}
      {rankBy === "total" && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            {(["A", "B", "C", "D", "E"] as const).map((g) => (
              <div
                key={g}
                onClick={() => setGradeFilter(gradeFilter === g ? "ALL" : g)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "5px 14px 5px 7px",
                  background: gradeFilter === g ? GRADE_CONFIG[g].bg : "#ffffff",
                  border: `1px solid ${gradeFilter === g ? GRADE_CONFIG[g].color : "#cbd5e1"}`,
                  borderRadius: 20,
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#334155",
                  cursor: "pointer",
                  boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
                }}
              >
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    background: GRADE_CONFIG[g].color,
                    color: "#ffffff",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  {g}
                </span>
                <b>{gradeCounts[g] || 0}</b> đơn vị
              </div>
            ))}
          </div>

          <div style={{ fontSize: 14, color: "#64748b" }}>
            Tổng: <b style={{ color: "#0f172a", fontSize: 15 }}>{filteredBanks.length}</b> tổ chức tín dụng
          </div>
        </div>
      )}

      {/* BIỂU ĐỒ XẾP HẠNG (Top Chart Card) */}
      <div
        style={{
          background: "#ffffff",
          borderRadius: 12,
          padding: "20px 24px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
          marginBottom: 24,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: 16,
          }}
        >
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#94a3b8", letterSpacing: "0.05em", textTransform: "uppercase" }}>
              BIỂU ĐỒ XẾP HẠNG
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 800, color: "#0f172a", margin: "4px 0 0 0" }}>
              {rankByLabel}
            </h3>
          </div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#64748b" }}>Top 10 đơn vị</div>
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "#64748b" }}>Đang tải dữ liệu từ API KetQuaTinhDiem...</div>
        ) : (
          <ResponsiveContainer width="100%" height={410}>
            <BarChart
              data={top10Chart}
              layout="vertical"
              margin={{ top: 10, right: 45, left: 10, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
              <XAxis
                type="number"
                domain={rankBy === "total" ? [0, 5] : [0, "auto"]}
                ticks={rankBy === "total" ? [0, 1, 2, 3, 4, 5] : undefined}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 11, fill: "#94a3b8" }}
              />
              <YAxis
                type="category"
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={renderCustomYAxisTick}
                width={130}
              />
              <Tooltip
                cursor={{ fill: "rgba(241, 245, 249, 0.6)" }}
                formatter={(val: any) => [rankBy === "total" ? `${val} / 5.0 điểm` : `${val}`, rankByLabel]}
                labelFormatter={(label: any) => `Ngân hàng: ${label}`}
                contentStyle={{ borderRadius: 8, border: "1px solid #cbd5e1", fontSize: 12 }}
              />
              <Bar
                dataKey="score"
                radius={[0, 6, 6, 0]}
                barSize={22}
                label={{ position: "right", fill: "#1e293b", fontSize: 12, fontWeight: 700 }}
                onClick={(entry: any) => {
                  const found = bankList.find((b) => b.name === entry.name || b.code === entry.code);
                  if (found) setSelectedBank(found);
                }}
                style={{ cursor: "pointer" }}
              >
                {top10Chart.map((d, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={rankBy === "total" ? (GRADE_CONFIG[d.grade]?.color || "#2563eb") : "#2563eb"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* BẢNG DỮ LIỆU CHI TIẾT (Data Table Card) */}
      <div
        style={{
          background: "#ffffff",
          borderRadius: 12,
          padding: "20px 24px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#94a3b8", letterSpacing: "0.05em", textTransform: "uppercase" }}>
              BẢNG DỮ LIỆU CHI TIẾT
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 800, color: "#0f172a", margin: "4px 0 0 0" }}>
              Xếp hạng {rankByLabel.toLowerCase()} — <span style={{ color: "#64748b", fontWeight: 400 }}>{filteredBanks.length} đơn vị</span>
            </h3>
          </div>

          <button
            onClick={handleExportExcel}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "9px 18px",
              background: "#059669",
              color: "#ffffff",
              border: "none",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              transition: "background 0.2s",
              boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = "#047857")}
            onMouseOut={(e) => (e.currentTarget.style.background = "#059669")}
          >
            📊 Xuất Excel
          </button>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #f1f5f9", color: "#475569", fontSize: 12, fontWeight: 700, letterSpacing: "0.05em" }}>
                <th style={{ padding: "12px 16px", width: 60 }}>STT</th>
                <th style={{ padding: "12px 16px" }}>ĐƠN VỊ</th>
                <th style={{ padding: "12px 16px" }}>PHÂN LOẠI</th>
                <th style={{ padding: "12px 16px", textAlign: "center", width: rankBy === "total" ? 190 : 160 }}>{tableScoreHeader}</th>
                {rankBy === "total" && (
                  <th style={{ padding: "12px 16px", textAlign: "center", width: 140 }}>XẾP HẠNG A–E</th>
                )}
                <th style={{ padding: "12px 16px", textAlign: "right", width: 120 }}>THỨ HẠNG</th>
              </tr>
            </thead>
            <tbody>
              {paginatedBanks.map((b, idx) => {
                const globalIndex = (currentPage - 1) * pageSize + idx + 1;
                return (
                  <tr
                    key={b.code + "_" + idx}
                    onClick={() => setSelectedBank(b)}
                    style={{
                      borderBottom: "1px solid #f8fafc",
                      cursor: "pointer",
                      transition: "background 0.15s",
                    }}
                    onMouseOver={(e) => (e.currentTarget.style.background = "#f8fafc")}
                    onMouseOut={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <td style={{ padding: "14px 16px", color: "#64748b", fontWeight: 600 }}>{globalIndex}</td>
                    <td style={{ padding: "14px 16px" }}>
                      <div style={{ fontWeight: 700, color: "#2563eb", fontSize: 14, textDecoration: "underline", textUnderlineOffset: 3 }}>
                        {b.name}
                      </div>
                      <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{b.fullName}</div>
                    </td>
                    <td style={{ padding: "14px 16px", color: "#334155", fontSize: 13.5 }}>{b.type}</td>
                    
                    {/* SCORE CELL */}
                    <td style={{ padding: "14px 16px", textAlign: "center" }}>
                      {rankBy === "total" ? (
                        <>
                          <div style={{ fontWeight: 800, color: "#1e40af", fontSize: 15, marginBottom: 4 }}>
                            {b.score.toFixed(2)}
                          </div>
                          <div style={{ width: 100, height: 6, background: "#e2e8f0", borderRadius: 3, margin: "0 auto", overflow: "hidden" }}>
                            <div
                              style={{
                                width: `${Math.min(100, (b.score / 5) * 100)}%`,
                                height: "100%",
                                background: GRADE_CONFIG[b.grade]?.color || "#2563eb",
                                borderRadius: 3,
                              }}
                            />
                          </div>
                        </>
                      ) : (
                        <div style={{ fontWeight: 800, color: "#1e40af", fontSize: 15 }}>
                          {b.score.toFixed(2)}
                        </div>
                      )}
                    </td>

                    {/* GRADE CELL: ONLY DISPLAYED WHEN RANKING BY TOTAL SCORE */}
                    {rankBy === "total" && (
                      <td style={{ padding: "14px 16px", textAlign: "center" }}>
                        <span
                          style={{
                            width: 30,
                            height: 30,
                            borderRadius: "50%",
                            background: GRADE_CONFIG[b.grade]?.color || "#2563eb",
                            color: "#ffffff",
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: 14,
                            fontWeight: 700,
                            margin: "0 auto",
                          }}
                        >
                          {b.grade}
                        </span>
                      </td>
                    )}

                    <td style={{ padding: "14px 16px", textAlign: "right", fontWeight: 700, color: "#1e293b", fontSize: 14 }}>
                      {b.rankStr}
                    </td>
                  </tr>
                );
              })}
              {filteredBanks.length === 0 && !loading && (
                <tr>
                  <td colSpan={rankBy === "total" ? 6 : 5} style={{ padding: 32, textAlign: "center", color: "#94a3b8" }}>
                    Chưa có kết quả tính điểm phù hợp với bộ lọc trong collection KetQuaTinhDiem.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* PAGINATION CONTROLS */}
        {filteredBanks.length > 0 && (
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: 20,
              paddingTop: 16,
              borderTop: "1px solid #f1f5f9",
              flexWrap: "wrap",
              gap: 12,
            }}
          >
            <div style={{ fontSize: 13, color: "#64748b" }}>
              Hiển thị <b>{(currentPage - 1) * pageSize + 1}</b> – <b>{Math.min(currentPage * pageSize, filteredBanks.length)}</b> trong tổng số <b>{filteredBanks.length}</b> tổ chức tín dụng (25 bản ghi / trang)
            </div>

            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(1)}
                style={{
                  padding: "6px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: currentPage === 1 ? "#f1f5f9" : "#ffffff",
                  color: currentPage === 1 ? "#94a3b8" : "#334155",
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: currentPage === 1 ? "not-allowed" : "pointer",
                }}
              >
                « Đầu
              </button>
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                style={{
                  padding: "6px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: currentPage === 1 ? "#f1f5f9" : "#ffffff",
                  color: currentPage === 1 ? "#94a3b8" : "#334155",
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: currentPage === 1 ? "not-allowed" : "pointer",
                }}
              >
                ‹ Trước
              </button>

              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter((p) => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 2)
                .map((p, i, arr) => {
                  const prevPage = arr[i - 1];
                  const showEllipsis = prevPage && p - prevPage > 1;
                  return (
                    <React.Fragment key={p}>
                      {showEllipsis && <span style={{ color: "#94a3b8", padding: "0 4px" }}>...</span>}
                      <button
                        onClick={() => setCurrentPage(p)}
                        style={{
                          minWidth: 32,
                          height: 32,
                          borderRadius: 6,
                          border: `1px solid ${currentPage === p ? "#2563eb" : "#cbd5e1"}`,
                          background: currentPage === p ? "#2563eb" : "#ffffff",
                          color: currentPage === p ? "#ffffff" : "#334155",
                          fontSize: 13,
                          fontWeight: currentPage === p ? 700 : 500,
                          cursor: "pointer",
                        }}
                      >
                        {p}
                      </button>
                    </React.Fragment>
                  );
                })}

              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                style={{
                  padding: "6px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: currentPage === totalPages ? "#f1f5f9" : "#ffffff",
                  color: currentPage === totalPages ? "#94a3b8" : "#334155",
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: currentPage === totalPages ? "not-allowed" : "pointer",
                }}
              >
                Sau ›
              </button>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(totalPages)}
                style={{
                  padding: "6px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: currentPage === totalPages ? "#f1f5f9" : "#ffffff",
                  color: currentPage === totalPages ? "#94a3b8" : "#334155",
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: currentPage === totalPages ? "not-allowed" : "pointer",
                }}
              >
                Cuối »
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail View Component */}
      <RankingBankDetail
        bank={selectedBank}
        allKetQuaList={ketQuaList}
        onClose={() => setSelectedBank(null)}
      />

      {/* Calculate Score Modal Component */}
      <CalculateScoreModal
        isOpen={isCalculateModalOpen}
        onClose={() => setIsCalculateModalOpen(false)}
      />
    </div>
  );
}
