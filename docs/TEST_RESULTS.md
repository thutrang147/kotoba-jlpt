# Kết quả kiểm thử

## Cập nhật 02/11/2026 — migration Neon thật

- Local: 54 tests, 53 đạt; 1 test migration PostgreSQL bỏ qua ở lượt SQLite.
- Neon thật: 37/37 đạt, không bỏ qua (14 online/migration + 23 engine học).
- Kết nối Neon qua TLS thành công, tạo 10 bảng trong database đích trống.
- Migration: 5.258 thẻ, 55 progress, 94 events; đối chiếu từng trường thành công.
- SHA-256 SQLite gốc trước/sau không thay đổi; đã tạo backup mới.
- App khởi động với Neon: `/healthz` trả 200, `/api/state` chưa đăng nhập trả 401.
- Restore backup ghi tối đa 250 dòng/lô trong cùng transaction, giảm số lượt gọi Neon.
  Bộ test local kiểm tra restore thành công và rollback khi dữ liệu bị trùng/lỗi.
- Git bỏ qua `.env`, SQLite, backup, PDF; rà soát các file tracked không phát hiện secrets thật.
- Chi tiết và hướng dẫn deploy: [NEON_MIGRATION.md](NEON_MIGRATION.md).

## Lịch sử kiểm thử 01/11/2026

## Đã thực hiện

| Kiểm tra | Kết quả |
|---|---|
| Toàn bộ unit tests SQLite + regression dữ liệu | 52 tests: 51 đạt, 1 bỏ qua vì cần PostgreSQL |
| Logic học cũ chạy trên PostgreSQL thật | 23/23 đạt |
| Bộ test online chạy trên PostgreSQL thật | 14/14 đạt, gồm test migration được bỏ qua ở lượt SQLite |
| Chrome headless, giao diện thật | Đạt; không có lỗi JavaScript |
| Responsive | Không tràn ngang ở 320, 390, 430, 1280 px |
| Luồng học | Hoàn thành 10 thẻ, học tiếp lượt mới, reload tiếp tục đúng event |
| Hai phiên trình duyệt | Đọc cùng lượt học và tiến độ sau khi trả lời |
| Reading/Meaning | Reading đúng + Meaning sai hiện hai khung riêng, lưu độc lập |
| Mất kết nối | Hiện chưa xác nhận lưu, không sinh event khi offline |
| PWA | Manifest/icons/service worker hợp lệ; Chrome `Page.getInstallabilityErrors` trả danh sách rỗng trong profile thường |
| Xác thực | Login/logout, cookie flags, chặn GET/POST riêng tư trước login, chặn Origin khác, khóa sau nhiều lần sai |
| Chống trùng | Gửi cùng event đồng thời từ hai thread và **hai process** chỉ sinh một event |
| Dữ liệu cũ | Revision cũ bị từ chối; response bị mất có thể gửi lại an toàn |
| Restart | Khởi tạo lại ứng dụng giữ nguyên progress và lượt học |
| Import | JSON/CSV idempotent, metadata giữ progress, chặn identity trùng ID khác, log trước reset kỹ năng đổi đáp án |
| Backup/restore | Lưu lượt dở, snapshot trước thay đổi, dữ liệu restore lỗi được rollback |
| Gói deploy | Giải nén và khởi động được độc lập; 62 file, 4.417 seed cards, không có DB/secrets/PDF |
| Migration | So sánh từng field; giữ cards/progress/events/settings/session; nguồn giữ nguyên; chạy lại không ghi trùng; từ chối ghi đè tiến trình online |

Chạy migration thực tế trên **bản sao** SQLite hiện tại sang PostgreSQL thử nghiệm:
**5.258 cards, 54 progress, 92 events**, không xóa database gốc.
Có thêm bài test migration fixture chứa lượt học dở trên server.
Bản dự phòng cục bộ: `backups/before-online-work.sqlite3` (không đóng gói deploy).

PostgreSQL thử nghiệm chạy trên localhost, mỗi test dùng schema riêng, không kết nối Neon.
Test HTTP và Chrome dùng database tạm, không dùng tiến trình cá nhân.
Ảnh kiểm tra: `artifacts/mobile-study.png`, `artifacts/mobile-feedback.png`.

## Điều chỉnh các test cũ

Giữ các kiểm tra engine hiện có. Điều chỉnh fixture để phản ánh trạng thái project:

- Test import dùng một từ thử **chưa có trong bộ thẻ**; từ `実現` vốn đã tồn tại và
  yêu cầu mới phải ngăn thêm duplicate bằng ID khác.
- Test nguồn thiếu dùng cache tạm rỗng; cache đầy đủ có sẵn không còn che kết quả test.
- Test v9 chấp nhận metadata workbook bổ sung ở v10, vẫn so hash của nội dung gốc.
  Nguồn workbook không bị coi nhầm là tham chiếu trang OCR.
- Test seed v9 chạy database tạm, kiểm ID khớp seed hiện tại thay vì số lượng v9 cũ;
  không gọi init lên SQLite cá nhân.

## Chưa thể xác nhận

- Chưa tạo tài nguyên Render/Neon hoặc repository GitHub cho người dùng.
- Chưa có URL HTTPS public hoạt động; chưa kiểm thử cold start, migration Neon và restart Render thật.
- Chưa cài thực tế trên iPhone Safari/Android. Điều kiện PWA đã kiểm tra bằng Chrome;
  kiểm thử headless không thay cho thao tác Add to Home Screen trên thiết bị.
- Chưa giả lập bàn phím IME/virtual keyboard thật trên iPhone/Android.
- Chưa chứng nhận chất lượng OCR hoặc độ phủ sách; dữ liệu từ vựng gốc không bị biên soạn lại.

## Lệnh tái hiện

```bash
.venv/bin/python -m unittest -v
TEST_DATABASE_URL='postgresql://TEST_DATABASE' .venv/bin/python tests/postgres_regression.py
TEST_DATABASE_URL='postgresql://TEST_DATABASE' .venv/bin/python -m unittest -v tests.test_online
.venv/bin/python tests/browser_smoke.py
```

Browser test cần `pip install playwright`, Chrome đã cài hoặc biến
`PLAYWRIGHT_CHROMIUM` trỏ tới Chromium. PostgreSQL test tự tạo/xóa schema tên ngẫu nhiên;
role thử cần quyền CREATE SCHEMA. Không dùng database cá nhân làm TEST_DATABASE_URL.
