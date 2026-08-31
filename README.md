# Phần mềm phân tích & đánh giá rủi ro hệ thống ngân hàng (hỗ trợ kiểm toán NHNN)

Hệ thống phân tích dữ liệu chuỗi thời gian của hệ thống các ngân hàng, phát hiện bất thường (Isolation Forest), phân nhóm rủi ro (K-means), áp dụng hệ thống rule pháp lý của Ngân hàng Nhà nước (Expert Rule-Based System), chấm điểm rủi ro tổng hợp, nhận diện giai đoạn rủi ro cao và hỗ trợ kiểm toán viên (KTV) chọn ngân hàng / thời kỳ / chỉ tiêu cần kiểm tra sâu.

> ⚠️ **Lưu ý quan trọng:** Kết quả phân tích (gồm cả output ML) là **công cụ hỗ trợ** kiểm toán, **KHÔNG thay thế** kết luận chuyên môn của kiểm toán viên. Mọi ngưỡng pháp lý phải được KTV đối chiếu với văn bản gốc của NHNN. Các mục "Fraud/Failure Risk" là **chỉ báo nguy cơ (proxy)** dựa trên bất thường, pattern và vi phạm rule — không khẳng định chắc chắn gian lận hoặc đổ vỡ.

---

## 1. Khởi động nhanh hệ thống (Chỉ cần 1-Click trên Windows)

### 🚀 Chạy duy nhất tệp `run_web.bat`

Mở **Docker Desktop** và nhấp đúp chuột vào tệp **`run_web.bat`** (hoặc mở Terminal tại thư mục dự án và chạy `run_web.bat`):

```cmd
run_web.bat
```

Tệp `run_web.bat` tự động thực hiện toàn bộ quy trình:
1. **Khởi chạy CSDL & Storage:** Tự động kích hoạt container MongoDB (`port 27018`) và MinIO Object Storage (`port 9010/9011`).
2. **Kiểm tra & Import dữ liệu:** Kiểm tra dữ liệu trong MongoDB (`bank_risk_db` & `credit_scoring_db`) và MinIO. Nếu cơ sở dữ liệu rỗng, script tự động import dữ liệu JSON seed (19 collections) và mount tệp Excel/PDF vào MinIO. Nếu đã có dữ liệu, tự động bỏ qua để tối ưu thời gian.
3. **Khởi chạy ứng dụng Web & API:** Tự động build và khởi chạy ứng dụng Web (React SPA + Express Gateway) cùng 2 microservices FastAPI.

