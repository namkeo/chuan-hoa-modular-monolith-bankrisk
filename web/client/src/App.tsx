import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { FREQ_LABEL } from "./api";
import PeriodPicker from "./components/PeriodPicker";
import { Loader } from "./components/ui";
import { useStore } from "./store";

import Overview from "./pages/Overview";
import RiskDashboard from "./pages/RiskDashboard";
import EarlyWarning from "./pages/EarlyWarning";
import StressTest from "./pages/StressTest";
import Ranking from "./pages/Ranking";
import RuleMonitor from "./pages/RuleMonitor";
import Anomaly from "./pages/Anomaly";
import Clustering from "./pages/Clustering";
import TimeSeries from "./pages/TimeSeries";
import CreditRisk from "./pages/CreditRisk";
import LiquidityRisk from "./pages/LiquidityRisk";
import FraudFailure from "./pages/FraudFailure";
import Validation from "./pages/Validation";
import Performance from "./pages/Performance";
import Reports from "./pages/Reports";
import FineTuning from "./pages/FineTuning";

interface NavItem { to: string; label: string; ico: string; group?: string; }
const NAV: NavItem[] = [
  { to: "/", label: "Tổng quan dữ liệu", ico: "📊", group: "Tổng quan" },
  { to: "/ews", label: "Cảnh báo sớm (EWS)", ico: "🚨" },
  { to: "/stress", label: "Kiểm tra sức chịu đựng", ico: "🧪" },
  { to: "/risk", label: "Bảng điều khiển rủi ro", ico: "🎯" },
  { to: "/ranking", label: "Xếp hạng", ico: "🏆", group: "Phân tích" },
  { to: "/rules", label: "Giám sát rule pháp lý", ico: "⚖️" },
  { to: "/anomaly", label: "Phát hiện bất thường", ico: "🔍" },
  { to: "/clustering", label: "Phân cụm rủi ro", ico: "🧩" },
  { to: "/timeseries", label: "Chuỗi thời gian", ico: "📈" },
  { to: "/credit", label: "Rủi ro tín dụng", ico: "💳", group: "Theo lĩnh vực" },
  { to: "/liquidity", label: "Rủi ro thanh khoản", ico: "💧" },
  { to: "/fraud", label: "Gian lận / Đổ vỡ (proxy)", ico: "🚩" },
  { to: "/validation", label: "Validation & chất lượng", ico: "✅", group: "Vận hành" },
  { to: "/performance", label: "Theo dõi hiệu năng", ico: "⚙️" },
  { to: "/tuning", label: "Tinh chỉnh mô hình (ML)", ico: "🎛️" },
  { to: "/reports", label: "Xuất báo cáo", ico: "📄" },
];

const TITLES: Record<string, string> = Object.fromEntries(NAV.map((n) => [n.to, n.label]));

export default function App() {
  const { meta, freq, setFreq, loading, running, error, refresh, toast } = useStore();
  const loc = useLocation();
  const title = TITLES[loc.pathname] || "Phân tích rủi ro hệ thống ngân hàng";
  const isRankingPage = loc.pathname === "/ranking";

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">🏦</div>
          <h1>Rủi ro hệ thống ngân hàng</h1>
          <p>Hỗ trợ kiểm toán NHNN · ML + Expert Rules</p>
        </div>
        <nav className="nav">
          {NAV.map((n) => (
            <div key={n.to}>
              {n.group && <div className="group-label">{n.group}</div>}
              <NavLink to={n.to} end={n.to === "/"}
                className={({ isActive }) => (isActive ? "active" : "")}>
                <span className="ico">{n.ico}</span>{n.label}
              </NavLink>
            </div>
          ))}
        </nav>
      </aside>

      <div className="main">
        {!isRankingPage && (
          <header className="topbar">
            <div className="title">{title}</div>
            <div className="spacer" />
            <div className="freq-select">
              <span>Tần suất:</span>
              <select value={freq} onChange={(e) => setFreq(e.target.value)}>
                {((meta?.frequencies && meta.frequencies.length > 0)
                  ? meta.frequencies
                  : ["combined", "monthly", "quarterly", "yearly", "daily"]
                ).map((f) => (
                  <option key={f} value={f}>{FREQ_LABEL[f] || f}</option>
                ))}
              </select>
            </div>
            {!loading && !running && <PeriodPicker />}
            <button className="btn" disabled={running} onClick={() => refresh(true)}>
              {running ? "Đang chạy..." : "🔄 Chạy lại"}
            </button>
          </header>
        )}

        <main className="content">
          {loading || running ? (
            <Loader text={running ? "Đang chạy pipeline phân tích (Python)..." : "Đang tải dữ liệu..."} />
          ) : error ? (
            <div className="card"><div className="empty-state">
              <div className="big">⚠️</div>
              <div>Lỗi: {error}</div>
              <button className="btn primary" style={{ marginTop: 16 }} onClick={() => refresh()}>Thử chạy lại</button>
            </div></div>
          ) : (
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/ews" element={<EarlyWarning />} />
              <Route path="/stress" element={<StressTest />} />
              <Route path="/risk" element={<RiskDashboard />} />
              <Route path="/ranking" element={<Ranking />} />
              <Route path="/rules" element={<RuleMonitor />} />
              <Route path="/anomaly" element={<Anomaly />} />
              <Route path="/clustering" element={<Clustering />} />
              <Route path="/timeseries" element={<TimeSeries />} />
              <Route path="/credit" element={<CreditRisk />} />
              <Route path="/liquidity" element={<LiquidityRisk />} />
              <Route path="/fraud" element={<FraudFailure />} />
              <Route path="/validation" element={<Validation />} />
              <Route path="/performance" element={<Performance />} />
              <Route path="/tuning" element={<FineTuning />} />
              <Route path="/reports" element={<Reports />} />
            </Routes>
          )}
        </main>
      </div>

      {toast && <div className={`toast ${toast.error ? "error" : ""}`}>{toast.msg}</div>}
    </div>
  );
}
