# Bản đồ quyền sở hữu dữ liệu

> **Bước 1–3/6** đã xong, cùng V3 và V6.
> Cập nhật 25-09-2026 · 38 collection · 2 module · **7** vi phạm nền đang chờ xử lý.

## Tài liệu này dùng để làm gì

Quy tắc nền tảng của Modular Monolith: **mỗi bảng dữ liệu thuộc về đúng một module, và
chỉ module đó được chạm vào nó.** Mọi thành phần khác muốn dùng thì gọi API công khai
của module sở hữu.

Trước khi áp được quy tắc đó, phải biết hiện trạng: bảng nào thuộc về ai, và ai đang
vi phạm. Đó là nội dung tài liệu này. Bước này **không sửa một dòng mã chạy nào** —
nó chỉ vẽ bản đồ để năm bước sau có cái mà bám vào.

Hai tệp đi kèm:

| Tệp | Vai trò |
|---|---|
| [`data-ownership.yml`](data-ownership.yml) | Nguồn sự thật, đọc được bằng máy |
| [`../../scripts/audit/check_data_ownership.py`](../../scripts/audit/check_data_ownership.py) | Đối chiếu mã nguồn với bản đồ |

```bash
python scripts/audit/check_data_ownership.py             # báo cáo hiện trạng
python scripts/audit/check_data_ownership.py --baseline   # sinh lại danh sách nền
```

Mã thoát `0` nếu không có vi phạm mới, `1` nếu có. **Chưa gắn vào CI** — việc gắn
thuộc bước 6. Hiện tại nó là công cụ chạy tay, để bản đồ không bị lạc hậu âm thầm.

## Hai module và kho dữ liệu của chúng

| Module | Database | Mã nguồn | Cửa công khai | Số collection |
|---|---|---|---|---|
| `giam_sat_rui_ro` | `bank_risk_db` | `bank_risk_service/` | [`bank_risk_service/api.py`](../../bank_risk_service/api.py) | 31 |
| `xep_hang_tctd` | `credit_scoring_db` | `xep_hang_service/app/` | [`xep_hang_service/app/api.py`](../../xep_hang_service/app/api.py) | 7 |

Từ bước 3, **cửa công khai là thứ duy nhất bên ngoài được import**. Không import
`bank_risk_service.src.*` hay `xep_hang_service.app.*` từ ngoài module, không truy vấn
collection của module khác.

Ba vùng **không sở hữu dữ liệu nào**, nên mọi truy cập MongoDB từ đây đều là vi phạm:

- `web/` — phải là BFF thuần, chỉ gọi HTTP
- `scripts/` — script vận hành cấp gốc, phải gọi use case của module
- `xep_hang_service/scripts/` — thuộc module B nhưng nằm ngoài `app/`

## Ký hiệu trong bảng

`A` mã module giám sát rủi ro · `B` mã module xếp hạng · `S` script cấp gốc ·
`Sb` script của module B · `W` web · **in đậm** = vi phạm ranh giới

## Module `giam_sat_rui_ro` — 31 collection

### Nguồn đã chuẩn hoá từ workbook Excel

| Collection | Ghi bởi | Đọc bởi | Ghi chú |
|---|---|---|---|
| `raw_panel_data` | **S** | A, **S** | Panel dạng dài, nguồn của mọi thứ phía sau |
| `raw_files` | **S** | A | Siêu dữ liệu 83 workbook |
| `unmapped_labels` | **S** | A | Nhãn Excel chưa map được, để rà lại |
| `regulatory_rules_config` | **S** | A | Bản sao của `regulatory_rules.yaml` |

### Kết quả phân tích, dạng bản ghi

| Collection | Ghi bởi | Đọc bởi | Ghi chú |
|---|---|---|---|
| `risk_scores` | **S** | A, **S** | |
| `bank_rankings` | **S** | A | |
| `rule_findings` | **S** | A | Bản **đầy đủ** — xem V3 |
| `anomalies` | **S** | A | |
| `clusters` | **S** | A | |
| `ews_indicators` | **S** | A | |
| `stress_test_results` | **S** | A | |
| `high_risk_periods` | **S** | A | |
| `systemic_stress` | **S** | A | |
| `validation_findings` | **S** | A | |
| `time_series_data` | **S** | A | ⚠️ V5 — người ghi không bao giờ chạy |
| `frequency_summaries` | **S** | — | ⚠️ V4 — mồ côi |

