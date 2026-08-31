# Web UI chuyên nghiệp (React + Node.js)

Giao diện web cho phần mềm phân tích rủi ro hệ thống ngân hàng. Kiến trúc 3 lớp:

```
React (Vite + TypeScript + Recharts)      web/client   ← giao diện
        │  REST /api/*
Node.js (Express) API gateway             web/server   ← cầu nối, spawn Python
        │  spawn: python -m src.api_export
Python engine (đã có & test)              src/         ← phân tích thật
        │  outputs/api/*.json
```

Engine phân tích **vẫn là Python** (Isolation Forest, K-means, rule engine, scoring đã
kiểm thử). Node chỉ là cầu nối mỏng: gọi `python -m src.api_export <freq>` để (chạy &)
xuất JSON, React đọc JSON qua REST. Không có bridge runtime Python↔JS.

## Cách chạy nhanh (Windows)

**Double-click `run_web.bat`** ở thư mục gốc dự án. Script sẽ tự:
1. Cài deps Node (backend + frontend) nếu thiếu
2. Build frontend (Vite) nếu chưa có `dist`
3. Sinh dữ liệu API ban đầu bằng Python nếu chưa có
4. Mở trình duyệt tại http://localhost:4000

## Cách chạy thủ công

```powershell
# 1) Backend
cd web\server
npm install
node server.js          # API + phục vụ frontend đã build tại http://localhost:4000

# 2) Frontend (production build — server sẽ tự phục vụ)
cd web\client
npm install
npm run build           # tạo web/client/dist
```

### Chế độ phát triển (hot reload)

```powershell
cd web\server && node server.js          # cửa sổ 1: API ở :4000
cd web\client && npm run dev             # cửa sổ 2: Vite dev ở :5173 (proxy /api -> :4000)
```
Mở http://localhost:5173.

## Yêu cầu

- Node.js LTS (đã cài qua `winget install OpenJS.NodeJS.LTS`)
- Python venv của dự án (`.venv`) với requirements đã cài (server tự dò `.venv`)

## REST API

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/health` | trạng thái server + đường dẫn Python |
| GET | `/api/meta` | danh sách tần suất, version |
| GET | `/api/data/:freq` | toàn bộ payload phân tích 1 tần suất |
| POST | `/api/run/:freq?fresh=1` | chạy lại pipeline Python (xóa cache nếu `fresh`) |
| GET | `/api/performance` | log hiệu năng + đề xuất iterative |
| GET | `/api/pdf-status` | trạng thái parse PDF + candidate rule |
| POST | `/api/report/:freq` | sinh Excel/HTML/CSV |
| GET | `/api/download/:name` | tải file báo cáo |
| POST | `/api/feedback` | lưu phản hồi kiểm toán viên |

## Các trang giao diện

Tổng quan dữ liệu · **Cảnh báo sớm (EWS)** · **Kiểm tra sức chịu đựng (stress-test)** ·
Bảng điều khiển rủi ro (heatmap) · Giám sát rule pháp lý · Phát hiện bất thường
(+ feedback) · Phân cụm (PCA scatter) · Chuỗi thời gian · Rủi ro tín dụng · Rủi ro
thanh khoản · Gian lận/Đổ vỡ (proxy) · Validation · Theo dõi hiệu năng · Xuất báo cáo.

Trang **EWS** (cảnh báo sớm) hiển thị: chỉ số EWS hệ thống theo kỳ, phân bố mức
traffic-light, watchlist "rủi ro mới nổi", quỹ đạo điểm EWS theo ngân hàng, phân rã
tín hiệu và dự phóng số kỳ tới khi chạm ngưỡng.

Trang **Stress-test** hiển thị: số NH không đạt CAR 8% theo từng kịch bản, tổng thiếu
hụt vốn, CAR trước/sau sốc, khe hở thanh khoản và **reverse stress** (điểm gãy NPL).
Cả hai khuyến nghị xem ở tần suất **tháng**.

**Tích hợp đa tần suất:** tần suất **"Kết hợp (đa tần suất)"** (mặc định) hợp nhất chỉ
tiêu Tháng + Quý + Năm vào lưới tháng bằng as-of join point-in-time, cho mọi mô hình bộ
chỉ tiêu giàu nhất (~74 chỉ tiêu). Trang **Tổng quan dữ liệu** hiển thị nguồn tần suất
từng chỉ tiêu.

**Chọn thời điểm:** ô **Năm + Tháng/Quý** trên thanh công cụ lọc mọi trang theo kỳ đã
chọn (tức thời). Trang **Tinh chỉnh mô hình (ML)** cho phép grid-search siêu tham số
Isolation Forest / K-means, xem leaderboard và **Áp dụng / Khôi phục** tham số tối ưu
(API: `POST /api/tune/:freq`, `/api/tune/apply`, `/api/tune/reset`).

## Thư mục

```
web/
  server/  package.json, server.js          (Express)
  client/  package.json, vite.config.ts, tsconfig*.json, index.html
           src/  main.tsx, App.tsx, store.tsx, api.ts, format.ts, styles.css
                 components/ui.tsx
                 pages/  (12 trang)
```

> ⚠️ Kết quả ML là công cụ hỗ trợ kiểm toán, không thay thế kết luận của KTV. Ngưỡng
> pháp lý cần đối chiếu văn bản gốc NHNN.
