# Kotoba N3 v7 — kiểm kê thực tế và giới hạn

## Kết luận quan trọng

**Chưa thể xác nhận đầy đủ toàn bộ từ/cụm trong 4 sách Soumatome.** Đừng coi số thẻ hoặc số ứng viên OCR là số từ của sách. Bản này là bản nâng cấp khả năng **tìm mục còn thiếu và bổ sung có kiểm soát**, không phải lời cam kết đã chép hết mọi trang.

### Bộ học dựng sẵn (không cần internet)

- 3.930 thẻ: 3.785 từ/cụm từ và 145 mẫu ngữ pháp; giữ nguyên ID và đáp án của v6.
- 191 thẻ đã đánh dấu `verified: true` (xác minh một mục, không tương đương với rà hết trang).
- Bộ ảnh gốc gồm 4 PDF: 469 trang, đã OCR nhưng OCR có trang lỗi/không có nội dung.
- Có thể học trắc nghiệm, chuyển sang gõ theo số lần đúng, tách đọc kanji/hiểu nghĩa. Tiến trình lưu SQLite trên Mac.

### Bảng kiểm kê 469 trang

Sinh bằng `python3 source_coverage.py` hoặc bấm **Kiểm kê từng trang PDF** ở **Dữ liệu & sao lưu**:

- `data/book_page_audit.csv`: từng trang, số mục OCR được khớp/không khớp với kho từ và số thẻ có nguồn chỉ tới trang.
- `data/ocr_not_in_deck.csv`: các **lượt xuất hiện** ứng viên OCR chưa khớp mặt chữ (có thể gồm lỗi OCR, dạng chia, từ lặp, tiêu đề).
- `data/LATEST_COVERAGE.json`: thống kê từ cơ sở dữ liệu SQLite hiện tại, có thể tạo lại sau khi nhập thêm.
- Trong bộ ban đầu v7 có 10.056 **lượt ứng viên OCR** chưa khớp trên tất cả trang (không phải 10.056 từ thiếu), và 3 trang có OCR rỗng. Chưa trang nào được xác nhận đã rà thủ công **đầy đủ tất cả mục**.

### Bổ sung tự động có kiểm soát trên Mac

Ở **Dữ liệu & sao lưu**, có nút **Bổ sung cả hai nguồn**. Cần Internet lần đầu và có thể mất thời gian tùy đường truyền:

1. Nguồn tham khảo cộng đồng Soumatome: https://www.nguphaptiengnhat.net/tu-vung-tieng-nhat-n3.html (35 phần). Phải tải đủ 35 và ít nhất 900 mục không trùng; các dòng kana/ý nghĩa sai bị loại. Với cách đọc còn kanji, chỉ khôi phục khi có cặp từ-cách đọc đã biết rõ.
2. Nguồn từ điển Nhật–Việt Yomichan: https://github.com/dreamofi/yomichan-Vietnamese-dictionary (dung lượng khoảng 14 MB). Tra các ứng viên từ sách, chỉ thêm khi có chữ viết, cách đọc và nghĩa. Nhiều nghĩa/đọc không rõ có thể bị bỏ lại để tránh học sai.
3. Kết quả ghi vào `progress.sqlite3`, lưu các thẻ mới và giữ nguyên tiến trình thẻ cũ. Sau khi nhập, bấm **Tạo bảng kiểm kê 469 trang** để cập nhật CSV. Bấm **Sao lưu tiến trình** để lưu tất cả các thẻ mới.

**Không được hiểu import đủ 35 phần từ cộng đồng là đã hoàn tất cả 4 sách:** nguồn này có thể thiếu từ trong bài đọc, bài tập và ví dụ. Dữ liệu tự động vẫn cần đối chiếu từ thực tế PDF gốc.

### Cách dùng

Giải nén, mở `jlpt-local` trong VSCode rồi chạy `python3 server.py` hoặc mở `start.command` trên Mac. Trình duyệt: http://localhost:8765. Để giữ tiến trình v6, **sao lưu v6**, sau đó sao chép `progress.sqlite3` từ v6 sang thư mục v7 trước khi khởi chạy.

Không cần deploy, không tốn phí API khi học. Test: `python3 -m unittest -q tests.test_app tests.test_import_v6 test_v7` — 25 tests đạt. Kiểm tra endpoint đọc trang và tìm từ thành công; Chromium trong môi trường thử hiện bị chặn localhost nên không xác nhận kiểm thử giao diện trực tiếp.

### Vì sao chưa thể chứng nhận 100%?

Bốn bản PDF là scan hình, không có text trực tiếp để trích. OCR thường mất chữ trong chú thích/khung/hình, tách sai chữ động từ và sai furigana. Các trường hợp này phải **kiểm trực tiếp ảnh từng trang, so sánh với danh sách thẻ, và duyệt nghĩa tiếng Việt trong ngữ cảnh** trước khi chứng nhận độ phủ. Việc chỉ tăng số từ N3 chung không chứng minh đã lấy đủ từ ở các quyển được cung cấp.
