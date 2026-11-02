# Kiểm kê mức độ hoàn thành — Kotoba N3 v5

## Điều đã có thực sự

- 3.669 thẻ trong `data/cards.json`: **3.524** từ và cụm từ, **145** cấu trúc ngữ pháp.
- Có thể dùng ngay để làm quiz và viết đáp án; tiến trình SQLite được giữ nguyên khi mang DB từ v4 sang.
- Bổ sung so với v4: **544 từ/cụm** và **4 mẫu ngữ pháp** (tổng tăng **548** thẻ).
- **191 thẻ đã kiểm ảnh PDF**: 137 thẻ từ bộ gốc v1, 50 từ/cụm và 4 mẫu ngữ pháp trong v5.
- Các thẻ còn lại được biên soạn hoặc đối chiếu OCR, chưa được đối chiếu 100% với ảnh PDF.

## Điều chưa được phép coi là hoàn thành

- Bộ scan có **469 trang PDF**. Chỉ **18 trang** có ít nhất một mục được xác nhận qua ảnh, **451 trang** chưa có xác nhận thủ công trong dữ liệu. Đây không phải số trang hoàn toàn thiếu từ; nhiều trang có dữ liệu OCR hoặc trang giới thiệu.
- Các mục OCR chưa khớp vẫn có lỗi nhận dạng, từ rời và những từ đã được học ở biến thể khác. `data/ocr_unresolved_by_page_v5.csv` là **hàng đợi kiểm tra**, KHÔNG phải danh sách từ phải học hoặc số từ chắc chắn còn thiếu.
- Chưa xác minh từng mục từ/cụm/mẫu ngữ pháp, đáp án và bài đọc của cả 4 sách; chưa thể chứng nhận độ bao phủ 100%.
- Chưa đối chiếu toàn bộ từ với các đề JLPT đã được kiểm chứng.

## Chứng cứ ở từng trang

- `data/page_coverage_v5.csv` thống kê số ứng viên OCR được khớp chính xác, số mục chưa khớp và số thẻ kiểm tra bằng ảnh cho mỗi trang PDF.
- `data/verified_missing_v5.tsv`: 50 từ/cụm xác nhận bằng ảnh; gồm những mục thiếu ở trang 42, 55, 87 Từ vựng, 69 Kanji, 35 Đọc hiểu.
- `data/verified_grammar_v5.tsv`: 4 mẫu thể bị động ở Ngữ pháp trang 14.
- `data/ocr_reviewed_v5.tsv`: mục được chọn để học với cách đọc/nghĩa biên soạn nhưng nguồn vẫn được đánh dấu chưa xác minh bằng ảnh.

## Nguyên tắc tiếp tục

Để hoàn tất thực sự cần xử lý từng trang: đối chiếu ảnh → trích đúng mục từ/cụm (kể cả ví dụ và đáp án theo phạm vi đã chọn) → xác nhận kana/nghĩa/ngữ cảnh → gộp trùng kèm mọi nguồn trang → kiểm kê trang nào còn mục chưa xử lý. Không sinh thẻ có đáp án đoán từ OCR.

*Kiểm kê v5, 29/10/2026.*
