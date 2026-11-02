# Đưa Kotoba JLPT N3 lên Internet

## 1. Kiến trúc và giới hạn miễn phí

Kiểm tra tài liệu chính thức ngày **01/11/2026**:

- [Render Free](https://render.com/docs/free): 750 giờ instance/workspace/tháng;
  ngủ sau 15 phút không có request, mở lại thường mất khoảng một phút. Filesystem bị
  xóa khi ngủ/restart/deploy; Free không có persistent disk. Render Postgres miễn phí
  hết hạn sau 30 ngày, **không dùng** cho dự án này. HTTPS và URL `*.onrender.com` có sẵn.
  Build và băng thông có hạn mức riêng; xem Usage/Billing của tài khoản.
- [Neon Free](https://neon.com/pricing): $0, không cần thẻ thanh toán, 100 CU-giờ/tháng/project,
  1 GB lưu trữ/project, tự ngủ sau 5 phút. Cửa sổ instant restore giới hạn đến 6 giờ
  hoặc 1 GB thay đổi; không thay thế backup tải về.

Phù hợp việc học cá nhân và chấp nhận chờ khi mở lại. Không phải cam kết miễn phí vô hạn
hay SLA hoạt động liên tục. Giữ cả hai tài khoản ở Free, không bật tự nâng cấp hoặc
thêm dịch vụ trả phí. Khi hết quota có thể phải đợi reset. Mac tắt vẫn học được vì
server và database nằm trên dịch vụ hosting. Không cần mua tên miền.

## 2. Chuẩn bị và giữ lượt học cũ

1. Cài Python 3.12+, chạy lệnh local trong README. Không chạy Python 3.7.
2. Mở **đúng trình duyệt và origin cũ** `http://localhost:8765` (cùng hostname và port),
   không chuyển sang `127.0.0.1`. Giao diện mới tự chuyển `kotoba-session-v2` từ
   localStorage lên bảng `study_session` nếu server chưa có lượt học nào.
3. Kiểm tra nút **Tiếp tục học** nếu trước đó có lượt dở. Vào Dữ liệu & sao lưu, tải
   một backup JSON về máy. Nếu lượt dở ở trình duyệt/port khác, cần mở đúng origin đó
   trước khi migration. Chỉ SQLite cũ không thể chứa hàng câu vốn nằm trong trình duyệt.
4. Dừng server local bằng Ctrl+C trước khi chạy migration. Giữ nguyên
   `progress.sqlite3`; không xóa hoặc gửi file này lên GitHub.

Bản sao an toàn đã tạo trong lúc chuẩn bị code: `backups/before-online-work.sqlite3`.
Migration sẽ tạo thêm backup mới bao gồm dữ liệu mới nhất, bằng SQLite backup API
(bao gồm dữ liệu WAL đã commit). Backup chứa dữ liệu cá nhân, cần giữ riêng.

## 3. Tạo Neon và môi trường cục bộ

**Cấu hình hiện tại:** không cần đăng nhập (`APP_AUTH_REQUIRED=0`, cũng là mặc định).
Ai có URL cũng có thể xem và sửa tiến trình. Không cần `APP_PASSWORD_HASH`;
bước tạo hash dưới đây chỉ dùng nếu muốn bật lại đăng nhập bằng `APP_AUTH_REQUIRED=1`.

1. Đăng ký tại [Neon Console](https://console.neon.tech/), chọn **Free**.
2. Tạo project `kotoba-jlpt-n3`, chọn region gần bạn, ưu tiên gần region Render.
3. Trong **Connect**, chọn database/role, sao chép connection string đầy đủ.
   Giữ các tham số TLS `sslmode=require` và `channel_binding=require` nếu có.
   Có thể dùng URL pooled (`-pooler`) cho ứng dụng; không dùng URL thiếu TLS lên Internet.
4. Tạo hash mật khẩu cá nhân (nên ít nhất 12 ký tự, khác mật khẩu Neon):

   ```bash
   .venv/bin/python online.py
   ```

   Mật khẩu được nhập kín. Sao chép dòng hash Argon2, không đưa mật khẩu gốc vào source.
5. Tạo file `.env` trên Mac bằng editor, dựa vào `.env.example`. File này đã bị Git bỏ qua.
   Đặt URL và hash trong dấu nháy đơn để giữ nguyên các ký tự đặc biệt:

   ```dotenv
   DATABASE_URL='postgresql://YOUR_NEON_CONNECTION_STRING'
   APP_PASSWORD_HASH='$argon2id$YOUR_GENERATED_HASH'
   APP_ENV=production
   APP_AUTH_REQUIRED=0
   COOKIE_SECURE=1
   APP_TIMEZONE=Asia/Ho_Chi_Minh
   HOST=0.0.0.0
   JLPT_NO_BROWSER=1
   ```

   Đây là ví dụ, phải thay URL và hash thật. `server.py` và `migrate_sqlite.py`
   tự đọc `.env` ở thư mục gốc. Biến môi trường đã có từ Render hoặc process
   được ưu tiên; không cần `source .env`. Giá trị mật khẩu/hash không được nội suy.
   Import module trong unit tests không tự nạp `.env`, tránh chạm dữ liệu thật.

   Không dán `.env`, URL hoặc hash vào chat, issue, ảnh chụp công khai hoặc GitHub.

## 4. Chuyển dữ liệu SQLite lên Neon một lần

Migration thực tế ngày 02/11/2026 đã hoàn tất; xem [NEON_MIGRATION.md](NEON_MIGRATION.md).
Không cần nhập lại dữ liệu cho lần deploy đầu tiên.

Thực hiện **trước khi bắt đầu học trên bản online**:

```bash
.venv/bin/python migrate_sqlite.py --source progress.sqlite3 --backup-dir backups
```

Script tạo bản sao SQLite, đọc nguồn ở chế độ chỉ đọc, giữ ID, các field tiến trình,
lịch sử, settings và lượt học trên server. Nó kiểm tra từng field trước khi commit.
Ngày giờ có timezone được chuẩn hóa UTC; `last_day` giữ nguyên ngày học lịch sử.
Ngày học mới dùng `APP_TIMEZONE=Asia/Ho_Chi_Minh`, tránh đổi ngày do server chạy UTC.
Không tự đoán timezone cho timestamp cũ không có timezone: script dừng để xử lý đúng nguồn.

- Chạy lại cùng nguồn: `already_migrated: true`, không thêm sự kiện hoặc đè tiến trình online.
- Nguồn đã thay đổi trong khi database đích có lịch học: từ chối toàn bộ transaction.
  Không cố ghi đè. Dùng một Neon branch/database **trống** nếu muốn thử lại từ nguồn khác.
- Database đích mới deploy nhưng chỉ có seed cards vẫn nhận được migration.
- Thất bại giữa chừng: rollback, nguồn SQLite và bản backup vẫn còn.

Sau đó không học tiếp trên bản SQLite cũ; các thay đổi SQLite phát sinh sau migration
không tự đồng bộ. Dùng cùng URL online trên cả Mac và điện thoại.

## 5. Tạo repository an toàn và deploy Render

Để không vô tình upload SQLite, secrets hoặc 201 MB PDF, tạo gói nguồn cho deployment:

```bash
.venv/bin/python package_deploy.py
```

Giải nén `artifacts/kotoba-render.zip` vào **thư mục mới**, ví dụ `kotoba-online`.
Gói chỉ chứa code, web assets và dữ liệu bộ thẻ/nguồn cần cho chức năng import;
không chứa `.env`, database, backups, virtualenv hoặc PDF. Tạo **private repository**
trên GitHub và upload nội dung thư mục mới đó. Không dùng upload toàn bộ project gốc.
Nếu dùng Git, chạy `git status --short` và kiểm tra danh sách trước khi commit/push.
Không có Git repository được tạo hoặc đẩy tự động trong lần chuẩn bị này.

1. Đăng ký [Render](https://dashboard.render.com/), kết nối GitHub.
2. **New → Blueprint**, chọn repository; Render đọc `render.yaml`.
   Nếu tạo Web Service thủ công, dùng:
   - Runtime Python; instance **Free**; region gần Neon.
   - Build: `pip install -r requirements.txt`
   - Start: `python server.py`
   - Health check: `/healthz`
   - Không tạo Render Postgres, không gắn disk trả phí.
3. Nhập secret `DATABASE_URL` vào Environment; đặt `APP_AUTH_REQUIRED=0`.
   Chỉ cần `APP_PASSWORD_HASH` nếu chủ động bật lại đăng nhập.
   Trong UI Render dán **giá trị thô, không bọc dấu nháy**.
4. Các biến còn lại đã có trong YAML:

   | Biến | Giá trị |
   |---|---|
   | `APP_ENV` | `production` |
   | `COOKIE_SECURE` | `1` |
   | `HOST` | `0.0.0.0` |
   | `JLPT_NO_BROWSER` | `1` |
   | `APP_TIMEZONE` | `Asia/Ho_Chi_Minh` |
   | `PYTHON_VERSION` | `3.12.12` |

   Render cung cấp `PORT`; không cần tự đặt. Thiếu DB/hash/cookie an toàn thì server
   từ chối khởi động thay vì rơi về SQLite tạm.
5. Deploy và chờ **Live**. Mở URL HTTPS Render cung cấp, ví dụ
   `https://kotoba-jlpt-n3-xxxx.onrender.com` — đây là mẫu, không phải URL đã deploy.
6. Đăng nhập bằng mật khẩu gốc bạn dùng tạo hash. Kiểm tra tổng thẻ và tiến độ so với
   backup SQLite. Mở cùng URL trên điện thoại, đăng nhập, học một câu và xem Mac cập nhật.
   Logout phải chặn `/api/state` và `/api/export`. Thử restart service rồi kiểm tra lại.

Chỉ khi URL thật mở được, đăng nhập và kiểm tra tiến độ thành công mới coi là deploy xong.
Không dùng công cụ ping để giữ app luôn thức, vì tiêu hao quota và mất mục đích scale-to-zero.

## 6. Thêm vào màn hình chính

- **iPhone/iPad**: mở URL HTTPS bằng Safari → Chia sẻ → Thêm vào Màn hình chính → Thêm.
- **Android Chrome**: mở URL HTTPS → menu ⋮ → Cài đặt ứng dụng / Thêm vào màn hình chính.
- **Mac Chrome**: nếu trình duyệt hiện biểu tượng cài ứng dụng trên thanh địa chỉ, chọn cài.

Tên hiển thị là **Kotoba JLPT N3**. Hỗ trợ standalone tùy trình duyệt.
Bản đầu **cần mạng để học**: mất mạng hiện thông báo chưa xác nhận lưu, giữ nguyên
câu hỏi để gửi lại. Không lưu cache API/progress. Nếu mở app khi offline, service worker
hiện trang yêu cầu kết nối mạng; lần đầu chưa từng mở app vẫn cần Internet.

## 7. Cập nhật code và từ vựng

Cập nhật code trong repository rồi push; Render tự deploy nếu bật auto deploy.
Database Neon tồn tại độc lập với restart/deploy. Giữ `DATABASE_URL` cũ.

Vào **Dữ liệu & sao lưu → Nhập / cập nhật thẻ** sau khi đăng nhập:

- JSON: `{"cards": [{...}]}`; dùng nút tải mẫu trong ứng dụng.
- CSV UTF-8: header `id,term,reading,meaning,kind,tier,topic`.
  Các trường aliases/source_refs nếu có phải chứa JSON array hợp lệ trong ô CSV.
  `verified` nhận `true/false/1/0`.
- Thẻ cũ phải dùng **ID cũ**. ID trùng trong cùng file bị từ chối.
  Thẻ cùng mặt chữ/cách đọc/loại nhưng mang ID khác bị từ chối, không âm thầm tạo bản trùng.
- Cập nhật note/topic/metadata giữ tiến trình và lượt học.
- Đổi đáp án chính hoặc bỏ kỹ năng: ghi `import_log` gồm nội dung cũ/mới và tiến trình
  trước thay đổi; chỉ đặt lại kỹ năng bị ảnh hưởng theo hành vi cũ của app. Lịch sử
  câu trả lời giữ nguyên. Lượt học chứa đáp án cũ được kết thúc an toàn và có trong backup.
- Có backup transaction **trước mọi lần import**, không chỉ file lớn. Lỗi một thẻ sẽ
  rollback toàn bộ lần nhập.
- Khi cập nhật `data/cards.json` rồi deploy, startup chỉ thêm ID mới; không ghi đè
  chỉnh sửa thẻ cũ trong database. Muốn cập nhật thẻ cũ, import qua UI.

Chức năng đối chiếu Soumatome/từ điển và kiểm kê OCR vẫn có, chỉ người đăng nhập dùng được.
Tải file nguồn/cache trên Render là tạm; các **thẻ đã nhập** được giữ trong PostgreSQL.
PDF không nằm trong gói deploy; nếu cần mở PDF gốc, phải bổ sung tài nguyên riêng vào
private deployment. Việc bỏ PDF không ảnh hưởng quiz, spaced repetition hoặc tiến trình.

## 8. Sao lưu và khôi phục

**Hàng tuần**: Dữ liệu & sao lưu → Tải bản sao lưu. JSON gồm thẻ, progress, events,
settings và lượt đang học; lưu ở Mac hoặc nơi lưu trữ cá nhân khác.

Trước import/restore, server lưu snapshot trong **cùng database Neon** và giữ 5 bản gần
nhất để hạn chế dung lượng. Bấm **Bản sao lưu trước khi nhập / khôi phục** để tải.
Bản tự động hỗ trợ hoàn tác nhập nhầm, không bảo vệ khi mất toàn bộ Neon/account;
vì vậy cần giữ backup tải về ở ngoài Neon.

Khôi phục: chọn JSON → Khôi phục → xác nhận. App backup trạng thái hiện tại trước khi
thay thế trong transaction; giữ lại seed cards mới. Hỗ trợ backup v1/v2 trước đây.
Không phục hồi auth cookie từ backup học tập. Cần đăng nhập lại nếu đổi server.

Backup toàn bộ PostgreSQL (bao gồm audit, auth và snapshots), nếu đã có PostgreSQL tools:

```bash
pg_dump --dbname="$DATABASE_URL" --format=custom --file=backups/kotoba-full.dump
```

Khôi phục dump vào một Neon database/branch **trống** bằng URL đích được nạp cục bộ:

```bash
pg_restore --dbname="$RESTORE_DATABASE_URL" --no-owner --no-privileges backups/kotoba-full.dump
```

Dump có thể chứa phiên đăng nhập, cần bảo vệ như secrets. Khôi phục xong kiểm tra tiến độ,
rồi mới thay `DATABASE_URL` của Render. Không chạy `--clean` trên database đang học.
Để đổi mật khẩu, tạo hash mới, cập nhật Environment và xóa các dòng `auth_sessions`
qua Neon SQL Editor nếu muốn đăng xuất mọi thiết bị ngay lập tức.

## 9. Tự kiểm tra sau deploy

1. So sánh thẻ/progress/events với backup; thử Reading đúng và Meaning sai độc lập.
2. Học trên Mac, tiếp tục điện thoại; đóng trình duyệt giữa lượt rồi mở lại.
3. Bấm liên tục hoặc gửi lại khi mạng chậm: chỉ một event/câu hỏi.
4. Mở hai thiết bị cùng câu: câu đã đổi được tải lại, request cũ không ghi đè.
5. Logout: API dữ liệu/backup/import đều trả 401.
6. Restart Render: tiến trình vẫn còn; thử PWA và chiều rộng điện thoại.
7. Kiểm tra Billing/Usage Free của Render và Neon định kỳ.

Test tự động đã chạy được ghi tại `TEST_RESULTS.md`. Chưa kiểm thử được URL Render/Neon
của bạn hoặc cài thực tế trên iPhone/Android trước khi bạn tạo các dịch vụ đó.