### Kết quả phân tích, bản do `api_export` ghi lại

| Collection | Ghi bởi | Đọc bởi | Ghi chú |
|---|---|---|---|
| `computed_rule_findings` | A, **S** | A | ⚠️ V3 — **bị cắt còn 5.000 dòng**, bên đọc lại ưu tiên bản này |
| `computed_anomalies` | A, **S** | A | ⚠️ V3 |
| `computed_clusters` | A, **S** | A | ⚠️ V3 |
| `computed_ews_indicators` | A, **S** | A | ⚠️ V3 |
| `computed_stress_test_results` | A, **S** | A | ⚠️ V3 |

### Payload phục vụ API

| Collection | Ghi bởi | Đọc bởi | Ghi chú |
|---|---|---|---|
| `api_payloads` | A, **S** | A, **S**, **W** | ⚠️ V1 — web đọc thẳng |
| `api_meta` | A, **S** | A | |
| `api_performance` | A, **S** | A | |
| `api_pdf_status` | A, **S** | A | |

### Phụ trợ — mồ côi toàn bộ

| Collection | Ghi bởi | Đọc bởi | Đã bị thay bởi |
|---|---|---|---|
| `pipeline_meta` | **S** | — | `api_meta` |
| `performance_logs` | **S** | — | `api_performance` |
| `performance_suggestions` | **S** | — | `api_performance` |
| `user_feedback` | **S** | — | `api_performance` |
| `pdf_file_status` | **S** | — | `api_pdf_status` |
| `pdf_rule_candidates` | **S** | — | `api_pdf_status` |

## Module `xep_hang_tctd` — 7 collection

| Collection | Ghi bởi | Đọc bởi | Ghi chú |
|---|---|---|---|
| `BoTieuChi` | B, **Sb** | B | |
| `NhomTieuChi` | B, **Sb** | B | |
| `ChiTieu` | B, **Sb** | B | |
| `DoiTuongDanhGia` | B, **Sb** | B, **W** | ⚠️ V1 — web đọc thẳng |
| `DuLieuTinhDiem` | B, **Sb** | B | |
| `DuLieuSaiPham` | B, **Sb** | B | Nguồn điểm định tính |
| `KetQuaTinhDiem` | B, **Sb** | B, **W**, **S** | ⚠️ V1 — web và script gốc đọc thẳng |

Module này có một điểm sáng: **toàn bộ truy cập từ mã ứng dụng đi qua repository**
(`collection_name` khai báo trong `app/repositories/`), không chỗ nào rải tên collection
trong service hay router. Đó là nền tốt cho bước 3.

## Năm phát hiện

### V1 — Web đọc thẳng database · ✅ ĐÃ XỬ LÝ ở bước 2

`web/server/server.js` từng bỏ qua API của **cả hai** module để đọc thẳng collection
ở bốn điểm: `api_payloads` (dòng 92), `KetQuaTinhDiem` (133 và 188),
`DoiTuongDanhGia` (248). Đã xoá toàn bộ, cùng với `import { MongoClient }` và
dependency `mongodb` trong `web/server/package.json`, `web/package.json` và lockfile.
Biến môi trường `MONGO_URI` của `web_fe` trong `docker-compose.yml` cũng đã bỏ, và
`depends_on: mongodb` — web không còn quan hệ nào với cơ sở dữ liệu.

Baseline giảm 42 → 39.

**Còn hai bản sao dữ liệu của module khác nằm trong web** — cùng loại vi phạm nhưng
không phải MongoDB nên không vào baseline:

| Vị trí | Nội dung | Rủi ro |
|---|---|---|
| `server.js` · `DEFAULT_BANKS` | 31 TCTD ghi cứng trong mã | Lạc hậu âm thầm: TCTD đổi tên hoặc mới cấp phép sẽ không xuất hiện |
| `server.js` · đọc `xep_hang_service/scripts/precomputed_31_rankings.json` | Tệp riêng của module B | Web phụ thuộc đường dẫn nội bộ của module khác |

Cả hai hiện là tầng dự phòng cuối, giữ để giao diện còn render khi module xếp hạng
ngừng chạy. Nên xoá ở bước 4, khi hai tiến trình gộp lại thì "module B chết" đồng
nghĩa với "web chết" và tầng dự phòng này mất ý nghĩa.

### V2 — Module không tự ghi được dữ liệu của mình · nặng · bước 3

**22 trong 31** collection của `giam_sat_rui_ro` chỉ được ghi bởi script cấp gốc:

