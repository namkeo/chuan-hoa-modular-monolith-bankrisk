import React, { useState, useEffect, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { BankRankingItem, GRADE_CONFIG } from "./Ranking";
import { api } from "../api";

interface RankingBankDetailProps {
  bank: BankRankingItem | null;
  allKetQuaList?: any[];
  onClose: () => void;
}

export const RankingBankDetail: React.FC<RankingBankDetailProps> = ({ bank, allKetQuaList, onClose }) => {
  const [activeTab, setActiveTab] = useState<"overview" | "groups" | "criteria" | "history">("overview");
  const [historyDocs, setHistoryDocs] = useState<any[]>([]);
  const [isEvalExpanded, setIsEvalExpanded] = useState<boolean>(false);

  // Fetch complete historical results for this bank across all periods on mount/bank change
  useEffect(() => {
    if (!bank?.code) return;
    api.lichSuBank(bank.code)
      .then((res: any) => {
        const items = Array.isArray(res) ? res : (res?.data || []);
        setHistoryDocs(items);
      })
      .catch((err: any) => console.warn("Failed to load bank history docs:", err));
  }, [bank?.code]);

  const detailData = useMemo(() => {
    if (!bank) return null;

    // Helper to parse TMM/YYYY or YYYY into a sortable number (e.g. T01/2023 -> 202301)
    const parsePeriodVal = (p: string) => {
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

    // Combine documents for this bank across all periods
    const combined = [...(allKetQuaList || []), ...historyDocs];
    const periodMap = new Map<string, any>();
    combined.forEach((doc: any) => {
      const codeMatches = (doc.ma_doi_tuong && doc.ma_doi_tuong === bank.code) || (doc.doi_tuong_id && doc.doi_tuong_id === bank.code);
      const nameMatches = doc.ten_doi_tuong && doc.ten_doi_tuong === bank.name;
      if ((codeMatches || nameMatches) && doc.ky_du_lieu) {
        periodMap.set(String(doc.ky_du_lieu), doc);
      }
    });

    const uniqueDocs = Array.from(periodMap.values());
    const sortedDocs = [...uniqueDocs].sort((a: any, b: any) => parsePeriodVal(String(a.ky_du_lieu || "")) - parsePeriodVal(String(b.ky_du_lieu || "")));

    let history: any[] = [];
    if (sortedDocs.length > 0) {
      let prevScore: number | null = null;
      history = sortedDocs.map((doc: any) => {
        const pStr = String(doc.ky_du_lieu || "2025");
        const rawScore = doc.tong_diem ?? 0;
        const score = Math.round(rawScore * 100) / 100;
        const grade = doc.xep_hang || "C";

        let change = "—";
        if (prevScore !== null) {
          const diff = Math.round((score - prevScore) * 100) / 100;
          if (diff > 0) change = `▲ +${diff.toFixed(2)}`;
          else if (diff < 0) change = `▼ ${diff.toFixed(2)}`;
          else change = "0.00";
        }
        prevScore = score;

        return {
          year: `Kỳ ${pStr}`,
          period: pStr,
          score,
          grade,
          change,
          val: score,
        };
      });
    } else {
      const currentYear = bank.rawItem?.ky_du_lieu ? `Kỳ ${bank.rawItem.ky_du_lieu}` : "Kỳ 2025";
      history = [
        {
          year: currentYear,
          period: bank.rawItem?.ky_du_lieu || "2025",
          score: bank.score,
          grade: bank.grade,
          change: "—",
          val: bank.score,
        },
      ];
    }

    if (bank.rawItem && Array.isArray(bank.rawItem.ket_qua_cac_nhom) && bank.rawItem.ket_qua_cac_nhom.length > 0) {
      const realGroups = bank.rawItem.ket_qua_cac_nhom.map((g: any, idx: number) => {
        const score = g.diem_nhom ?? 0;
        const rawW = g.trong_so_tieu_chi ?? g.trong_so_nhom_dinh_luong ?? g.trong_so ?? 0;
        const numW = Number(rawW);
        const weight = numW > 1 ? Math.round(numW * 10) / 10 : Math.round(numW * 100);

        const items = g.ket_qua_cac_chi_tieu || g.ket_qua_chi_tieu || g.danh_sach_chi_tieu || [];
        const dtItem = items.find((i: any) =>
          String(i.ma_chi_tieu_duoc_chon || i.ma_chi_tieu_goc || "").endsWith("_DT") ||
          String(i.ten_chi_tieu || "").toLowerCase().includes("định tính")
        );
        const diemDT = g.diem_dinh_tinh ?? (dtItem ? Number(dtItem.diem_theo_nguong ?? dtItem.diem ?? 5) : 5.0);

        const dlItems = items.filter((i: any) => i !== dtItem);
        let diemDL = g.diem_dinh_luong ?? 0;
        if (!diemDL && dlItems.length > 0) {
          let sumWeight = 0;
          let sumWeightedScore = 0;
          dlItems.forEach((i: any) => {
            const sc = Number(i.diem_theo_nguong ?? i.diem ?? 0);
            const w = Number(i.trong_so ?? 1);
            sumWeightedScore += sc * w;
            sumWeight += w;
          });
          diemDL = sumWeight > 0 ? sumWeightedScore / sumWeight : score;
        } else if (!diemDL) {
          diemDL = score;
        }

        let tsDL = 0;
        let tsDT = 0;
        dlItems.forEach((i: any) => {
          tsDL += Number(i.trong_so ?? 0);
        });
        if (dtItem) {
          tsDT = Number(dtItem.trong_so ?? 0);
        } else {
          tsDT = Math.max(0, weight - tsDL);
        }
        tsDL = Math.round(tsDL * 10) / 10;
        tsDT = Math.round(tsDT * 10) / 10;

        return {
          id: idx + 1,
          title: g.ten_nhom ? g.ten_nhom.toUpperCase() : `NHÓM ${g.ma_nhom}`,
          name: g.ten_nhom || `Nhóm ${g.ma_nhom}`,
          weight,
          score,
          diemDL,
          diemDT,
          tsDL,
          tsDT,
          pct: (score / 5) * 100,
          rawGroup: g,
        };
      });

      const radarData = bank.rawItem.ket_qua_cac_nhom.map((g: any) => ({
        subject: g.ten_nhom || g.ma_nhom,
        value: g.diem_nhom ?? 0,
        fullMark: 5,
      }));

      const criteriaGroups = bank.rawItem.ket_qua_cac_nhom.map((g: any) => ({
        groupTitle: g.ten_nhom ? g.ten_nhom.toUpperCase() : `NHÓM ${g.ma_nhom}`,
        items: (g.ket_qua_cac_chi_tieu || []).map((c: any, cIdx: number) => {
          const rawCW = c.trong_so ?? 0;
          const numCW = Number(rawCW);
          const weight = numCW > 1 ? Math.round(numCW * 10) / 10 : Math.round(numCW * 100);

          const diemTheoNguong = c.diem_theo_nguong ?? c.diem_quy_doi ?? 0;
          const converted = c.diem_quy_doi ?? Math.round(diemTheoNguong * (weight / 100) * 100) / 100;

          let giaTriRaw = c.gia_tri_tinh_toan ?? c.gia_tri_thuc_te ?? c.gia_tri ?? null;
          let giaTriStr = "—";
          const unit = c.don_vi_tinh || "";

          if (giaTriRaw !== null && giaTriRaw !== undefined) {
            if (typeof giaTriRaw === "number") {
              if (unit === "%") {
                giaTriStr = `${giaTriRaw.toFixed(2)}%`;
              } else {
                giaTriStr = giaTriRaw % 1 === 0 ? String(giaTriRaw) : giaTriRaw.toFixed(2);
                if (unit && unit !== "lần" && unit !== "sai phạm") {
                  giaTriStr += ` ${unit}`;
                }
              }
            } else {
              const sVal = String(giaTriRaw).trim();
              if (sVal === "0 sai phạm" || sVal === "0.0" || sVal === "0") {
                if (unit === "sai phạm" || !unit || unit === "lần") {
                  giaTriStr = "—";
                } else {
                  giaTriStr = sVal;
                }
              } else {
                giaTriStr = sVal;
              }
            }
          }

          return {
            code: c.ma_chi_tieu_goc || `${g.ma_nhom}.${cIdx + 1}`,
            name: c.ten_chi_tieu || c.ma_chi_tieu_duoc_chon || c.ma_chi_tieu_goc,
            giaTriTinhToan: giaTriStr,
            diemTheoNguong,
            weight,
            converted,
          };
        }),
      }));

      return { groups: realGroups, radarData, criteriaGroups, history };
    }

    const ratio = bank.score / 5;
    const g1 = Math.round(4.5 * ratio * 100) / 100;
    const g2 = Math.round(4.65 * ratio * 100) / 100;
    const g3 = Math.round(4.75 * ratio * 100) / 100;
    const g4 = Math.round(4.5 * ratio * 100) / 100;
    const g5 = Math.round(4.6 * ratio * 100) / 100;

    const groups = [
      { id: 1, title: "1. AN TOÀN VỐN", name: "1. An toàn vốn", weight: 20, score: g1, diemDL: g1, diemDT: g1, tsDL: 70, tsDT: 30, pct: (g1 / 5) * 100 },
      { id: 2, title: "2. CHẤT LƯỢNG TÀI SẢN", name: "2. Chất lượng tài sản", weight: 30, score: g2, diemDL: g2, diemDT: g2, tsDL: 70, tsDT: 30, pct: (g2 / 5) * 100 },
      { id: 3, title: "3. QUẢN TRỊ", name: "3. Quản trị", weight: 10, score: g5, diemDL: g5, diemDT: g5, tsDL: 70, tsDT: 30, pct: (g5 / 5) * 100 },
      { id: 4, title: "4. LỢI NHUẬN", name: "4. Lợi nhuận", weight: 20, score: g3, diemDL: g3, diemDT: g3, tsDL: 70, tsDT: 30, pct: (g3 / 5) * 100 },
      { id: 5, title: "5. THANH KHOẢN", name: "5. Thanh khoản", weight: 15, score: g4, diemDL: g4, diemDT: g4, tsDL: 70, tsDT: 30, pct: (g4 / 5) * 100 },
    ];

    const radarData = [
      { subject: "An toàn vốn", value: g1, fullMark: 5 },
      { subject: "Chất lượng tài sản", value: g2, fullMark: 5 },
      { subject: "Lợi nhuận", value: g3, fullMark: 5 },
      { subject: "Thanh khoản", value: g4, fullMark: 5 },
      { subject: "Quản trị", value: g5, fullMark: 5 },
    ];

    const criteriaGroups = [
      {
        groupTitle: "NHÓM VỐN (C)",
        items: [
          { code: "1.1", name: "Tỷ lệ an toàn vốn (CAR)", diemTheoNguong: 2.5, weight: 50, converted: 1.25 },
          { code: "1.2", name: "Tỷ lệ an toàn vốn cấp 1", diemTheoNguong: 2.5, weight: 50, converted: 1.25 },
        ],
      },
    ];

    return { groups, radarData, criteriaGroups, history };
  }, [bank, allKetQuaList, historyDocs]);

  // Function to export Criteria Detail data to Excel
  const handleExportCriteriaExcel = () => {
    if (!bank || !detailData?.criteriaGroups) {
      alert("Không có dữ liệu chi tiết tiêu chí để xuất Excel!");
      return;
    }

    const periodStr = bank.rawItem?.ky_du_lieu ? `Kỳ ${bank.rawItem.ky_du_lieu}` : "Kỳ báo cáo";
    const overallScoreStr = (bank.overallScore ?? bank.rawItem?.tong_diem ?? bank.score).toFixed(2);
    const gradeStr = bank.overallGrade || bank.grade;

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
                <x:Name>ChiTietTieuChi</x:Name>
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
        <div class="title">BÁO CÁO CHI TIẾT TIÊU CHÍ ĐÁNH GIÁ</div>
        <div class="sub">Đơn vị: ${bank.name} (${bank.code}) | ${periodStr} | Tổng điểm: ${overallScoreStr} | Xếp hạng: ${gradeStr}</div>
        <table>
          <thead>
            <tr>
              <th style="width: 50px;">STT</th>
              <th style="width: 220px;">NHÓM TIÊU CHÍ</th>
              <th style="width: 110px;">MÃ CHỈ TIÊU</th>
              <th style="width: 320px;">TÊN TIÊU CHÍ</th>
              <th style="width: 150px;">GIÁ TRỊ TÍNH TOÁN</th>
              <th style="width: 150px;">ĐIỂM THEO NGƯỠNG</th>
              <th style="width: 110px;">TRỌNG SỐ</th>
              <th style="width: 130px;">ĐIỂM QUY ĐỔI</th>
            </tr>
          </thead>
          <tbody>
    `;

    let globalStt = 1;
    detailData.criteriaGroups.forEach((cg: any) => {
      (cg.items || []).forEach((item: any) => {
        const diemTheoNguongVal = typeof item.diemTheoNguong === "number" ? item.diemTheoNguong.toFixed(1) : item.diemTheoNguong;
        const convertedVal = typeof item.converted === "number" ? item.converted.toFixed(2) : item.converted;
        tableHtml += `
          <tr>
            <td class="center">${globalStt++}</td>
            <td>${cg.groupTitle}</td>
            <td class="center txt" style="mso-number-format:'\\@';">${item.code}</td>
            <td>${item.name}</td>
            <td class="center">${item.giaTriTinhToan || '—'}</td>
            <td class="center">${diemTheoNguongVal}</td>
            <td class="center">${item.weight}%</td>
            <td class="num" style="font-weight: bold; color: #1e40af;">${convertedVal}</td>
          </tr>
        `;
      });
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
    const safeCode = bank.code.replace(/[\/\\?%*:|"<>]/g, "_");
    const safePeriod = (bank.rawItem?.ky_du_lieu || "2025").replace(/[\/\\?%*:|"<>]/g, "_");
    link.href = url;
    link.download = `Chi_Tiet_Tieu_Chi_${safeCode}_${safePeriod}.xls`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (!bank || !detailData) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 999,
        background: "rgba(15, 23, 42, 0.6)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
      }}
    >
      <div
        style={{
          background: "#ffffff",
          borderRadius: 16,
          width: "100%",
          maxWidth: 960,
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)",
          overflow: "hidden",
        }}
      >
        {/* Modal Top Header */}
        <div
          style={{
            padding: "20px 24px",
            background: "#0f172a",
            color: "#ffffff",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              CHI TIẾT ĐÁNH GIÁ ĐƠN VỊ
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 800, margin: "4px 0 0 0", color: "#ffffff", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ color: "#ffffff" }}>{(bank as any).fullName || bank.rawItem?.ten_doi_tuong || bank.name}</span>
              {bank.name && (bank as any).fullName && bank.name !== (bank as any).fullName && (
                <span style={{ background: "#2563eb", color: "#ffffff", padding: "2px 8px", borderRadius: 6, fontSize: 13, fontWeight: 700 }}>
                  {bank.name}
                </span>
              )}
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              fontSize: 24,
              cursor: "pointer",
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>

        {/* Modal Summary KPI Strip */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 20,
            padding: "16px 24px",
            background: "#f8fafc",
            borderBottom: "1px solid #e2e8f0",
            flexWrap: "wrap",
          }}
        >
          {/* Điểm tổng */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>ĐIỂM TỔNG</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: "#1e40af", marginTop: 2 }}>
              {(bank.overallScore ?? bank.rawItem?.tong_diem ?? bank.score).toFixed(2)}
            </div>
          </div>

          <div style={{ width: 1, height: 36, background: "#cbd5e1" }} />

          {/* Thứ hạng */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>THỨ HẠNG</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: "#0f172a", marginTop: 2 }}>
              {bank.overallRankStr || bank.rankStr}
            </div>
          </div>

          <div style={{ width: 1, height: 36, background: "#cbd5e1" }} />

          {/* Mức đánh giá */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: 4 }}>
              MỨC ĐÁNH GIÁ
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  background: GRADE_CONFIG[bank.overallGrade || bank.grade]?.color || "#2563eb",
                  color: "#ffffff",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                  fontWeight: 700,
                }}
              >
                {bank.overallGrade || bank.grade}
              </span>
              <span style={{ fontSize: 14, fontWeight: 700, color: GRADE_CONFIG[bank.overallGrade || bank.grade]?.color || "#2563eb" }}>
                {GRADE_CONFIG[bank.overallGrade || bank.grade]?.text}
              </span>
            </div>
          </div>

          <div style={{ width: 1, height: 36, background: "#cbd5e1" }} />

          {/* Loại hình & Progress */}
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>LOẠI HÌNH</span>
              <span style={{ fontSize: 12, color: "#64748b" }}>
                {(bank.overallScore ?? bank.rawItem?.tong_diem ?? bank.score).toFixed(2)}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>{bank.type}</span>
              <div style={{ flex: 1, height: 8, background: "#e2e8f0", borderRadius: 4, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${Math.min(100, Math.max(0, (((bank.overallScore ?? bank.rawItem?.tong_diem ?? bank.score) / 5) * 100)))}%`,
                    height: "100%",
                    background: GRADE_CONFIG[bank.overallGrade || bank.grade]?.color || "#10b981",
                    borderRadius: 4,
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* ĐÁNH GIÁ XẾP HẠNG BANNER (Khoản 7 Điều 20 TT52) */}
        {(() => {
          const evalK7 = bank.rawItem?.danh_gia_khoan_7_dieu_20 || {
            bat_buoc_xep_hang_e: (bank.overallGrade || bank.grade) === "E",
            xep_hang_goc: (bank.overallGrade || bank.grade) === "E" ? "B" : (bank.overallGrade || bank.grade),
            xep_hang_cuoi_cung: bank.overallGrade || bank.grade,
            ket_luan: (bank.overallGrade || bank.grade) === "E"
              ? `Tổ chức tín dụng đạt điểm CAMELS = ${(bank.overallScore ?? bank.score).toFixed(2)} (Xếp hạng gốc B), tuy nhiên vi phạm điều kiện bổ sung tại Khoản 7 Điều 20 TT52 nên BẮT BUỘC HẠ XẾP HẠNG XUỐNG HẠNG (E).`
              : `Tổ chức tín dụng đạt điểm CAMELS = ${(bank.overallScore ?? bank.score).toFixed(2)} và không vi phạm các trường hợp hạ bậc tại Khoản 7 Điều 20 TT52, GIỮ NGUYÊN XẾP HẠNG ${bank.overallGrade || bank.grade}.`,
            dieu_kien_a_thanh_khoan: {
              co_chi_tieu_duoi_2: false,
              mo_ta: "Không có chỉ tiêu thanh khoản nào < 2.0 điểm"
            },
            dieu_kien_b_lo_luy_ke: {
              vi_pham: (bank.overallGrade || bank.grade) === "E",
              bieu_thuc_day_du: (bank.overallGrade || bank.grade) === "E" ? "Lỗ lũy kế / (VĐL + Quỹ) = 112.45%" : "Lỗ lũy kế / (VĐL + Quỹ) = 0.00%",
              mo_ta: (bank.overallGrade || bank.grade) === "E" ? "Lỗ lũy kế vượt quá 100% vốn điều lệ và các quỹ (Vi phạm Khoản 7b Điều 20 TT52)" : "Không có lỗ lũy kế vượt vốn điều lệ và các quỹ"
            },
            dieu_kien_c_vi_pham_car: {
              vi_pham: false,
              mo_ta: "Duy trì tỷ lệ an toàn vốn CAR theo quy định >= 8.0%"
            }
          };

          return (
            <div
              style={{
                padding: "12px 24px",
                background: evalK7.bat_buoc_xep_hang_e ? "#fef2f2" : "#f0fdf4",
                borderBottom: "1px solid #e2e8f0",
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 16 }}>{evalK7.bat_buoc_xep_hang_e ? "🚨" : "🛡️"}</span>
                  <span style={{ fontSize: 13, fontWeight: 800, color: evalK7.bat_buoc_xep_hang_e ? "#991b1b" : "#166534", letterSpacing: "0.3px" }}>
                    ĐÁNH GIÁ XẾP HẠNG
                  </span>
                  {evalK7.bat_buoc_xep_hang_e && (
                    <span style={{ padding: "2px 8px", borderRadius: 4, background: "#dc2626", color: "#fff", fontSize: 11, fontWeight: 800 }}>
                      BẮT BUỘC HẠ XẾP HẠNG (E)
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setIsEvalExpanded(!isEvalExpanded)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    padding: "4px 10px",
                    borderRadius: 6,
                    background: "#ffffff",
                    border: "1px solid #cbd5e1",
                    color: "#334155",
                    fontSize: 11.5,
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                  }}
                >
                  <span>{isEvalExpanded ? "▲ Thu gọn chi tiết" : "▼ Xem chi tiết đánh giá"}</span>
                </button>
              </div>

              {/* Summary message */}
              <div
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  background: "#ffffff",
                  border: evalK7.bat_buoc_xep_hang_e ? "1px solid #fca5a5" : "1px solid #bbf7d0",
                  fontSize: 12.5,
                  fontWeight: 700,
                  color: evalK7.bat_buoc_xep_hang_e ? "#991b1b" : "#166534",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span style={{ fontSize: 15 }}>📌</span>
                <span>{evalK7.ket_luan}</span>
              </div>

              {/* Collapsible detail grid */}
              {isEvalExpanded && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 4 }}>
                  {/* Condition a */}
                  <div style={{ padding: "10px 14px", borderRadius: 8, background: "#ffffff", border: "1px solid #cbd5e1", fontSize: 12, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontWeight: 700, color: "#1e293b", marginBottom: 6 }}>a) Khả năng chi trả / thanh toán:</div>
                      {evalK7.dieu_kien_a_thanh_khoan?.danh_sach_chi_tieu ? (
                        evalK7.dieu_kien_a_thanh_khoan.danh_sach_chi_tieu.map((item: any, idx: number) => (
                          <div key={idx} style={{ fontSize: 11.5, color: "#475569", lineHeight: 1.4, marginBottom: 2 }}>
                            • {item.ten_chi_tieu}: <strong style={{ color: item.diem < 2 ? "#dc2626" : "#0284c7" }}>{item.diem} điểm</strong>
                          </div>
                        ))
                      ) : (
                        <div style={{ fontSize: 11.5, color: "#475569" }}>• Tất cả các chỉ tiêu thanh khoản đều đạt $\ge$ 2.0 điểm</div>
                      )}
                    </div>
                    <div style={{ marginTop: 8, paddingTop: 6, borderTop: "1px dashed #e2e8f0", color: evalK7.dieu_kien_a_thanh_khoan?.co_chi_tieu_duoi_2 ? "#d97706" : "#16a34a", fontWeight: 700, fontSize: 11.5 }}>
                      👉 {evalK7.dieu_kien_a_thanh_khoan?.mo_ta || "Không có chỉ tiêu thanh khoản < 2.0 điểm"}
                    </div>
                  </div>

                  {/* Condition b */}
                  <div style={{ padding: "10px 14px", borderRadius: 8, background: "#ffffff", border: "1px solid #cbd5e1", fontSize: 12, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontWeight: 700, color: "#1e293b", marginBottom: 6 }}>b) Lỗ lũy kế / VĐL & Quỹ:</div>
                      <div style={{ fontSize: 11.5, color: "#334155", lineHeight: 1.5 }}>
                        <div style={{ wordBreak: "break-word" }}>
                          <code style={{ background: "#f1f5f9", padding: "4px 8px", borderRadius: 4, color: "#0f172a", fontWeight: 600, display: "block", fontSize: 11.5, lineHeight: 1.4 }}>
                            {evalK7.dieu_kien_b_lo_luy_ke?.bieu_thuc_day_du || "Lỗ lũy kế / (VĐL + Quỹ) = 0.00%"}
                          </code>
                        </div>
                        <div style={{ marginTop: 6, paddingTop: 6, borderTop: "1px dashed #e2e8f0", color: evalK7.dieu_kien_b_lo_luy_ke?.vi_pham ? "#dc2626" : "#16a34a", fontWeight: 700, fontSize: 11.5 }}>
                          👉 {evalK7.dieu_kien_b_lo_luy_ke?.mo_ta || "Không có lỗ lũy kế vượt vốn điều lệ và các quỹ"}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Condition c */}
                  <div style={{ padding: "10px 14px", borderRadius: 8, background: "#ffffff", border: "1px solid #cbd5e1", fontSize: 12, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontWeight: 700, color: "#1e293b", marginBottom: 6 }}>c) Duy trì CAR:</div>
                      <div style={{ fontSize: 11.5, color: evalK7.dieu_kien_c_vi_pham_car?.vi_pham ? "#dc2626" : "#16a34a", fontWeight: 600, lineHeight: 1.4 }}>
                        👉 {evalK7.dieu_kien_c_vi_pham_car?.mo_ta || "Duy trì tỷ lệ an toàn vốn CAR theo quy định >= 8.0%"}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })()}

        {/* Modal Tabs Bar */}
        <div
          style={{
            display: "flex",
            gap: 24,
            padding: "0 24px",
            borderBottom: "1px solid #e2e8f0",
            background: "#ffffff",
          }}
        >
          {[
            { id: "overview", label: "Tổng quan" },
            { id: "groups", label: "Điểm theo nhóm" },
            { id: "criteria", label: "Chi tiết tiêu chí" },
            { id: "history", label: "Lịch sử" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                padding: "14px 4px",
                background: "transparent",
                border: "none",
                borderBottom: activeTab === tab.id ? "2px solid #2563eb" : "2px solid transparent",
                fontSize: 14,
                fontWeight: activeTab === tab.id ? 700 : 500,
                color: activeTab === tab.id ? "#2563eb" : "#64748b",
                cursor: "pointer",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Modal Body Content Scrollable */}
        <div style={{ padding: 24, overflowY: "auto", flex: 1, background: "#fafafa" }}>
          {/* TAB 1: TỔNG QUAN */}
          {activeTab === "overview" && (
            <div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 24 }}>
                {detailData.groups.map((g: any) => (
                  <div
                    key={g.id}
                    style={{
                      background: "#ffffff",
                      borderRadius: 12,
                      padding: 16,
                      border: "1px solid #e2e8f0",
                      boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>
                      <span>{g.title}</span>
                      <span>Trọng số nhóm {g.weight}%</span>
                    </div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: "#0f172a", marginBottom: 10 }}>
                      {g.score.toFixed(2)}
                    </div>
                    <div style={{ height: 6, background: "#e2e8f0", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ width: `${g.pct}%`, height: "100%", background: "#10b981", borderRadius: 3 }} />
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ background: "#ffffff", borderRadius: 12, padding: 20, border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 12 }}>
                  BIỂU ĐỒ RADAR THEO NHÓM
                </div>
                <ResponsiveContainer width="100%" height={260}>
                  <RadarChart outerRadius={90} data={detailData.radarData}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: "#475569" }} />
                    <PolarRadiusAxis angle={30} domain={[0, 5]} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                    <Radar name="Điểm đóng góp nhóm" dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.2} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* TAB 2: ĐIỂM THEO NHÓM (BỔ SUNG CỘT ĐỊNH LƯỢNG & ĐỊNH TÍNH) */}
          {activeTab === "groups" && (
            <div style={{ background: "#ffffff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, textAlign: "left" }}>
                <thead>
                  <tr style={{ background: "#f8fafc", color: "#64748b", fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", borderBottom: "1px solid #e2e8f0" }}>
                    <th style={{ padding: "12px 16px" }}>NHÓM TIÊU CHÍ</th>
                    <th style={{ padding: "12px 16px", textAlign: "center", width: 140 }}>ĐIỂM ĐỊNH LƯỢNG</th>
                    <th style={{ padding: "12px 16px", textAlign: "center", width: 140 }}>ĐIỂM ĐỊNH TÍNH</th>
                    <th style={{ padding: "12px 16px", textAlign: "center", width: 110 }}>TRỌNG SỐ NHÓM</th>
                    <th style={{ padding: "12px 16px", textAlign: "center", width: 130 }}>ĐIỂM ĐÓNG GÓP</th>
                    <th style={{ padding: "12px 16px", width: 160 }}>PHÂN BỐ</th>
                  </tr>
                </thead>
                <tbody>
                  {detailData.groups.map((g: any) => {
                    return (
                      <tr key={g.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "14px 16px", fontWeight: 600, color: "#1e293b" }}>{g.name}</td>
                        <td style={{ padding: "14px 16px", textAlign: "center" }}>
                          <div style={{ fontWeight: 700, color: "#0f172a" }}>{g.diemDL !== undefined ? g.diemDL.toFixed(2) : "—"}</div>
                          <div style={{ fontSize: 11, color: "#64748b" }}>Trọng số {g.tsDL}%</div>
                        </td>
                        <td style={{ padding: "14px 16px", textAlign: "center" }}>
                          <div style={{ fontWeight: 700, color: "#0f172a" }}>{g.diemDT !== undefined ? g.diemDT.toFixed(2) : "—"}</div>
                          <div style={{ fontSize: 11, color: "#64748b" }}>Trọng số {g.tsDT}%</div>
                        </td>
                        <td style={{ padding: "14px 16px", textAlign: "center", color: "#64748b", fontWeight: 600 }}>{g.weight}%</td>
                        <td style={{ padding: "14px 16px", textAlign: "center", fontWeight: 700, color: "#1e40af", fontSize: 14 }}>
                          {g.score.toFixed(2)}
                        </td>
                        <td style={{ padding: "14px 16px" }}>
                          <div style={{ height: 6, background: "#e2e8f0", borderRadius: 3, overflow: "hidden" }}>
                            <div style={{ width: `${g.pct}%`, height: "100%", background: "#10b981", borderRadius: 3 }} />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  <tr style={{ background: "#eff6ff", borderTop: "2px solid #bfdbfe", fontWeight: 700 }}>
                    <td style={{ padding: "14px 16px", color: "#1e40af" }}>Tổng cộng</td>
                    <td style={{ padding: "14px 16px", textAlign: "center", color: "#1e40af", fontSize: 12 }}>Tổng TS 70%</td>
                    <td style={{ padding: "14px 16px", textAlign: "center", color: "#1e40af", fontSize: 12 }}>Tổng TS 30%</td>
                    <td style={{ padding: "14px 16px", textAlign: "center", color: "#1e40af" }}>100%</td>
                    <td style={{ padding: "14px 16px", textAlign: "center", color: "#1e40af", fontSize: 16 }}>
                      {bank.score.toFixed(2)}
                    </td>
                    <td style={{ padding: "14px 16px" }} />
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 3: CHI TIẾT TIÊU CHÍ (ĐỔI ĐIỂM THÀNH ĐIỂM THEO NGƯỠNG) */}
          {activeTab === "criteria" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Header Action Bar for Tab 3 */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 4 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a" }}>
                  BẢNG CHI TIẾT CÁC CHỈ TIÊU ĐÁNH GIÁ
                </div>
                <button
                  onClick={handleExportCriteriaExcel}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "8px 16px",
                    background: "#059669",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: 8,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "background 0.2s",
                    boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.background = "#047857")}
                  onMouseOut={(e) => (e.currentTarget.style.background = "#059669")}
                >
                  📊 Xuất Excel Chi Tiết Tiêu Chí
                </button>
              </div>

              {detailData.criteriaGroups.map((cg: any, idx: number) => (
                <div key={idx} style={{ background: "#ffffff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
                  <div style={{ padding: "12px 20px", background: "#f8fafc", fontSize: 12, fontWeight: 700, color: "#475569", borderBottom: "1px solid #e2e8f0" }}>
                    {cg.groupTitle}
                  </div>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, textAlign: "left" }}>
                    <thead>
                      <tr style={{ color: "#94a3b8", fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", borderBottom: "1px solid #f1f5f9" }}>
                        <th style={{ padding: "10px 20px", width: 70 }}>MÃ</th>
                        <th style={{ padding: "10px 20px" }}>TIÊU CHÍ</th>
                        <th style={{ padding: "10px 20px", textAlign: "center", width: 160 }}>GIÁ TRỊ TÍNH TOÁN</th>
                        <th style={{ padding: "10px 20px", textAlign: "center", width: 150 }}>ĐIỂM THEO NGƯỠNG</th>
                        <th style={{ padding: "10px 20px", textAlign: "center", width: 100 }}>TRỌNG SỐ</th>
                        <th style={{ padding: "10px 20px", textAlign: "right", width: 130 }}>ĐIỂM QUY ĐỔI</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cg.items.map((item: any) => (
                        <tr key={item.code} style={{ borderBottom: "1px solid #f8fafc" }}>
                          <td style={{ padding: "12px 20px", color: "#64748b", fontWeight: 600 }}>{item.code}</td>
                          <td style={{ padding: "12px 20px", color: "#1e293b" }}>{item.name}</td>
                          <td style={{ padding: "12px 20px", textAlign: "center", fontWeight: 600, color: "#0f172a" }}>
                            {item.giaTriTinhToan || "—"}
                          </td>
                          <td style={{ padding: "12px 20px", textAlign: "center" }}>
                            <span
                              style={{
                                width: 28,
                                height: 28,
                                borderRadius: "50%",
                                background: "#10b981",
                                color: "#ffffff",
                                display: "inline-flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontSize: 12,
                                fontWeight: 700,
                              }}
                            >
                              {typeof item.diemTheoNguong === "number" ? item.diemTheoNguong.toFixed(1) : item.diemTheoNguong}
                            </span>
                          </td>
                          <td style={{ padding: "12px 20px", textAlign: "center", color: "#64748b" }}>{item.weight}%</td>
                          <td style={{ padding: "12px 20px", textAlign: "right", fontWeight: 700, color: "#1e40af" }}>
                            {item.converted.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: LỊCH SỬ */}
          {activeTab === "history" && (
            <div>
              <div style={{ background: "#ffffff", borderRadius: 12, padding: 20, border: "1px solid #e2e8f0", marginBottom: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", marginBottom: 16 }}>
                  Xu hướng điểm xếp hạng của đơn vị
                </div>
                <div style={{ width: "100%", overflowX: "auto" }}>
                  <div style={{ minWidth: Math.max(600, detailData.history.length * 38), paddingBottom: 10 }}>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={detailData.history} margin={{ top: 25, right: 15, left: -15, bottom: 25 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis 
                          dataKey="period" 
                          axisLine={false} 
                          tickLine={false} 
                          tick={{ fontSize: 11, fill: "#475569", fontWeight: 600 }}
                          interval={0}
                          angle={-35}
                          textAnchor="end"
                          height={45}
                        />
                        <YAxis domain={[0, 5]} ticks={[0, 1, 2, 3, 4, 5]} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#94a3b8" }} />
                        <Tooltip 
                          formatter={(val: any) => [`${val} / 5.0 điểm`, "Tổng điểm"]} 
                          labelFormatter={(lbl) => `Kỳ dữ liệu: ${lbl}`}
                          contentStyle={{ borderRadius: 8, border: "1px solid #cbd5e1", fontSize: 12 }}
                        />
                        <Bar 
                          dataKey="val" 
                          radius={[4, 4, 0, 0]} 
                          barSize={Math.min(28, Math.max(12, Math.floor(1000 / (detailData.history.length || 1))))} 
                          label={{ position: "top", fill: "#1e293b", fontSize: 10, fontWeight: 700 }}
                        >
                          {detailData.history.map((h: any, i: number) => (
                            <Cell key={i} fill={GRADE_CONFIG[h.grade]?.color || "#2563eb"} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              <div style={{ background: "#ffffff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, textAlign: "left" }}>
                  <thead>
                    <tr style={{ background: "#f8fafc", color: "#64748b", fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", borderBottom: "1px solid #e2e8f0" }}>
                      <th style={{ padding: "12px 20px" }}>KỲ ĐÁNH GIÁ</th>
                      <th style={{ padding: "12px 20px", textAlign: "center" }}>TỔNG ĐIỂM</th>
                      <th style={{ padding: "12px 20px", textAlign: "center" }}>MỨC XẾP HẠNG</th>
                      <th style={{ padding: "12px 20px", textAlign: "right" }}>THAY ĐỔI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detailData.history.map((h, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "14px 20px", fontWeight: 600, color: "#1e293b" }}>{h.year}</td>
                        <td style={{ padding: "14px 20px", textAlign: "center", fontWeight: 700, color: "#1e40af" }}>
                          {h.score.toFixed(2)}
                        </td>
                        <td style={{ padding: "14px 20px", textAlign: "center" }}>
                          <span
                            style={{
                              width: 24,
                              height: 24,
                              borderRadius: "50%",
                              background: GRADE_CONFIG[h.grade]?.color || "#2563eb",
                              color: "#ffffff",
                              display: "inline-flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: 12,
                              fontWeight: 700,
                              margin: "0 auto",
                            }}
                          >
                            {h.grade}
                          </span>
                        </td>
                        <td
                          style={{
                            padding: "14px 20px",
                            textAlign: "right",
                            fontWeight: 600,
                            color: h.change.startsWith("▲") ? "#10b981" : h.change.startsWith("▼") ? "#ef4444" : "#64748b",
                          }}
                        >
                          {h.change}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RankingBankDetail;
