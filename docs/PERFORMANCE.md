# Độ trễ khi học — 02/11/2026

Mỗi thao tác trước đây mở kết nối PostgreSQL mới; một POST học còn mở riêng
transaction xác thực và transaction cập nhật lượt học. Bản tối ưu:

- Tái sử dụng kết nối bằng psycopg-pool, tối đa 4 kết nối/process.
- Kiểm tra kết nối trước khi dùng; tự đóng kết nối rảnh sau 60 giây.
- Xác thực và cập nhật POST dùng cùng transaction; gửi kết quả sau commit.
- Giữ advisory lock, revision và event ID để bảo vệ thao tác đồng thời/retry.
- Bỏ một truy vấn kiểm tra event lặp bên trong transaction đã kiểm tra event đó.
- Nút hiện “Đang lưu câu trả lời…” hoặc “Đang chuyển câu…”, chặn bấm lặp.

## Phép đo

Đo từ máy local tới Neon, trong schema thử riêng; 12 thao tác mỗi lượt,
gồm 7 lần trả lời và 5 lần chuyển câu. Không chạm dữ liệu cá nhân.

| Thao tác | Trung vị trước | Trung vị sau |
|---|---:|---:|
| Lưu đáp án | 1.871 ms | 614 ms |
| Chuyển câu | 924 ms | 324 ms |

Các phép đo gọi logic server trực tiếp, không gồm HTTP/browser hoặc Render.
Không phải cam kết tốc độ site: độ trễ mạng, region và khởi động lại dịch vụ vẫn ảnh hưởng.
Chi tiết mẫu: `artifacts/latency-before.json`, `artifacts/latency-after.json` (Git bỏ qua).

Kiểm tra sau thay đổi: 56 tests local đạt, 1 test PostgreSQL bỏ qua ở lượt local;
15/15 tests online trên Neon đạt, gồm hai process trả lời đồng thời, retry,
revision cũ, rollback và migration. Chrome smoke đạt: hoàn thành 10 thẻ,
tiếp tục lượt sau, reload, hai phiên và mất mạng; không có lỗi JavaScript.

Pool dùng quy tắc commit/rollback chuẩn của
[psycopg-pool](https://www.psycopg.org/psycopg3/docs/advanced/pool.html).
Giữ Render và Neon ở region gần nhau để giảm thời gian truyền giữa hai dịch vụ.