| Script | Số collection ghi | Có trong luồng khởi động? |
|---|---|---|
| `scripts/import_to_mongodb.py` | 21 | có |
| `scripts/copy_api_to_mongodb.py` | 16 | **không** |
| `scripts/import_baseline_to_mongodb.py` | 5 | **không** |
| `scripts/verify_and_compare.py` | 5 | **không** |

Module đọc dữ liệu mà nó không tự sản xuất được, nên **chưa thật sự sở hữu** dữ liệu đó.
Ba script không nằm trong luồng khởi động lại vẫn có quyền `drop()` rồi ghi lại —
`verify_and_compare.py` xoá và ghi lại toàn bộ 5 collection `computed_*` dù tên nó là
"verify". Một cái tên hứa chỉ đọc mà thực tế ghi là bẫy chờ người sau.

### V3 — Hai bản thể hiện cùng một dữ liệu · ⚠️ ĐÃ SỬA PHẦN MẤT DỮ LIỆU · cấu trúc còn lại ở bước 3

Năm cặp collection giữ **cùng một dữ liệu logic**, hai người ghi khác nhau:

| Bản đầy đủ (ghi bởi `import_to_mongodb`) | Bản rút gọn (ghi bởi `api_export`) |
|---|---|
| `rule_findings` | `computed_rule_findings` |
| `anomalies` | `computed_anomalies` |
| `clusters` | `computed_clusters` |
| `ews_indicators` | `computed_ews_indicators` |
| `stress_test_results` | `computed_stress_test_results` |

Bên đọc **ưu tiên bản `computed_*`**, chỉ dùng bản đầy đủ khi bản kia rỗng. Mà bản
`computed_*` bị cắt cứng ở 5.000 dòng trong `api_export.py`. Kết quả: với tần suất
`combined`, 9.747 trong 14.747 phát hiện không bao giờ lên tới giao diện, trong đó có
489 vi phạm mức CRITICAL thuộc 23 kỳ báo cáo — các kỳ đó trông như không có vi phạm.

**Đây là lý do bước 1 không phải việc giấy tờ.** Không ai cố tình làm mất dữ liệu; lỗi
này sống được vì không có tài liệu nào nói rõ bảng nào là bản chính. Bản đồ này nói rõ
điều đó.

**Đã sửa 25-09-2026:** `api_export.py` thay `insert_many(list[:5000])` bằng
`_insert_all()` chèn theo lô 1.000 bản ghi, và ghi log số lượng thực ghi. Đo lại trên
stack thật sau khi chạy lại cả 5 tần suất:

| Tần suất | Trước | Sau |
|---|---|---|
| `combined` | 5.000 | **14.747** |
| `daily` | 5.000 | **8.022** |
| `monthly` | 5.000 | **7.732** |
| `quarterly` | 3.377 | 3.377 (vốn dưới ngưỡng) |
| `yearly` | 545 | 545 (vốn dưới ngưỡng) |

Với `combined`: vi phạm CRITICAL từ 295 → **784**, số kỳ báo cáo có mặt từ 13 → **37**.
Thẻ KPI và bảng chi tiết trên giao diện giờ khớp nhau — trước đây KPI báo 784 CRITICAL
trong khi bảng chỉ liệt kê được 295.

**Chưa sửa — còn hai chốt cắt đang ngủ:** `build_payload()` vẫn giới hạn
`limit=8000` cho `scores` và `anomalies`. Hiện chưa chạm ngưỡng (cao nhất là `daily`
với 5.694 dòng), nhưng dữ liệu là chuỗi thời gian tăng dần theo từng kỳ mới, nên sẽ
chạm. Phần cấu trúc của V3 — hai collection cho cùng một dữ liệu, hai người ghi — vẫn
còn, để xử lý ở bước 3.

### V4 — Bảy collection mồ côi · nhẹ · bước 5

Được ghi mỗi lần nạp dữ liệu nhưng **không nơi nào đọc**, vì đều đã bị thay bởi một
payload tổng hợp (xem bảng "Phụ trợ" ở trên). Nên xoá khi chia lại module.

### V5 — Đọc dữ liệu không bao giờ được ghi · trung bình · bước 2

`overview_router.py:372` đọc `time_series_data`, nhưng collection này chỉ được ghi bởi
`scripts/copy_api_to_mongodb.py` — script **không** nằm trong luồng khởi động
(`run_web.bat` chỉ gọi `seed_if_empty.py` → `import_to_mongodb.py`).

