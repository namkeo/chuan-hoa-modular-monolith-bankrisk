# Backend Tính Điểm Bộ Tiêu Chí (FastAPI + MongoDB)

Hệ thống Backend phục vụ tính điểm, xếp hạng các tổ chức tín dụng theo bộ tiêu chí nghiệp vụ động, đọc cấu hình công thức, điều kiện và ngưỡng từ MongoDB (không hardcode).

## 🛠 Công Nghệ Sử Dụng

- **Framework**: FastAPI (Python 3.10+)
- **Database**: MongoDB
- **Driver Async**: Motor AsyncIOMotorClient
- **Validation & Serialization**: Pydantic v2
- **Tính toán số học chính xác**: `decimal.Decimal`
- **Testing**: Pytest & Pytest-Asyncio

---

## 📂 Cấu Trúc Thư Mục

```
source_code/be/
├── app/
│   ├── main.py                     # Entrypoint ứng dụng FastAPI
│   ├── core/                       # Config Settings, Database connection & Exceptions
│   ├── repositories/               # Async MongoDB Repositories
│   ├── routers/                    # FastAPI REST API Endpoints
│   ├── schemas/                    # Pydantic schemas cho API requests/responses
│   ├── services/                   # Formula AST Engine, Threshold, Condition & Scoring Engine
│   └── utils/                      # Helpers xử lý Decimal, ObjectId, Response
├── tests/                          # Automated Unit Tests (Pytest)
├── scripts/                        # Các script phụ trợ
│   ├── seed/                       # Scripts khởi tạo dữ liệu mẫu
│   │   ├── seed_data.py
│   │   └── ...
│   ├── data_loaders/               # Scripts nạp dữ liệu thực vào MongoDB
│   │   ├── clear_and_load_real_data.py
│   │   └── ...
│   └── db_utils/                   # Các công cụ kiểm tra & bảo trì DB
│       ├── recalculate_and_dedup_db.py
│       └── ...
├── requirements.txt                # Thư viện phụ thuộc
├── pytest.ini                      # Cấu hình Pytest
├── Dockerfile                      # Docker container build
├── docker-compose.yml              # Docker Compose setup
└── README.md                       # Hướng dẫn sử dụng
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy

### 1. Cài đặt môi trường Python & dependencies

```bash
python -m venv venv
# Windows:
venv\Scripts\activate

# Cài đặt các thư viện:
pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường MongoDB

Tạo file `.env` (hoặc thiết lập biến môi trường) nếu cần thay đổi URI mặc định:

```env
MONGO_URI=mongodb://admin:12345678@localhost:27017/
MONGO_DB_NAME=credit_scoring_db
```

### 3. Nạp dữ liệu mẫu (Seed Data)

Nạp dữ liệu mẫu bộ tiêu chí 2026, nhóm VỐN & CHẤT LƯỢNG TÀI SẢN, đối tượng `NH_001` và kỳ dữ liệu `2025`:

```bash
python seed_data.py
```

### 4. Chạy Unit Tests

```bash
pytest -v
```

### 5. Khởi chạy Server FastAPI Backend

```bash
uvicorn app.main:app --reload --port 8000
```

Truy cập Swagger UI tài liệu API tương tác tại: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📊 Các Endpoint API Chính

### 1. Kiểm tra dữ liệu trước khi tính
- `POST /tinh-diem/kiem-tra`
```json
{
  "bo_tieu_chi_id": "BTC_2026_V1",
  "doi_tuong_id": "NH_001",
  "ky_du_lieu": "2025"
}
```

### 2. Thực hiện tính điểm & Lưu snapshot
- `POST /tinh-diem/thuc-hien`
```json
{
  "bo_tieu_chi_id": "BTC_2026_V1",
  "doi_tuong_id": "NH_001",
  "ky_du_lieu": "2025",
  "luu_ket_qua": true
}
```

### 3. Truy xuất kết quả
- `GET /tinh-diem/ket-qua/{id}`
- `GET /tinh-diem/ket-qua?doi_tuong_id=NH_001&ky_du_lieu=2025`

### 4. Quản trị cấu hình CRUD
- `/bo-tieu-chi`: CRUD + `/cong-bo`
- `/nhom-tieu-chi`: CRUD
- `/chi-tieu`: CRUD + `/kiem-tra`
- `/du-lieu-tinh-diem`: CRUD + `/phe-duyet`