**Địa chỉ truy cập các dịch vụ sau khi chạy:**
- 🌐 **Web Application (Giao diện chính):** [http://localhost:4000](http://localhost:4000)
- ⚡ **FastAPI Bank Risk Gateway:** [http://localhost:8080/docs](http://localhost:8080/docs)
- 📊 **FastAPI Credit Scoring & Rating:** [http://localhost:8088/docs](http://localhost:8088/docs)
- 🗄️ **MinIO Web Console:** [http://localhost:9011](http://localhost:9011) (`minioadmin` / `minioadminpassword`)
- 🍃 **MongoDB:** `localhost:27018` (`admin` / `12345678`)

---

## 2. Kiến trúc Docker & CSDL (MongoDB & MinIO)

Hệ thống được container hóa hoàn toàn qua **Docker Compose** với 5 microservices độc lập:

| Dịch vụ | Container Name | Port (Host) | Nhiệm vụ | Cơ chế Volume & Dữ liệu |
|---|---|---|---|---|
| **`mongodb`** | `bank_risk_mongodb` | `27018:27017` | CSDL NoSQL lưu trữ dữ liệu thô, chỉ tiêu tài chính & kết quả tính toán | Docker Named Volume (`mongo_data_vol`). Dữ liệu được seed tự động qua `scripts/seed_if_empty.py` |
| **`minio`** | `bank_risk_minio` | `9010` (S3 API)<br>`9011` (Console) | Object Storage lưu trữ các tệp Excel báo cáo & PDF quy định | Mount trực tiếp `./minio_data:/data` chứa sẵn 89 file Excel/PDF trong bucket `bankrisk-files` |
| **`bank_risk_service`** | `bank_risk_fastapi` | `8080:8080` | REST API Gateway chính (FastAPI) | Đọc mã nguồn phân tích từ `bank_risk_service/src/` |
| **`xep_hang_service`** | `bank_risk_xep_hang` | `8088:8088` | REST API chấm điểm & xếp hạng TCTD (FastAPI) | Đọc mã nguồn xếp hạng từ `xep_hang_service/app/` |
| **`web_fe`** | `bank_risk_web_fe` | `4000:4000` | Unified Web FE (React SPA + Express Gateway) | Mã nguồn `web/client` và `web/server` |

**Lệnh thao tác Docker thủ công:**
```powershell
# Tắt toàn bộ hệ thống Docker
docker compose down

# Khởi chạy lại hệ thống
docker compose up -d --build
```

---

## 3. Vị trí thư mục dữ liệu

Thư mục `source_code` chứa mã nguồn và tệp cấu hình. Chương trình tự động nhận diện thư mục dữ liệu theo thứ tự ưu tiên:

1. Biến môi trường `BANKRISK_DATA_DIR` (nếu đặt).
2. File [`config/data_dir.txt`](config/data_dir.txt) — một dòng ghi đường dẫn thư mục dữ liệu.
3. Nếu chính `source_code` có file .xlsx → dùng luôn.
4. Tự dò thư mục cùng cấp chứa dữ liệu (ví dụ `..\data_all`).

---

## 4. Chạy Script Python CLI & Pipeline độc lập

Các script engine Python hiện nằm trong gói `bank_risk_service/src/` và `scripts/`:

```powershell
# Import dữ liệu thủ công vào MongoDB
python scripts/import_all_data.py

# Chạy pipeline phân tích cho 1 tần suất (quarterly | daily | monthly | yearly | combined)
python -m bank_risk_service.src.pipeline quarterly

# Sinh báo cáo Excel + HTML + CSV CRITICAL
python -m bank_risk_service.src.reporting

# Trích xuất candidate rule từ các PDF quy định
python -m bank_risk_service.src.pdf_rule_extractor

# Chạy hệ thống cảnh báo sớm (EWS)
python -m bank_risk_service.src.ews

# Chạy kiểm tra sức chịu đựng (Stress-test)
python -m bank_risk_service.src.stress_test
```

---

## 5. Cấu hình Mapping Cột & Rule Pháp Lý

### Mapping cột
Tất cả ánh xạ nhãn chỉ tiêu → tên feature chuẩn nằm trong [`config/column_mapping.yaml`](config/column_mapping.yaml). Khi file Excel có nhãn mới:
1. Mở trang **"1 · Tổng quan dữ liệu"** trên Giao diện Web → mục *"Nhãn chỉ tiêu CHƯA map"*.
2. Thêm nhãn vào `metric_aliases` dưới feature chuẩn tương ứng trong `column_mapping.yaml`.
3. Bấm nút **"🔄 Tính lại"** trên giao diện Web.

### Cấu hình Rule & Ngưỡng pháp lý
| File | Nội dung |
|---|---|
| [`config/regulatory_rules.yaml`](config/regulatory_rules.yaml) | Rule giới hạn/tỷ lệ an toàn (CAR, LDR, vốn ngắn hạn cho vay TDH, dự trữ thanh khoản, NPL…). Tích hợp ngưỡng giám sát 3 bậc QĐ 682/618 theo loại hình TCTD. |
| [`config/institution_types.yaml`](config/institution_types.yaml) | Loại hình TCTD từng đơn vị (NHTM quy mô lớn, vừa & nhỏ, công ty tài chính…) quyết định bộ ngưỡng áp dụng. |
| [`config/rating_rules.yaml`](config/rating_rules.yaml) | Scoring xếp hạng TCTD theo CAMELS. |
| [`config/model_config.yaml`](config/model_config.yaml) | Tham số Isolation Forest / K-means, trọng số chấm điểm, rule floor. |
| [`config/ews_config.yaml`](config/ews_config.yaml) | Hệ thống cảnh báo sớm (EWS): ngưỡng/vùng đệm từng chỉ tiêu. |
| [`config/stress_scenarios.yaml`](config/stress_scenarios.yaml) | Kịch bản stress-test (sốc NPL/RWA/run-off), giả định LGD. |

---

## 5a. Ngưỡng giám sát theo loại hình TCTD (QĐ 682 & QĐ 618)

Các rule áp **3 bậc ngưỡng** (`tiers_by_type` trong `regulatory_rules.yaml`) theo loại hình khai tại [`config/institution_types.yaml`](config/institution_types.yaml):

| Bậc | Ý nghĩa (QĐ 682, Phụ lục 3) | `finding_type` | `severity` |
|---|---|---|---|
| Ngưỡng 3 | Vi phạm tỷ lệ bảo đảm an toàn → xử lý theo pháp luật | `VIOLATION` | CRITICAL |
| Ngưỡng 2 | Nguy cơ dẫn tới vi phạm → khuyến nghị, cảnh báo | `WARNING` | HIGH |
| Ngưỡng 1 | Tăng cường theo dõi, tìm hiểu nguyên nhân | `WATCH` | MEDIUM |

- **Kiểm soát đặc biệt / Can thiệp sớm** → Gắn nhãn `SPECIAL_CONTROL` (bỏ qua ngưỡng 682/618 nhưng vẫn áp các rule pháp lý bắt buộc khác).
- **Chỉ Ngưỡng 3 mới được tính là `VIOLATION`** và kích hoạt ép điểm `CRITICAL` (`final_risk_score ≥ 90`).

---

## 5b. Hệ thống cảnh báo sớm — EWS ([bank_risk_service/src/ews.py](bank_risk_service/src/ews.py))

Mỗi bank-period tính toán các chỉ báo dẫn dắt (leading indicators):
- **proximity-to-limit** (khoảng cách tới ngưỡng mềm),
- **trend / acceleration** (xu hướng và gia tốc xấu đi),
- **volatility** (biến động bất thường),
- **breach streak** (chuỗi kỳ chớm vi phạm),
- **projected breach** (dự phóng số kỳ tới khi vi phạm).

Đưa ra các mức cảnh báo: **NORMAL / WATCH / WARNING / ALARM**.

---

## 5c. Stress-test — Sức chịu đựng vốn & thanh khoản ([bank_risk_service/src/stress_test.py](bank_risk_service/src/stress_test.py))

- **Vốn (Capital):** Sốc tín dụng (`NPL shock`) → ăn mòn vốn tự có & RWA → tính `CAR sau sốc` và nhu cầu tái cấp vốn.
- **Thanh khoản (Liquidity):** Sốc rút tiền gửi & haircut tài sản có thanh khoản cao.
- **Reverse Stress-Test (Điểm gãy):** Tính mức NPL tăng thêm tối đa để CAR rơi xuống mốc 8%.

---

## 5d. Tần suất "Kết hợp" (Combined Multi-Frequency) ([bank_risk_service/src/multi_frequency.py](bank_risk_service/src/multi_frequency.py))

Tích hợp dữ liệu đa tần suất (Tháng, Quý, Năm) trên lưới thời gian Tháng bằng cơ chế **as-of join point-in-time** (không nhìn trước tương lai). Tạo ra ~74 chỉ tiêu/bank-tháng cho toàn bộ pipeline phân tích.

---

## 6. Giao diện Web Application (12 Trang Chức Năng)

Giao diện Web React SPA (`web/client`) bao gồm 12 trang chức năng chuyên sâu:

1. **Tổng quan dữ liệu** — Thống kê file, số lượng ngân hàng, tỷ lệ khuyết thiếu.
2. **Giám sát rule pháp lý** — Vi phạm theo severity, căn cứ văn bản NHNN.
3. **Bảng điều khiển rủi ro** — Xếp hạng rủi ro tổng hợp, heatmap bank×kỳ.
4. **Phát hiện bất thường** — Mô hình Isolation Forest, feature deviation, nhập feedback KTV.
5. **Phân cụm Rủi ro** — Mô hình K-means, hồ sơ cụm, biểu đồ PCA 2D.
6. **Chuỗi thời gian** — Rolling z-score, giai đoạn rủi ro cao, systemic stress.
7. **Rủi ro tín dụng** — Tỷ lệ NPL, nợ nhóm 2, bao phủ dự phòng.
8. **Rủi ro thanh khoản** — LDR, vốn ngắn hạn cho vay TDH, dự trữ thanh khoản.
9. **Gian lận/Đổ vỡ (Proxy)** — Cảnh báo cờ đỏ tích hợp.
10. **Validation & Chất lượng** — Kiểm tra tính toàn vẹn dữ liệu.
11. **Theo dõi hiệu năng & Fine-tuning ML** — Tinh chỉnh tham số mô hình ML.
12. **Xuất báo cáo** — Xuất báo cáo Excel, HTML Executive Summary, CSV.

---

## 7. Xuất Báo Cáo

Lệnh sinh báo cáo tự động từ engine:
```powershell
python -m bank_risk_service.src.reporting
```
Tệp đầu ra lưu tại `outputs/`:
- `outputs/exports/bank_risk_report_<freq>.xlsx` (Excel chi tiết nhiều sheet)
- `outputs/reports/bank_risk_report_<freq>.html` (Báo cáo HTML trực quan)
- `outputs/exports/critical_banks_<freq>.csv` (Danh sách ngân hàng vi phạm CRITICAL)

---

## 8. Cấu trúc Thư mục Mã nguồn Cập nhật

```
source_code/
├── run_web.bat                 # Launcher duy nhất 1-click khởi chạy toàn bộ hệ thống
├── docker-compose.yml          # Cấu hình Docker Compose (5 microservices)
├── requirements.txt            # Python dependencies
├── README.md                   # Tài liệu hướng dẫn hệ thống
├── scripts/                    # Scripts import & seed dữ liệu
│   ├── seed_if_empty.py        # Kiểm tra & seed dữ liệu tự động
│   └── import_all_data.py      # Import dữ liệu JSON vào MongoDB
├── mongo_data/                 # Dữ liệu JSON seed ban đầu
│   └── init_json/              # bank_risk_db & credit_scoring_db
├── minio_data/                 # Dữ liệu file Excel & PDF cho MinIO
│   └── bankrisk-files/         # 89 file Excel/PDF báo cáo & quy định
├── bank_risk_service/          # Microservice FastAPI Phân tích Rủi ro
│   ├── main.py                 # FastAPI Entrypoint (Port 8080)
│   ├── Dockerfile
│   └── src/                    # Core Engine phân tích Python
│       ├── pipeline.py         # Pipeline phân tích chính
│       ├── rule_engine.py      # Engine kiểm tra luật NHNN
│       ├── anomaly_detection.py# Isolation Forest ML
│       ├── clustering.py       # K-means clustering ML
│       ├── ews.py              # Early Warning System
│       ├── stress_test.py      # Stress testing engine
│       └── reporting.py        # Xuất báo cáo Excel/HTML
├── xep_hang_service/           # Microservice FastAPI Chấm điểm & Xếp hạng TCTD
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py             # FastAPI Entrypoint (Port 8088)
│   │   ├── services/           # Scoring services & CAMELS evaluator
│   │   └── repositories/       # Mongo Repositories
│   └── scripts/                # Scripts tính toán & recompute
├── web/                        # Unified Web Frontend & Server Gateway
│   ├── Dockerfile
│   ├── client/                 # React SPA Frontend (Vite + TypeScript)
│   └── server/                 # Express Gateway Node.js (Port 4000)
├── config/                     # File YAML cấu hình rule, mapping & model
├── outputs/                    # Thư mục chứa báo cáo xuất ra
└── tests/                      # Pytest unit & integration tests
```

---

## 9. Chạy Kiểm Thử (Tests)

```powershell
# Pytest cho Bank Risk Service Engine
python -m pytest tests/ -q

# Pytest cho Credit Scoring Service
python -m pytest xep_hang_service/tests/ -q
```

---

## 10. Bảo mật & Tính tái lập

- **100% Local Execution:** Chạy hoàn toàn nội bộ trong Docker, không gửi dữ liệu ra ngoài internet hay API công cộng.
- **Tái lập kết quả (Reproducibility):** Cố định seed (`random_state=42`) cho tất cả các mô hình Machine Learning.