Trong vận hành bình thường collection này **luôn rỗng**, nên nhánh đọc đó luôn rơi vào
phương án dự phòng. Cần xác nhận với người phụ trách trang Time Series xem đây là tính
năng chưa hoàn thiện hay tàn dư cần xoá.

### V6 — Seeding module xếp hạng không thể chạy · ✅ ĐÃ XỬ LÝ

Phát hiện khi chạy thật trên Docker ngày 25-09-2026. `run_web.bat` gọi
`seed_if_empty.py` **bên trong container `bank_risk_service`**, nhưng script đó lại
đi nạp dữ liệu cho module xếp hạng bằng cách import xuyên biên giới:

```python
sys.path.insert(0, str(PROJECT_ROOT / "xep_hang_service"))
from xep_hang_service.scripts.load_all_31_excel_rankings import process_all_rankings
```

Container `bank_risk_service` **không chứa mã của `xep_hang_service`**, nên lệnh
import luôn thất bại. Script bắt lỗi rồi chuyển sang nạp từ `mongo_data/init_json/`
— thư mục không có trong repo — và in ra:

```
[!] Dynamic credit scoring calculation failed: No module named 'xep_hang_service'
[✓] Credit scoring MongoDB JSON seeding complete!     <-- báo thành công
```

Kết quả đo được: `KetQuaTinhDiem = 0`, `DoiTuongDanhGia = 0`. Toàn bộ chức năng xếp
hạng không có dữ liệu, mà quy trình khởi động vẫn báo thành công và thoát với mã 0.

Container `xep_hang_service` cũng không được mount `./data`, nên chạy lại script ở
đúng chỗ cũng chưa đủ — cần cả hai: chạy đúng container **và** mount nguồn Excel.

Đây chính là V2 biểu hiện lúc chạy: một script cấp gốc cố ghi dữ liệu của module
khác bằng `sys.path`, và thất bại lặng lẽ. Trước bước 2, các tầng dự phòng trong
`server.js` che kín lỗi này — giao diện vẫn hiện 31 TCTD lấy từ tệp precomputed, nên
không ai biết cơ sở dữ liệu trống rỗng.

**Cách sửa (25-09-2026) — mỗi module tự nạp dữ liệu của mình:**

| Thay đổi | Nội dung |
|---|---|
| `xep_hang_service/scripts/seed_if_empty.py` | **Mới.** Module tự kiểm tra và tự nạp, bằng mã và dữ liệu của mình. Không tìm thấy file Excel thì **trả mã lỗi 1**, không báo thành công |
| `scripts/seed_if_empty.py` | Bỏ toàn bộ khối `credit_scoring_db`, bỏ `sys.path.insert` xuyên module, bỏ hai import chết (`json_util`, `BATCH_SIZE`) |
| `docker-compose.yml` | Mount `./data:/app/data:ro` vào `xep_hang_service` — thiếu mount này thì chạy đúng container vẫn không có nguồn Excel |
| `run_web.bat` | Gọi seeding cho **cả hai** module, mỗi cái trong container của nó; xếp hạng thất bại thì dừng lại báo người dùng |

Kết quả đo: `KetQuaTinhDiem = 31`, `DoiTuongDanhGia = 31`. Ba endpoint xếp hạng đều trả
`message: "Thành công"` — tức đi qua API của module, không phải tầng dự phòng. Chạy lại
lần hai thì bỏ qua đúng như thiết kế. Baseline giảm 39 → 38.

## Luật áp dụng từ nay

1. Thêm collection mới → khai báo vào `owns` của đúng một module trong `data-ownership.yml`.
2. Cần dữ liệu của module khác → gọi API công khai của nó, **không** truy vấn kho của nó.
3. Chạy `check_data_ownership.py` trước khi mở pull request. Có vi phạm mới thì không merge.
4. Xử lý xong một vi phạm nền → **xoá dòng đó khỏi `baseline`**. Danh sách chỉ được ngắn đi.

## Tiến độ đốt nợ

| Mốc | Số dòng trong `baseline` | Trạng thái |
|---|---|---|
| Bước 1 — lập bản đồ | 42 | ✅ xong 25-09-2026 |
| Bước 2 — bịt web | 39 | ✅ xong 25-09-2026 |
| V6 — seeding module B | 38 | ✅ xong 25-09-2026 |
| Bước 3 — dựng `api.py` | **7** | ✅ xong 25-09-2026 |
| Bước 4 — gộp tiến trình | 7 | chưa bắt đầu |
| Bước 5 — chia theo năng lực | 0 | chưa bắt đầu |
| Bước 6 — gắn vào CI | 0, cưỡng chế tự động | chưa bắt đầu |

