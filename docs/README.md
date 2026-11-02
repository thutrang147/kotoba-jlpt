# Kotoba JLPT N3

Ứng dụng học cá nhân Python + HTML/CSS/JavaScript, giữ logic Reading/Meaning,
10 thẻ/lượt và spaced repetition. Bản online dùng Render Free + Neon PostgreSQL,
đăng nhập cá nhân, tiếp tục lượt học giữa thiết bị và PWA.

**Chưa deploy public.** Cần tạo Neon/Render và cấu hình secrets theo [DEPLOY.md](DEPLOY.md).
Không cần mua domain. Chính sách miễn phí có hạn mức và có thể thay đổi.

## Chạy local

Các lệnh bên dưới chạy từ thư mục gốc `jlpt-local`, nơi có `server.py`.

Cần Python **3.12+**. Máy hiện có thể trỏ `python3` vào Python 3.7, nên dùng `python3.12`.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py
```

Mở **http://localhost:8765**. Không đặt `DATABASE_URL` thì tiếp tục dùng SQLite cũ.
Chế độ local mặc định chỉ bind `127.0.0.1`; chưa cấu hình hash thì không hỏi mật khẩu.
Production bắt buộc PostgreSQL + mật khẩu hash + cookie Secure, thiếu sẽ không khởi động.

Lượt học v2 trong localStorage tại đúng origin cũ được tự chuyển lên server một lần.
Sau migration sang Neon, dùng bản online làm nguồn tiến trình duy nhất.

## Deploy, migration, backup

Làm theo [DEPLOY.md](DEPLOY.md), gồm hướng dẫn Neon, Render, giữ SQLite cũ, secrets,
import JSON/CSV, backup/restore và thêm vào màn hình chính.

- `database.py`: adapter SQLite/PostgreSQL, transaction dùng chung, khóa giữa workers.
- `online.py`: Argon2, cookie session lưu database, lượt học có revision.
- `migrate_sqlite.py`: backup trước, kiểm tra từng field, migration nguyên tử, chống chạy trùng.
- `render.yaml`: Web Service **Free**, không dùng Render Postgres hoặc disk tạm để lưu tiến trình.
- `package_deploy.py`: đóng gói nguồn triển khai theo danh sách cho phép, loại DB và secrets.
- `web/manifest.webmanifest`, `web/sw.js`: PWA chỉ dùng mạng, không cache tiến trình.

## Kiểm thử

```bash
.venv/bin/python -m unittest -v
# Database thử riêng; tests tự tạo và xóa schema test_<uuid>:
TEST_DATABASE_URL='postgresql://...' .venv/bin/python -m unittest -v tests.test_online
TEST_DATABASE_URL='postgresql://...' .venv/bin/python tests/postgres_regression.py
# Cần pip install playwright và Google Chrome:
.venv/bin/python tests/browser_smoke.py
```

Xem [TEST_RESULTS.md](TEST_RESULTS.md) cho kết quả và các giới hạn kiểm thử.
Các ghi chép bản local trước đây giữ ở `README_LOCAL_HISTORY.md`; mô tả SQLite/localStorage
trong tài liệu lịch sử không áp dụng cho bản online.

## Cấu trúc thư mục

- `docs/`: toàn bộ tài liệu Markdown, hướng dẫn deploy và ghi chép kiểm kê.
- `scripts/`: công cụ xây bộ thẻ, kiểm kê OCR và cập nhật metadata qua các phiên bản.
- `tests/`: kiểm thử ứng dụng, PostgreSQL và trình duyệt.
- `web/`: giao diện HTML, CSS, JavaScript và tài nguyên PWA.
- `data/`: bộ thẻ, dữ liệu nguồn và kết quả đối chiếu OCR.
- `source_books/`: sách PDF gốc.
- `backups/`: bản sao lưu database cá nhân.
- `artifacts/`: gói triển khai và ảnh chụp kiểm thử.

Code chạy app, cấu hình và `start.command` nằm ở thư mục gốc.
Ví dụ chạy công cụ: `.venv/bin/python scripts/audit_coverage.py`.
Các script xây bộ thẻ có thể ghi đè `data/cards.json`; chỉ chạy khi cần cập nhật dữ liệu.
Các lệnh cũ trong tài liệu lịch sử dùng tên script ở thư mục gốc;
hiện các công cụ này nằm trong `scripts/`.
