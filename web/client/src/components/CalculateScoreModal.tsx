import React, { useState, useEffect, useMemo, useRef } from "react";
import { api } from "../api";
import { OBJECT_TYPE_LABEL_MAP } from "../pages/Ranking";

interface CalculateScoreModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const GRADE_CONFIG: Record<string, { color: string; bg: string; text: string }> = {
  A: { color: "#10b981", bg: "#dcfce7", text: "Hạng A - Rất Tốt" },
  B: { color: "#3b82f6", bg: "#dbeafe", text: "Hạng B - Tốt" },
  C: { color: "#f59e0b", bg: "#fef3c7", text: "Hạng C - Trung Bình" },
  D: { color: "#f97316", bg: "#ffedd5", text: "Hạng D - Yếu" },
  E: { color: "#ef4444", bg: "#fee2e2", text: "Hạng E - Kém" },
};

export const CalculateScoreModal: React.FC<CalculateScoreModalProps> = ({ isOpen, onClose }) => {
  const [bankList, setBankList] = useState<any[]>([]);
  const [loadingBanks, setLoadingBanks] = useState(false);

  // Form states - NO DEFAULT VALUES
  const [selectedBankId, setSelectedBankId] = useState("");
  const [bankSearchQuery, setBankSearchQuery] = useState("");
  const [isBankDropdownOpen, setIsBankDropdownOpen] = useState(false);

  const [selectedPeriod, setSelectedPeriod] = useState("2025");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Calculation result states
  const [calcResult, setCalcResult] = useState<any | null>(null);
  const [activeResultTab, setActiveResultTab] = useState<"criteria" | "extracted">("criteria");
  const [extractedSearch, setExtractedSearch] = useState("");
  const [selectedThresholdFilter, setSelectedThresholdFilter] = useState<number | null>(null);
  const [showFormulaDetails, setShowFormulaDetails] = useState<boolean>(true);
  const [isEvalExpanded, setIsEvalExpanded] = useState<boolean>(false);

  const bankDropdownRef = useRef<HTMLDivElement>(null);

  const getScoreThresholdColor = (score: number | null | undefined): string => {
    if (score === null || score === undefined) return "#94a3b8";
    const num = Math.round(score);
    switch (num) {
      case 5:
        return "#10b981"; // Xanh lá cây
      case 4:
        return "#0284c7"; // Xanh da trời
      case 3:
        return "#eab308"; // Vàng
      case 2:
        return "#f97316"; // Cam
      case 1:
        return "#ef4444"; // Đỏ
      default:
        return "#10b981";
    }
  };

const DEFAULT_FALLBACK_BANKS = [
  { _id: "VietinBank", ma_doi_tuong: "VietinBank", ten_doi_tuong: "Ngân hàng TMCP Công thương Việt Nam", ten_viet_tat: "VietinBank (CTG)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "BIDV", ma_doi_tuong: "BIDV", ten_doi_tuong: "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam", ten_viet_tat: "BIDV (BID)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "Agribank", ma_doi_tuong: "Agribank", ten_doi_tuong: "Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam", ten_viet_tat: "Agribank (AGR)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "Vietcombank", ma_doi_tuong: "Vietcombank", ten_doi_tuong: "Ngân hàng TMCP Ngoại thương Việt Nam", ten_viet_tat: "Vietcombank (VCB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "ACB", ma_doi_tuong: "ACB", ten_doi_tuong: "Ngân hàng TMCP Á Châu", ten_viet_tat: "ACB", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "LPBank", ma_doi_tuong: "LPBank", ten_doi_tuong: "Ngân hàng TMCP Lộc Phát Việt Nam", ten_viet_tat: "LPBank (LPB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "Techcombank", ma_doi_tuong: "Techcombank", ten_doi_tuong: "Ngân hàng TMCP Kỹ Thương Việt Nam", ten_viet_tat: "Techcombank (TCB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "HDBank", ma_doi_tuong: "HDBank", ten_doi_tuong: "Ngân hàng TMCP Phát triển TP.HCM", ten_viet_tat: "HDBank (HDB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "MBBank", ma_doi_tuong: "MBBank", ten_doi_tuong: "Ngân hàng TMCP Quân Đội", ten_viet_tat: "MBBank (MBB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "VIB", ma_doi_tuong: "VIB", ten_doi_tuong: "Ngân hàng TMCP Quốc tế Việt Nam", ten_viet_tat: "VIB", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "SHB", ma_doi_tuong: "SHB", ten_doi_tuong: "Ngân hàng TMCP Sài Gòn - Hà Nội", ten_viet_tat: "SHB", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "TPBank", ma_doi_tuong: "TPBank", ten_doi_tuong: "Ngân hàng TMCP Tiên Phong", ten_viet_tat: "TPBank (TPB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "VPBank", ma_doi_tuong: "VPBank", ten_doi_tuong: "Ngân hàng TMCP Việt Nam Thịnh Vượng", ten_viet_tat: "VPBank (VPB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "Bac A Bank", ma_doi_tuong: "Bac A Bank", ten_doi_tuong: "Ngân hàng TMCP Bắc Á", ten_viet_tat: "Bac A Bank (BAB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "MSB", ma_doi_tuong: "MSB", ten_doi_tuong: "Ngân hàng TMCP Hàng Hải Việt Nam", ten_viet_tat: "MSB", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "VietABank", ma_doi_tuong: "VietABank", ten_doi_tuong: "Ngân hàng TMCP Việt Á", ten_viet_tat: "VietABank (VAB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "SeABank", ma_doi_tuong: "SeABank", ten_doi_tuong: "Ngân hàng TMCP Đông Nam Á", ten_viet_tat: "SeABank (SSB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "BVBank", ma_doi_tuong: "BVBank", ten_doi_tuong: "Ngân hàng TMCP Bản Việt", ten_viet_tat: "BVBank (BVB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "Eximbank", ma_doi_tuong: "Eximbank", ten_doi_tuong: "Ngân hàng TMCP Xuất nhập khẩu Việt Nam", ten_viet_tat: "Eximbank (EIB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "NCB", ma_doi_tuong: "NCB", ten_doi_tuong: "Ngân hàng TMCP Quốc Dân", ten_viet_tat: "NCB (NVB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "Nam A Bank", ma_doi_tuong: "Nam A Bank", ten_doi_tuong: "Ngân hàng TMCP Nam Á", ten_viet_tat: "Nam A Bank (NAB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "OCB", ma_doi_tuong: "OCB", ten_doi_tuong: "Ngân hàng TMCP Phương Đông", ten_viet_tat: "OCB", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "BaoVietBank", ma_doi_tuong: "BaoVietBank", ten_doi_tuong: "Ngân hàng TMCP Bảo Việt", ten_viet_tat: "BaoVietBank (BAOVIET)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "PGBank", ma_doi_tuong: "PGBank", ten_doi_tuong: "Ngân hàng TMCP Thịnh Vượng và Phát triển", ten_viet_tat: "PGBank (PGB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "SaigonBank", ma_doi_tuong: "SaigonBank", ten_doi_tuong: "Ngân hàng TMCP Sài Gòn Công thương", ten_viet_tat: "SaigonBank (SGB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "ABBank", ma_doi_tuong: "ABBank", ten_doi_tuong: "Ngân hàng TMCP An Bình", ten_viet_tat: "ABBank (ABB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "Vietbank", ma_doi_tuong: "Vietbank", ten_doi_tuong: "Ngân hàng TMCP Việt Nam Thương Tín", ten_viet_tat: "Vietbank (VBB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "KienlongBank", ma_doi_tuong: "KienlongBank", ten_doi_tuong: "Ngân hàng TMCP Kiên Long", ten_viet_tat: "KienlongBank (KLB)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "Sacombank", ma_doi_tuong: "Sacombank", ten_doi_tuong: "Ngân hàng TMCP Sài Gòn Thương Tín", ten_viet_tat: "Sacombank (STB)", ma_loai_doi_tuong: "NHTM_QUY_MO_LON" },
  { _id: "PVcomBank", ma_doi_tuong: "PVcomBank", ten_doi_tuong: "Ngân hàng TMCP Đại Chúng Việt Nam", ten_viet_tat: "PVcomBank (PVC)", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" },
  { _id: "SCB", ma_doi_tuong: "SCB", ten_doi_tuong: "Ngân hàng TMCP Sài Gòn", ten_viet_tat: "SCB", ma_loai_doi_tuong: "NHTM_VUA_VA_NHO" }
];

  // Load bank list from DoiTuongDanhGia on modal open
  useEffect(() => {
    if (!isOpen) return;
    setLoadingBanks(true);

    // Reset form states on open
    setSelectedBankId("");
    setBankSearchQuery("");
    setIsBankDropdownOpen(false);
    setSelectedPeriod("");
    setSelectedFile(null);
    setCalcResult(null);
    setActiveResultTab("criteria");
    setExtractedSearch("");
    setIsEvalExpanded(false);

    api.doiTuongList()
      .then((res: any) => {
        const items = Array.isArray(res) ? res : (res?.data || []);
        if (items.length > 0) {
          setBankList(items);
        } else {
          setBankList(DEFAULT_FALLBACK_BANKS);
        }
      })
      .catch((err) => {
        console.warn("Failed to load DoiTuongDanhGia list, using fallback:", err);
        setBankList(DEFAULT_FALLBACK_BANKS);
      })
      .finally(() => setLoadingBanks(false));
  }, [isOpen]);

  // Click outside listener for bank searchable dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (bankDropdownRef.current && !bankDropdownRef.current.contains(event.target as Node)) {
        setIsBankDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Filter bank options based on search query (case-insensitive code, short name or full name match)
  const filteredBankOptions = useMemo(() => {
    const effectiveList = bankList.length > 0 ? bankList : DEFAULT_FALLBACK_BANKS;
    if (!bankSearchQuery.trim()) return effectiveList;
    const q = bankSearchQuery.toLowerCase().trim();
    const cleanQ = q.replace(/^\[.*?\]\s*/, "");
    return effectiveList.filter((b: any) => {
      const code = String(b.ma_doi_tuong || b._id || "").toLowerCase();
      const name = String(b.ten_doi_tuong || "").toLowerCase();
      const shortName = String(b.ten_viet_tat || "").toLowerCase();
      return (
        code.includes(cleanQ) ||
        name.includes(cleanQ) ||
        shortName.includes(cleanQ) ||
        code.includes(q) ||
        name.includes(q)
      );
    });
  }, [bankList, bankSearchQuery]);

  // Selected bank object
  const selectedBankObj = useMemo(() => {
    if (!selectedBankId) return null;
    const effectiveList = bankList.length > 0 ? bankList : DEFAULT_FALLBACK_BANKS;
    return effectiveList.find(
      (b: any) => b.ma_doi_tuong === selectedBankId || b._id === selectedBankId || b.doi_tuong_id === selectedBankId
    );
  }, [selectedBankId, bankList]);

  // Compute read-only Bank Type label based on selected bank_id
  const bankTypeLabel = useMemo(() => {
    if (!selectedBankId) return "-- Tự động điền theo ngân hàng đã chọn --";
    const rawType = selectedBankObj?.ma_loai_doi_tuong || "";
    return OBJECT_TYPE_LABEL_MAP[rawType] || rawType || "Ngân hàng thương mại có quy mô lớn";
  }, [selectedBankId, selectedBankObj]);

  if (!isOpen) return null;

  const handleSelectBank = (b: any) => {
    const code = b.ma_doi_tuong || b._id;
    const name = b.ten_doi_tuong || code;
    setSelectedBankId(code);
    setBankSearchQuery(`[${code}] ${name}`);
    setIsBankDropdownOpen(false);
  };

  const handleBankInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setBankSearchQuery(val);
    setSelectedBankId("");
    setIsBankDropdownOpen(true);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBankId) {
      alert("Vui lòng chọn Ngân hàng!");
      return;
    }
    if (!selectedPeriod) {
      alert("Vui lòng chọn Kỳ đánh giá!");
      return;
    }
    if (!selectedFile) {
      alert("Vui lòng chọn file tiêu chí định lượng!");
      return;
    }

    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("doi_tuong_id", selectedBankId);
      formData.append("ky_du_lieu", selectedPeriod);

      const res = await api.tinhDiemTuExcel(formData);
      if (res && (res.code === 200 || res.data)) {
        setCalcResult(res.data || res);
        setActiveResultTab("criteria");
      } else {
        alert("Tính điểm thất bại: " + (res?.message || "Không có phản hồi"));
      }
    } catch (err: any) {
      console.error("Lỗi tính điểm từ file:", err);
      alert("Có lỗi xảy ra khi tính điểm từ file excel: " + (err.response?.data?.message || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  // Export excel function for calculated result
  const handleExportResultExcel = () => {
    if (!calcResult) return;

    const bankName = selectedBankObj?.ten_doi_tuong || calcResult.doi_tuong?.ten_doi_tuong || selectedBankId;
    const periodStr = `Kỳ ${selectedPeriod}`;
    const overallScoreStr = (calcResult.tong_diem || 0).toFixed(2);
    const gradeStr = calcResult.xep_hang || "A";

    let tableRowsHtml = "";
    let globalStt = 1;

    (calcResult.ket_qua_cac_nhom || []).forEach((nhom: any) => {
      (nhom.ket_qua_cac_chi_tieu || []).forEach((ct: any) => {
        tableRowsHtml += `
          <tr>
            <td class="center">${globalStt++}</td>
            <td>${nhom.ten_nhom}</td>
            <td class="center txt">${ct.ma_chi_tieu_duoc_chon || ct.ma_chi_tieu_goc}</td>
            <td>${ct.ten_chi_tieu}</td>
            <td class="center">${ct.diem_theo_nguong ?? "-"}</td>
            <td class="num">${ct.trong_so ? ct.trong_so + "%" : "-"}</td>
            <td class="num">${ct.diem_quy_doi ? ct.diem_quy_doi.toFixed(3) : "-"}</td>
          </tr>
        `;
      });
    });

    const tableHtml = `
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
        <div class="title">BÁO CÁO CHI TIẾT TIÊU CHÍ ĐÁNH GIÁ (TÍNH TỪ FILE EXCEL)</div>
        <div class="sub">Đơn vị: ${bankName} (${selectedBankId}) | ${periodStr} | Tổng điểm: ${overallScoreStr} | Xếp hạng: ${gradeStr}</div>
        <table>
          <thead>
            <tr>
              <th style="width: 50px;">STT</th>
              <th style="width: 220px;">NHÓM TIÊU CHÍ</th>
              <th style="width: 110px;">MÃ CHỈ TIÊU</th>
              <th style="width: 320px;">TÊN TIÊU CHÍ</th>
              <th style="width: 150px;">ĐIỂM THEO NGƯỠNG</th>
              <th style="width: 110px;">TRỌNG SỐ</th>
              <th style="width: 130px;">ĐIỂM QUY ĐỔI</th>
            </tr>
          </thead>
          <tbody>
            ${tableRowsHtml}
          </tbody>
        </table>
      </body>
      </html>
    `;

    const blob = new Blob([tableHtml], { type: "application/vnd.ms-excel;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ChiTietTieuChi_${selectedBankId}_Ky_${selectedPeriod}.xls`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.65)",
        backdropFilter: "blur(6px)",
        zIndex: 9999,
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
          maxWidth: calcResult ? 1040 : 620,
          maxHeight: "92vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
          overflow: "hidden",
          border: "1px solid #cbd5e1",
          animation: "modalFadeIn 0.25s ease-out",
          transition: "max-width 0.3s ease",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
            color: "#ffffff",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: "rgba(59, 130, 246, 0.2)",
                border: "1px solid rgba(59, 130, 246, 0.4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 20,
              }}
            >
              📊
            </div>
            <div>
              <h3 style={{ fontSize: 18, fontWeight: 800, margin: 0, letterSpacing: "-0.01em" }}>
                {calcResult ? `KẾT QUẢ TÍNH ĐIỂM - ${selectedBankObj?.ten_doi_tuong || selectedBankId}` : "THỰC HIỆN TÍNH ĐIỂM XẾP HẠNG"}
              </h3>
              <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>
                {calcResult
                  ? `Đánh giá từ file Excel CAMELS | Kỳ ${selectedPeriod} | Mã đợt: ${calcResult.ket_qua_id}`
                  : "Nhập thông tin ngân hàng và file dữ liệu tiêu chí định lượng để tính điểm"}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "rgba(255,255,255,0.1)",
              border: "none",
              color: "#cbd5e1",
              fontSize: 18,
              width: 32,
              height: 32,
              borderRadius: "50%",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            ✕
          </button>
        </div>

        {/* CALCULATION RESULT DISPLAY (WITH FORMULA BREAKDOWN & EXTRACTED DATA TAB) */}
        {calcResult ? (
          <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden", background: "#f8fafc" }}>
            {/* Result KPI Bar */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "16px 24px",
                background: "#ffffff",
                borderBottom: "1px solid #e2e8f0",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>TỔNG ĐIỂM</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "#0f172a" }}>
                    {(calcResult.tong_diem || 0).toFixed(2)} <span style={{ fontSize: 14, color: "#94a3b8" }}>/ 5.0</span>
                  </div>
                </div>

                <div style={{ width: 1, height: 36, background: "#cbd5e1" }} />

                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>XẾP HẠNG</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
                    <span
                      style={{
                        padding: "4px 10px",
                        borderRadius: 6,
                        background: GRADE_CONFIG[calcResult.xep_hang]?.bg || "#dcfce7",
                        color: GRADE_CONFIG[calcResult.xep_hang]?.color || "#10b981",
                        fontSize: 14,
                        fontWeight: 800,
                      }}
                    >
                      {calcResult.xep_hang}
                    </span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: GRADE_CONFIG[calcResult.xep_hang]?.color || "#10b981" }}>
                      {GRADE_CONFIG[calcResult.xep_hang]?.text}
                    </span>
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: 10 }}>
                <button
                  onClick={handleExportResultExcel}
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
                    boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
                  }}
                >
                  📊 Xuất Excel Chi Tiết
                </button>

                <button
                  onClick={() => setCalcResult(null)}
                  style={{
                    padding: "8px 16px",
                    background: "#ffffff",
                    color: "#2563eb",
                    border: "1px solid #2563eb",
                    borderRadius: 8,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  🔄 Tính file khác
                </button>
              </div>
            </div>

            {/* CLAUSE 7 ARTICLE 20 EVALUATION BANNER */}
            {calcResult.danh_gia_khoan_7_dieu_20 && (
              <div
                style={{
                  padding: "12px 24px",
                  background: calcResult.danh_gia_khoan_7_dieu_20.bat_buoc_xep_hang_e ? "#fef2f2" : "#f0fdf4",
                  borderBottom: "1px solid #e2e8f0",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 16 }}>
                      {calcResult.danh_gia_khoan_7_dieu_20.bat_buoc_xep_hang_e ? "🚨" : "🛡️"}
                    </span>
                    <span style={{ fontSize: 13, fontWeight: 800, color: calcResult.danh_gia_khoan_7_dieu_20.bat_buoc_xep_hang_e ? "#991b1b" : "#166534", letterSpacing: "0.3px" }}>
                      ĐÁNH GIÁ XẾP HẠNG
                    </span>
                    {calcResult.danh_gia_khoan_7_dieu_20.bat_buoc_xep_hang_e && (
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

                {/* Overall Rating Conclusion Summary - Always Visible */}
                <div
                  style={{
                    padding: "8px 14px",
                    borderRadius: 8,
                    background: "#ffffff",
                    border: calcResult.danh_gia_khoan_7_dieu_20.bat_buoc_xep_hang_e ? "1px solid #fca5a5" : "1px solid #bbf7d0",
                    fontSize: 12.5,
                    fontWeight: 700,
                    color: calcResult.danh_gia_khoan_7_dieu_20.bat_buoc_xep_hang_e ? "#991b1b" : "#166534",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span style={{ fontSize: 15 }}>📌</span>
                  <span>
                    {calcResult.danh_gia_khoan_7_dieu_20.ket_luan || (
                      calcResult.danh_gia_khoan_7_dieu_20.bat_buoc_xep_hang_e
                        ? `Tổ chức tín dụng đạt điểm CAMELS = ${(calcResult.tong_diem || 0).toFixed(2)} (Xếp hạng gốc ${calcResult.danh_gia_khoan_7_dieu_20.xep_hang_goc}), tuy nhiên vi phạm điều kiện bổ sung tại Khoản 7 Điều 20 TT52 nên BẮT BUỘC HẠ XẾP HẠNG XUỐNG HẠNG (E).`
                        : `Tổ chức tín dụng đạt điểm CAMELS = ${(calcResult.tong_diem || 0).toFixed(2)} và không vi phạm các trường hợp hạ bậc tại Khoản 7 Điều 20 TT52, GIỮ NGUYÊN XẾP HẠNG ${calcResult.danh_gia_khoan_7_dieu_20.xep_hang_goc || calcResult.xep_hang}.`
                    )}
                  </span>
                </div>

                {/* Collapsible Detail Grid */}
                {isEvalExpanded && (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 4 }}>
                    {/* Condition a */}
                    <div style={{ padding: "10px 14px", borderRadius: 8, background: "#ffffff", border: "1px solid #cbd5e1", fontSize: 12, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                      <div>
                        <div style={{ fontWeight: 700, color: "#1e293b", marginBottom: 6 }}>a) Khả năng chi trả / thanh toán:</div>
                        {calcResult.danh_gia_khoan_7_dieu_20.dieu_kien_a_thanh_khoan.danh_sach_chi_tieu ? (
                          calcResult.danh_gia_khoan_7_dieu_20.dieu_kien_a_thanh_khoan.danh_sach_chi_tieu.map((item: any, idx: number) => (
                            <div key={idx} style={{ fontSize: 11.5, color: "#475569", lineHeight: 1.4, marginBottom: 2 }}>
                              • {item.ten_chi_tieu}: <strong style={{ color: item.diem < 2 ? "#dc2626" : "#0284c7" }}>{item.diem} điểm</strong>
                            </div>
                          ))
                        ) : (
                          calcResult.danh_gia_khoan_7_dieu_20.dieu_kien_a_thanh_khoan.chi_tiet_diem?.map((itemStr: string, idx: number) => (
                            <div key={idx} style={{ fontSize: 11.5, color: "#475569", lineHeight: 1.4, marginBottom: 2 }}>
                              • {itemStr}
                            </div>
                          ))
                        )}
                      </div>
                      <div style={{ marginTop: 8, paddingTop: 6, borderTop: "1px dashed #e2e8f0", color: calcResult.danh_gia_khoan_7_dieu_20.dieu_kien_a_thanh_khoan.co_chi_tieu_duoi_2 ? "#d97706" : "#16a34a", fontWeight: 700, fontSize: 11.5 }}>
                        👉 {calcResult.danh_gia_khoan_7_dieu_20.dieu_kien_a_thanh_khoan.mo_ta}
                      </div>
                    </div>

                    {/* Condition b */}
                    <div style={{ padding: "10px 14px", borderRadius: 8, background: "#ffffff", border: "1px solid #cbd5e1", fontSize: 12, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                      <div>
                        <div style={{ fontWeight: 700, color: "#1e293b", marginBottom: 6 }}>b) Lỗ lũy kế / VĐL & Quỹ:</div>
                        <div style={{ fontSize: 11.5, color: "#334155", lineHeight: 1.5 }}>
                          <div style={{ wordBreak: "break-word" }}>
                            <code style={{ background: "#f1f5f9", padding: "4px 8px", borderRadius: 4, color: "#0f172a", fontWeight: 600, display: "block", fontSize: 11.5, lineHeight: 1.4 }}>
                              {calcResult.danh_gia_khoan_7_dieu_20.dieu_kien_b_lo_luy_ke.bieu_thuc_day_du || 
                               `Lỗ lũy kế / VĐL & Quỹ = (R-191 / R-192) × 100%`}
                            </code>
                          </div>
                          <div style={{ marginTop: 6, paddingTop: 6, borderTop: "1px dashed #e2e8f0", color: calcResult.danh_gia_khoan_7_dieu_20.dieu_kien_b_lo_luy_ke.vi_pham ? "#dc2626" : "#16a34a", fontWeight: 700, fontSize: 11.5 }}>
                            👉 {calcResult.danh_gia_khoan_7_dieu_20.dieu_kien_b_lo_luy_ke.mo_ta}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Condition c */}
                    <div style={{ padding: "10px 14px", borderRadius: 8, background: "#ffffff", border: "1px solid #cbd5e1", fontSize: 12, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                      <div>
                        <div style={{ fontWeight: 700, color: "#1e293b", marginBottom: 6 }}>c) Duy trì CAR:</div>
                        <div style={{ fontSize: 11.5, color: calcResult.danh_gia_khoan_7_dieu_20.dieu_kien_c_vi_pham_car.vi_pham ? "#dc2626" : "#16a34a", fontWeight: 600, lineHeight: 1.4 }}>
                          👉 {calcResult.danh_gia_khoan_7_dieu_20.dieu_kien_c_vi_pham_car.mo_ta}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Navigation Tabs Bar */}
            <div style={{ display: "flex", gap: 16, borderBottom: "1px solid #e2e8f0", background: "#ffffff", padding: "0 24px" }}>
              <button
                onClick={() => setActiveResultTab("criteria")}
                style={{
                  padding: "12px 16px",
                  border: "none",
                  borderBottom: activeResultTab === "criteria" ? "2px solid #2563eb" : "2px solid transparent",
                  color: activeResultTab === "criteria" ? "#2563eb" : "#64748b",
                  fontWeight: activeResultTab === "criteria" ? 700 : 500,
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: 14,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <span>📐</span> Chi tiết tiêu chí & Công thức
              </button>
              <button
                onClick={() => setActiveResultTab("extracted")}
                style={{
                  padding: "12px 16px",
                  border: "none",
                  borderBottom: activeResultTab === "extracted" ? "2px solid #2563eb" : "2px solid transparent",
                  color: activeResultTab === "extracted" ? "#2563eb" : "#64748b",
                  fontWeight: activeResultTab === "extracted" ? 700 : 500,
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: 14,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <span>📋</span> Dữ liệu dạng excel
              </button>
            </div>

            {/* TAB 1: CHI TIẾT TIÊU CHÍ & CÔNG THỨC THẾ SỐ */}
            {activeResultTab === "criteria" && (
              <div style={{ padding: 24, overflowY: "auto", flex: 1 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a" }}>
                      BẢNG CHI TIẾT CÁC CHỈ TIÊU ĐÁNH GIÁ (TỪ FILE EXCEL CAMELS)
                    </div>
                    <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13, fontWeight: 600, color: "#2563eb", background: "#eff6ff", padding: "6px 14px", borderRadius: 8, border: "1px solid #bfdbfe", userSelect: "none" }}>
                      <input
                        type="checkbox"
                        checked={showFormulaDetails}
                        onChange={(e) => setShowFormulaDetails(e.target.checked)}
                        style={{ width: 16, height: 16, cursor: "pointer", accentColor: "#2563eb" }}
                      />
                      <span>Hiển thị công thức</span>
                    </label>
                  </div>

                  {((calcResult.ket_qua_cac_nhom || calcResult.ket_qua_nhom || []) as any[]).map((nhom: any, idx: number) => (
                    <div key={idx} style={{ background: "#ffffff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
                      <div style={{ padding: "12px 20px", background: "#f8fafc", fontSize: 12, fontWeight: 700, color: "#475569", borderBottom: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between" }}>
                        <span>{nhom.ten_nhom}</span>
                        <span>Điểm nhóm: {nhom.diem_nhom?.toFixed(2)} | Trọng số: {nhom.trong_so_tieu_chi ?? nhom.trong_so ?? 0}%</span>
                      </div>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, textAlign: "left" }}>
                        <thead>
                          <tr style={{ color: "#94a3b8", fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", borderBottom: "1px solid #f1f5f9" }}>
                            <th style={{ padding: "10px 20px", width: 90 }}>MÃ</th>
                            <th style={{ padding: "10px 20px" }}>TIÊU CHÍ & CÔNG THỨC ÁP DỤNG</th>
                            <th style={{ padding: "10px 20px", textAlign: "center", width: 140 }}>GIÁ TRỊ TÍNH TOÁN</th>
                            <th style={{ padding: "10px 20px", textAlign: "center", width: 130 }}>ĐIỂM THEO NGƯỠNG</th>
                            <th style={{ padding: "10px 20px", textAlign: "center", width: 90 }}>TRỌNG SỐ</th>
                            <th style={{ padding: "10px 20px", textAlign: "right", width: 110 }}>ĐIỂM QUY ĐỔI</th>
                          </tr>
                        </thead>
                        <tbody>
                          {((nhom.ket_qua_cac_chi_tieu || nhom.ket_qua_chi_tieu || nhom.danh_sach_chi_tieu || []) as any[]).map((item: any) => {
                            const isDinhTuynh = (item.loai_chi_tieu === "DINH_TUYNH") || (item.ma_chi_tieu_duoc_chon && String(item.ma_chi_tieu_duoc_chon).endsWith("_DT"));
                            const rawVal = item.gia_tri_tinh_toan;
                            let displayVal = "-";

                            if (rawVal !== undefined && rawVal !== null) {
                              const strVal = String(rawVal).trim();
                              if (isDinhTuynh && (strVal === "0 sai phạm" || strVal === "-" || strVal === "0")) {
                                displayVal = "-";
                              } else {
                                const numVal = Number(rawVal);
                                if (isNaN(numVal)) {
                                  displayVal = strVal;
                                } else if (isDinhTuynh || Number.isInteger(numVal) || numVal % 1 === 0) {
                                  const intVal = Math.round(numVal);
                                  displayVal = isDinhTuynh ? `${intVal}` : `${intVal} ${item.don_vi_tinh || "%"}`;
                                } else {
                                  displayVal = `${numVal.toFixed(3)} ${item.don_vi_tinh || "%"}`;
                                }
                              }
                            }

                            return (
                              <tr key={item.ma_chi_tieu_duoc_chon || item.ma_chi_tieu_goc} style={{ borderBottom: "1px solid #f8fafc" }}>
                                <td style={{ padding: "12px 20px", color: "#64748b", fontWeight: 600, verticalAlign: "top" }}>
                                  {item.ma_chi_tieu_duoc_chon || item.ma_chi_tieu_goc}
                                </td>
                                <td style={{ padding: "12px 20px", color: "#1e293b", verticalAlign: "top" }}>
                                  <div style={{ fontWeight: 700, fontSize: 13, color: "#0f172a" }}>{item.ten_chi_tieu}</div>

                                  {/* Step-by-step formula substitution box */}
                                  {showFormulaDetails && (item.cong_thuc_snapshot?.bieu_thuc_the_so || item.cong_thuc_snapshot?.mo_ta_cong_thuc || item.dien_giai) && (
                                    <div style={{ marginTop: 6, background: "#f8fafc", padding: "8px 12px", borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }}>
                                      {item.cong_thuc_snapshot?.bieu_thuc_the_so ? (
                                        <div style={{ color: "#1e293b", fontFamily: "monospace", marginBottom: 4 }}>
                                          <strong style={{ color: "#2563eb", fontFamily: "Inter, sans-serif" }}>Công thức:</strong> {item.cong_thuc_snapshot.bieu_thuc_the_so}
                                        </div>
                                      ) : item.cong_thuc_snapshot?.mo_ta_cong_thuc ? (
                                        <div style={{ color: "#1e293b", fontFamily: "monospace", marginBottom: 4 }}>
                                          <strong style={{ color: "#2563eb", fontFamily: "Inter, sans-serif" }}>Công thức:</strong> {item.cong_thuc_snapshot.mo_ta_cong_thuc}
                                        </div>
                                      ) : null}

                                      {item.dien_giai && (
                                        <div style={{ color: "#475569", fontWeight: 600 }}>
                                          <span style={{ color: "#059669" }}>⚖️ So sánh ngưỡng:</span> {item.dien_giai}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </td>
                                <td style={{ padding: "12px 20px", textAlign: "center", fontWeight: 600, color: "#0f172a", verticalAlign: "top" }}>
                                  {displayVal}
                                </td>
                                <td style={{ padding: "12px 20px", textAlign: "center", verticalAlign: "top" }}>
                                  <span
                                    style={{
                                      width: 28,
                                      height: 28,
                                      borderRadius: "50%",
                                      background: getScoreThresholdColor(item.diem_theo_nguong ?? item.diem),
                                      color: "#ffffff",
                                      display: "inline-flex",
                                      alignItems: "center",
                                      justifyContent: "center",
                                      fontSize: 12,
                                      fontWeight: 700,
                                    }}
                                  >
                                    {item.diem_theo_nguong ?? item.diem ?? 0}
                                  </span>
                                </td>
                                <td style={{ padding: "12px 20px", textAlign: "center", color: "#64748b", verticalAlign: "top" }}>
                                  {item.trong_so}%
                                </td>
                                <td style={{ padding: "12px 20px", textAlign: "right", fontWeight: 700, color: "#2563eb", verticalAlign: "top" }}>
                                  {(item.diem_quy_doi || 0).toFixed(3)}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 2: DỮ LIỆU DẠNG EXCEL */}
            {activeResultTab === "extracted" && (() => {
              const rawExtractedList = calcResult.du_lieu_boc_tach || [];
              const thresholdCounts: Record<number, number> = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };
              rawExtractedList.forEach((row: any) => {
                if (row.diem_theo_nguong !== null && row.diem_theo_nguong !== undefined) {
                  const sc = Math.round(row.diem_theo_nguong);
                  if (thresholdCounts[sc] !== undefined) {
                    thresholdCounts[sc]++;
                  }
                }
              });

              return (
                <div style={{ padding: 24, overflowY: "auto", flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a" }}>
                      DỮ LIỆU DẠNG EXCEL
                    </div>
                    <input
                      type="text"
                      value={extractedSearch}
                      onChange={(e) => setExtractedSearch(e.target.value)}
                      placeholder="🔍 Tìm kiếm mã dòng nguồn (R-105...), tên chỉ tiêu, STT..."
                      style={{
                        padding: "8px 14px",
                        borderRadius: 8,
                        border: "1px solid #cbd5e1",
                        fontSize: 13,
                        width: 320,
                        outline: "none",
                      }}
                    />
                  </div>

                  {/* THRESHOLD QUICK FILTER PILLS (ROUNDED BADGES) */}
                  <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
                    {[5, 4, 3, 2, 1].map((scoreNum) => {
                      const count = thresholdCounts[scoreNum] || 0;
                      const isSelected = selectedThresholdFilter === scoreNum;
                      const badgeColor = getScoreThresholdColor(scoreNum);

                      return (
                        <button
                          key={scoreNum}
                          type="button"
                          onClick={() => setSelectedThresholdFilter(isSelected ? null : scoreNum)}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 8,
                            padding: "5px 14px 5px 8px",
                            borderRadius: 24,
                            border: isSelected ? `2px solid ${badgeColor}` : "1px solid #cbd5e1",
                            background: isSelected ? "#f0f9ff" : "#ffffff",
                            boxShadow: isSelected ? `0 2px 8px ${badgeColor}33` : "0 1px 2px rgba(0,0,0,0.04)",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                            userSelect: "none",
                          }}
                        >
                          <span
                            style={{
                              width: 22,
                              height: 22,
                              borderRadius: "50%",
                              background: badgeColor,
                              color: "#ffffff",
                              display: "inline-flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontWeight: 800,
                              fontSize: 12,
                            }}
                          >
                            {scoreNum}
                          </span>
                          <span style={{ fontSize: 13, color: "#0f172a", fontWeight: 700 }}>
                            {count} <span style={{ fontWeight: 500, color: "#64748b" }}>chỉ tiêu</span>
                          </span>
                        </button>
                      );
                    })}

                    {selectedThresholdFilter !== null && (
                      <button
                        type="button"
                        onClick={() => setSelectedThresholdFilter(null)}
                        style={{
                          padding: "5px 12px",
                          borderRadius: 16,
                          border: "1px solid #cbd5e1",
                          background: "#f1f5f9",
                          color: "#475569",
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        ✕ Xóa lọc điểm
                      </button>
                    )}
                  </div>

                  <div style={{ background: "#ffffff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, textAlign: "left" }}>
                      <thead>
                        <tr style={{ background: "#f8fafc", color: "#475569", fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", borderBottom: "1px solid #e2e8f0" }}>
                          <th style={{ padding: "10px 16px", width: 90 }}>STT</th>
                          <th style={{ padding: "10px 16px", width: 130 }}>MÃ DÒNG NGUỒN</th>
                          <th style={{ padding: "10px 16px" }}>TÊN CHỈ TIÊU (EXCEL)</th>
                          <th style={{ padding: "10px 16px", textAlign: "right", width: 170 }}>SỐ LIỆU</th>
                          <th style={{ padding: "10px 16px", textAlign: "center", width: 130 }}>ĐIỂM THEO NGƯỠNG</th>
                          <th style={{ padding: "10px 16px", textAlign: "right", width: 120 }}>ĐIỂM QUY ĐỔI</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rawExtractedList
                          .filter((row: any) => {
                            if (selectedThresholdFilter !== null) {
                              const rowScore = row.diem_theo_nguong !== null && row.diem_theo_nguong !== undefined ? Math.round(row.diem_theo_nguong) : null;
                              if (rowScore !== selectedThresholdFilter) return false;
                            }
                            if (!extractedSearch.trim()) return true;
                            const q = extractedSearch.toLowerCase();
                            return (
                              String(row.stt || "").toLowerCase().includes(q) ||
                              String(row.ma_dong_nguon || "").toLowerCase().includes(q) ||
                              String(row.chi_tieu || "").toLowerCase().includes(q)
                            );
                          })
                        .map((row: any, idx: number) => {
                          const isHeader = row.is_header;
                          const level = row.cap_do || 1;
                          const code = String(row.ma_dong_nguon || "").trim();
                          const isBranch = ["R-102", "R-105", "R-109", "R-112"].includes(code);

                          const isDtRow = code.endsWith("_DT") || String(row.chi_tieu || "").includes("định tính");
                          const numVal = row.so_lieu;
                          let numStr = numVal !== null && numVal !== undefined
                            ? (typeof numVal === "number" ? numVal.toLocaleString("vi-VN", { maximumFractionDigits: 2 }) : String(numVal))
                            : null;
                          if (isDtRow && (numStr === "0 sai phạm" || numStr === "-" || numStr === "0")) {
                            numStr = null;
                          }

                          const ngVal = row.diem_theo_nguong;
                          const qdVal = row.diem_quy_doi;
                          const scoreType = row.loai_diem;

                          let rowBg = "#ffffff";
                          let fontWt = 400;
                          let fontSize = 13;
                          let textColor = "#1e293b";
                          let fontStyle = "normal";
                          let indentPadding = Math.min((level - 1) * 16, 48);

                          if (level === 1) {
                            rowBg = "#cbd5e1"; // Section header level 1 (R-100, R-115...)
                            fontWt = 800;
                            fontSize = 14;
                            textColor = "#0f172a";
                            fontStyle = "normal";
                          } else if (level === 2) {
                            // Nhóm chỉ tiêu (STT 1.1, 1.2, 1.3, 2.1..2.7, 3.1..3.2, 4.1..4.4, 5.1..5.5, 6.1..6.3)
                            rowBg = "#f1f5f9";
                            fontWt = 700;
                            fontSize = 13;
                            textColor = "#0f172a";
                            fontStyle = "italic";
                          } else if (isBranch) {
                            rowBg = "#f0f9ff";
                            textColor = "#0369a1";
                            fontWt = 500;
                            fontStyle = "italic";
                          }

                          return (
                            <tr key={idx} style={{ background: rowBg, borderBottom: "1px solid #cbd5e1" }}>
                              <td style={{ padding: "8px 16px", color: level === 1 ? "#0f172a" : "#475569", fontWeight: fontWt }}>
                                {row.stt}
                              </td>
                              <td style={{ padding: "8px 16px" }}>
                                <span
                                  style={{
                                    padding: "3px 8px",
                                    background: level === 1 ? "#0f172a" : isHeader ? "#1e293b" : isBranch ? "#e0f2fe" : "#eff6ff",
                                    color: level === 1 || isHeader ? "#ffffff" : isBranch ? "#0369a1" : "#2563eb",
                                    borderRadius: 6,
                                    fontWeight: 700,
                                    fontSize: 12,
                                    fontFamily: "monospace",
                                  }}
                                >
                                  {row.ma_dong_nguon}
                                </span>
                              </td>
                              <td style={{ padding: `8px 16px 8px ${16 + indentPadding}px`, color: textColor, fontWeight: fontWt, fontSize, fontStyle }}>
                                {row.chi_tieu}
                              </td>
                              <td style={{ padding: "8px 16px", textAlign: "right", fontWeight: isHeader ? 800 : 700, color: numStr ? "#0f172a" : "#94a3b8", fontStyle }}>
                                {numStr !== null ? numStr : (isHeader ? "" : <span style={{ fontStyle: "italic", fontWeight: 400, color: "#cbd5e1" }}>-</span>)}
                              </td>
                              <td style={{ padding: "8px 16px", textAlign: "center" }}>
                                {ngVal !== null && ngVal !== undefined ? (
                                  <span style={{ width: 26, height: 26, borderRadius: "50%", background: getScoreThresholdColor(ngVal), color: "#ffffff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 12 }}>
                                    {ngVal}
                                  </span>
                                ) : (
                                  <span style={{ color: "#cbd5e1" }}>-</span>
                                )}
                              </td>
                              <td style={{ padding: "8px 16px", textAlign: "right" }}>
                                {qdVal !== null && qdVal !== undefined ? (
                                  scoreType === "NHOM" ? (
                                    <span style={{ padding: "3px 10px", background: "#2563eb", color: "#ffffff", borderRadius: 12, fontWeight: 800, fontSize: 12 }}>
                                      {qdVal.toFixed(2)}
                                    </span>
                                  ) : (
                                    <span style={{ color: "#2563eb", fontWeight: 700, fontSize: 13 }}>
                                      {qdVal.toFixed(3)}
                                    </span>
                                  )
                                ) : (
                                  <span style={{ color: "#cbd5e1" }}>-</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })()}
          </div>
        ) : (
          /* FORM INPUT DISPLAY */
          <form onSubmit={handleSubmit} style={{ padding: 24, overflowY: "auto" }}>
            {/* 1. Chọn Ngân hàng (bank_id) - SEARCHABLE DROPDOWN */}
            <div style={{ marginBottom: 18, position: "relative" }} ref={bankDropdownRef}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 6, letterSpacing: "0.03em" }}>
                TỔ CHỨC TÍN DỤNG / NGÂN HÀNG <span style={{ color: "#ef4444" }}>*</span>
              </label>

              <div style={{ position: "relative" }}>
                <input
                  type="text"
                  value={bankSearchQuery}
                  onChange={handleBankInputChange}
                  onFocus={() => setIsBankDropdownOpen(true)}
                  onClick={() => setIsBankDropdownOpen((prev) => !prev)}
                  placeholder="-- Gõ tên hoặc mã ngân hàng để tìm kiếm (ví dụ: VCB, VPBank, V...) --"
                  disabled={loadingBanks}
                  style={{
                    width: "100%",
                    padding: "11px 40px 11px 14px",
                    borderRadius: 8,
                    border: isBankDropdownOpen ? "1px solid #2563eb" : "1px solid #cbd5e1",
                    boxShadow: isBankDropdownOpen ? "0 0 0 3px rgba(37, 99, 235, 0.15)" : "none",
                    fontSize: 14,
                    fontWeight: 600,
                    color: "#0f172a",
                    outline: "none",
                    background: "#ffffff",
                    boxSizing: "border-box",
                    cursor: "pointer",
                  }}
                />
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setIsBankDropdownOpen((prev) => !prev);
                  }}
                  style={{
                    position: "absolute",
                    right: 8,
                    top: "50%",
                    transform: "translateY(-50%)",
                    fontSize: 14,
                    color: "#64748b",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    padding: "4px 6px",
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                  }}
                >
                  🔍 {isBankDropdownOpen ? "▲" : "▼"}
                </button>
              </div>

              {/* Dropdown Options list */}
              {isBankDropdownOpen && (
                <div
                  style={{
                    position: "absolute",
                    top: "100%",
                    left: 0,
                    right: 0,
                    marginTop: 4,
                    maxHeight: 220,
                    overflowY: "auto",
                    background: "#ffffff",
                    borderRadius: 8,
                    border: "1px solid #cbd5e1",
                    boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
                    zIndex: 10,
                  }}
                >
                  {loadingBanks ? (
                    <div style={{ padding: "12px 16px", fontSize: 13, color: "#64748b" }}>Đang tải danh sách ngân hàng...</div>
                  ) : filteredBankOptions.length === 0 ? (
                    <div style={{ padding: "12px 16px", fontSize: 13, color: "#94a3b8" }}>Không tìm thấy ngân hàng khớp với từ khóa</div>
                  ) : (
                    filteredBankOptions.map((b: any) => {
                      const code = b.ma_doi_tuong || b._id;
                      const name = b.ten_doi_tuong || code;
                      const isSelected = selectedBankId === code;

                      return (
                        <div
                          key={code}
                          onClick={() => handleSelectBank(b)}
                          style={{
                            padding: "10px 14px",
                            fontSize: 13,
                            fontWeight: isSelected ? 700 : 500,
                            color: isSelected ? "#2563eb" : "#1e293b",
                            background: isSelected ? "#eff6ff" : "transparent",
                            cursor: "pointer",
                            borderBottom: "1px solid #f1f5f9",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                          }}
                          onMouseEnter={(e) => {
                            if (!isSelected) e.currentTarget.style.background = "#f8fafc";
                          }}
                          onMouseLeave={(e) => {
                            if (!isSelected) e.currentTarget.style.background = "transparent";
                          }}
                        >
                          <div>
                            <span style={{ fontWeight: 700, color: "#0f172a", marginRight: 8 }}>[{code}]</span>
                            {name}
                          </div>
                          {isSelected && <span style={{ color: "#2563eb", fontWeight: 800 }}>✓</span>}
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>

            {/* 2. Kỳ đánh giá (Chỉ có Kỳ 2025, Kỳ 2024, Kỳ 2023 - Không có mặc định) */}
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 6, letterSpacing: "0.03em" }}>
                KỲ ĐÁNH GIÁ <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <select
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value)}
                style={{
                  width: "100%",
                  padding: "11px 14px",
                  borderRadius: 8,
                  border: "1px solid #cbd5e1",
                  fontSize: 14,
                  fontWeight: 600,
                  color: selectedPeriod ? "#0f172a" : "#94a3b8",
                  outline: "none",
                  background: "#ffffff",
                }}
              >
                <option value="">-- Chọn kỳ đánh giá --</option>
                <option value="2025" style={{ color: "#0f172a" }}>Kỳ 2025</option>
                <option value="2024" style={{ color: "#0f172a" }}>Kỳ 2024</option>
                <option value="2023" style={{ color: "#0f172a" }}>Kỳ 2023</option>
              </select>
            </div>

            {/* 3. Loại hình ngân hàng (Read-only, disabled, auto-populated) */}
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 6, letterSpacing: "0.03em" }}>
                <span>LOẠI HÌNH TỔ CHỨC TÍN DỤNG</span>
                <span style={{ fontSize: 11, fontWeight: 500, color: "#64748b" }}>🔒 Tự động điền theo ngân hàng</span>
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type="text"
                  value={bankTypeLabel}
                  readOnly
                  disabled
                  style={{
                    width: "100%",
                    padding: "11px 14px 11px 36px",
                    borderRadius: 8,
                    border: "1px solid #e2e8f0",
                    fontSize: 14,
                    fontWeight: 600,
                    color: selectedBankId ? "#475569" : "#94a3b8",
                    background: "#f1f5f9",
                    cursor: "not-allowed",
                    boxSizing: "border-box",
                  }}
                />
                <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", fontSize: 14 }}>
                  🏛️
                </span>
              </div>
            </div>

            {/* 4. File các tiêu chí định lượng */}
            <div style={{ marginBottom: 24 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 6, letterSpacing: "0.03em" }}>
                FILE TIÊU CHÍ ĐỊNH LƯỢNG <span style={{ color: "#ef4444" }}>*</span>
              </label>
              
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                style={{
                  border: dragActive ? "2px dashed #2563eb" : "2px dashed #cbd5e1",
                  borderRadius: 10,
                  padding: "20px 16px",
                  textAlign: "center",
                  background: dragActive ? "#eff6ff" : "#f8fafc",
                  transition: "all 0.2s ease",
                  cursor: "pointer",
                  position: "relative",
                }}
              >
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileChange}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: "100%",
                    opacity: 0,
                    cursor: "pointer",
                  }}
                />

                {selectedFile ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 8, background: "#dcfce7", color: "#16a34a", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 700 }}>
                      📊
                    </div>
                    <div style={{ textAlign: "left" }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a" }}>{selectedFile.name}</div>
                      <div style={{ fontSize: 12, color: "#64748b" }}>{(selectedFile.size / 1024).toFixed(1)} KB</div>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedFile(null);
                      }}
                      style={{
                        marginLeft: 16,
                        background: "#fee2e2",
                        color: "#ef4444",
                        border: "none",
                        borderRadius: 6,
                        padding: "4px 8px",
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Bỏ chọn
                    </button>
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: 28, marginBottom: 6 }}>📁</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#1e293b", marginBottom: 2 }}>
                      Kéo thả file vào đây hoặc <span style={{ color: "#2563eb", textDecoration: "underline" }}>bấm để chọn file</span>
                    </div>
                    <div style={{ fontSize: 12, color: "#94a3b8" }}>Hỗ trợ định dạng .xlsx, .xls, .csv</div>
                  </div>
                )}
              </div>
            </div>

            {/* Footer actions */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, paddingTop: 16, borderTop: "1px solid #f1f5f9" }}>
              <button
                type="button"
                onClick={onClose}
                disabled={submitting}
                style={{
                  padding: "10px 18px",
                  borderRadius: 8,
                  border: "1px solid #cbd5e1",
                  background: "#ffffff",
                  color: "#475569",
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: submitting ? "not-allowed" : "pointer",
                }}
              >
                Hủy
              </button>
              <button
                type="submit"
                disabled={submitting}
                style={{
                  padding: "10px 22px",
                  borderRadius: 8,
                  border: "none",
                  background: submitting ? "#94a3b8" : "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
                  color: "#ffffff",
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: submitting ? "not-allowed" : "pointer",
                  boxShadow: submitting ? "none" : "0 4px 12px rgba(37, 99, 235, 0.25)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                {submitting ? (
                  <>
                    <span style={{ animation: "spin 1s linear infinite" }}>🔄</span> Đang tính toán...
                  </>
                ) : (
                  <>
                    <span>⚡</span> Thực hiện tính điểm
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