### Bước 3 đã thay đổi những gì

Bảy dòng còn lại trong `baseline` đều là `xep_hang_service/scripts/ → …` — các script
nạp dữ liệu và tiện ích của module B, cần chuyển sang dùng `app/api.py`. Để bước 5.

| Thay đổi | Nội dung |
|---|---|
| `bank_risk_service/api.py` | **Mới.** Cửa công khai module A: `is_seeded`, `seed_if_empty`, `rebuild_all`, `rebuild_frequency`, `get_payload`, `available_frequencies`, `health` |
| `xep_hang_service/app/api.py` | **Mới.** Cửa công khai module B: `is_seeded`, `seed_if_empty`, `recalculate_all`, `count_results`, `list_doi_tuong`, `get_lich_su`, `health` |
| `scripts/import_to_mongodb.py` → `bank_risk_service/src/db_seed.py` | 280 dòng logic ghi 21 collection **chuyển vào trong module**, đổi sang import tương đối. Script cấp gốc còn lại 35 dòng gọi qua cửa công khai |
| `scripts/{copy_api_to_mongodb,import_baseline_to_mongodb,verify_and_compare}.py` → `bank_risk_service/scripts/` | Cả ba đều import `src.*`, tức là nội bộ module A. Chuyển về đúng nhà, không sửa logic |
| `scripts/seed_if_empty.py` | Không còn tự mở MongoDB; hỏi trạng thái qua `api.health()` / `api.seed_if_empty()` |
| `xep_hang_service/scripts/seed_if_empty.py` | Chuyển sang gọi `app/api.py` thay vì chạm collection |

**Sửa kèm — pipeline từng chạy hai lần mỗi tần suất.** `db_seed` gọi
`export_frequency(freq)` rồi `build_payload(freq)` ngay sau đó, mà `export_frequency`
bên trong đã gọi `build_payload`. Với `combined` (~100 giây/lượt) là chạy không hai
lần. Đã thêm tham số `payload` cho `export_frequency` để dựng một lần rồi dùng lại.

### Bước 2 đã thay đổi những gì

| Tệp | Thay đổi |
|---|---|
| `web/server/server.js` | Xoá 4 khối đọc MongoDB và `import { MongoClient }`; sửa lỗi coi "kết quả rỗng" là thất bại; `/lich-su` trả 503 thay vì báo thành công với danh sách rỗng |
| `web/server/package.json` · `package-lock.json` | Bỏ dependency `mongodb` — **bắt buộc đồng bộ lockfile**, vì Dockerfile dùng `npm ci` sẽ thất bại nếu hai tệp lệch nhau |
| `web/package.json` | Bỏ dependency `mongodb` |
| `docker-compose.yml` | `web_fe`: bỏ `MONGO_URI` và `depends_on: mongodb` |
| `web/server/server.js` | `resolveProjectRoot()` — sửa lỗi `PROJECT_ROOT` trỏ sai trong container |
| `tests/conftest.py` | Thêm `bank_risk_service/` vào `sys.path` — khôi phục 67 test |

### Kiểm chứng trên stack Docker thật (25-09-2026)

| Kiểm tra | Kết quả |
|---|---|
| `npm ci` trong image `web_fe` | ✅ 69 gói, không có `mongodb` |
| `grep MongoClient` trong image | ✅ 0 |
| `/api/health` | ✅ `fastApiConnected: true`, `projectRoot: /app`, `apiDirExists: true` |
| `/api/data/combined` qua FastAPI | ✅ HTTP 200 |
| `/api/data/combined` khi tắt FastAPI | ✅ HTTP 200 từ tệp JSON |
| `/tinh-diem/ket-qua` | ✅ `message: "Thành công"` — đi qua API của module, không phải fallback |
| Bộ test Python | ✅ 67 passed |

**Nghịch lý đo được:** đường chính (qua FastAPI → MongoDB) trả về **5.000** phát hiện,
còn tầng dự phòng (đọc tệp JSON) trả về **14.747**. Tầng dự phòng đang cho dữ liệu
đầy đủ hơn đường chính — hệ quả trực tiếp của V3.
