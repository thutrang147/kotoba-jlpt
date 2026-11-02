# Migration Neon — 02/11/2026

Project Neon `kotoba-jlpt` đã kết nối thành công qua TLS bằng `DATABASE_URL`
đọc từ `.env`. Database đích trống trước migration. Đã tạo 10 bảng ứng dụng
và nhập dữ liệu trong transaction; đối chiếu từng trường sau commit.

| Dữ liệu | SQLite | Neon |
|---|---:|---:|
| Thẻ | 5.258 | 5.258 |
| Tiến trình kỹ năng, lịch ôn, streak, phase, mastered | 55 | 55 |
| Sự kiện/lịch sử học | 94 | 94 |
| Settings | 0 | 0 |
| Lượt học dở lưu trên server | 0 | 0 |

Tất cả nội dung đối chiếu khớp. SQLite gốc giữ nguyên, SHA-256 trước/sau giống nhau.
Backup: `backups/before-neon-20261102T144242646815Z.sqlite3`.
Báo cáo máy đọc được: `artifacts/neon-migration-verification.json` (Git bỏ qua).
App đã khởi động với Neon: `/healthz` trả 200; API riêng tư chưa đăng nhập trả 401.
Local có 54 tests: 53 đạt và 1 bỏ qua do chỉ chạy ở PostgreSQL.
Neon thật: **37/37 tests đạt**, không bỏ qua; 14 bài online/migration và 23 bài
logic học. Test dùng schema ngẫu nhiên riêng, không dùng tiến trình cá nhân ở `public`.
Báo cáo test: `artifacts/neon-tests.json` (Git bỏ qua).
Nếu lượt dở chỉ có trong localStorage của trình duyệt cũ, SQLite không chứa lượt đó;
mở đúng origin cũ để chuyển lượt sang server trước khi đổi sang URL Render.

Kiểm tra lại dữ liệu (chỉ đọc, thực hiện trước khi bắt đầu học trên Neon):

```bash
.venv/bin/python scripts/verify_neon_migration.py
```

Sau khi học trên Neon, tiến trình mới khác SQLite là bình thường.
Không nhập đè SQLite cũ lên tiến trình mới.

## GitHub Private và Render Free

1. Tạo mật khẩu đăng nhập ứng dụng bằng `.venv/bin/python online.py`.
   Nhập mật khẩu kín; giữ hash Argon2 trong `.env` và cấu hình Render.
   Không dùng mật khẩu Neon làm mật khẩu ứng dụng.
2. Commit thay đổi triển khai, xem lại danh sách file trước khi push:

   ```bash
   git status --short
   git add .gitignore .env.example config.py requirements.txt server.py migrate_sqlite.py package_deploy.py scripts/verify_neon_migration.py tests/test_config.py docs/
   git commit -m "Load local environment and verify Neon migration"
   ```

3. Trên GitHub tạo repository **Private**, để trống README/.gitignore/license.
   Thay `YOUR_USERNAME` trong các lệnh sau rồi chạy:

   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/kotoba-jlpt.git
   git push -u origin main
   ```

   `.env`, SQLite, backup, PDF và artifacts không được Git theo dõi.
   Chỉ push sau khi kiểm tra kết quả Neon thành công ở báo cáo này.

4. Render → New → Blueprint → cấp quyền vào đúng repository private.
   Chọn repo và nhánh `main`; `render.yaml` đã đặt `plan: free`.
   Không tạo thêm Render Postgres; dữ liệu nằm trên Neon.
5. Nhập `DATABASE_URL` từ `.env` và `APP_PASSWORD_HASH` vừa tạo vào các trường secrets.
   Có thể dùng giá trị `DATABASE_URL_POOLED` làm `DATABASE_URL` trên Render;
   app chỉ đọc tên biến `DATABASE_URL`. Giữ nguyên tham số TLS.
   Khi nhập trên Render, không thêm dấu nháy bao ngoài.
   Blueprint đã cấu hình production, cookie Secure, Python, timezone và HOST.
6. Kiểm tra dịch vụ là **Free** trước khi chọn deploy. Build:
   `pip install -r requirements.txt`; start: `python server.py`; health: `/healthz`.
7. Mở URL HTTPS Render, đăng nhập và kiểm tra số thẻ/tiến trình, học thử rồi reload.
   Không chạy migration lại trên Render, không đưa SQLite lên máy chủ.

Render Free tự ngủ sau 15 phút không có truy cập; lần mở lại có thể chậm.
Hướng dẫn chính thức: [Blueprint](https://render.com/docs/infrastructure-as-code),
[secrets](https://render.com/docs/configure-environment-variables),
[Free](https://render.com/docs/free).
