# Nguồn và phương pháp — 29/10/2026

## Học tập
- Quizlet Learn: https://quizlet.com/features/learn
- Quizlet Write: https://help.quizlet.com/hc/en-au/articles/360030990531-Studying-with-Write-mode
- Spaced retrieval practice giúp luyện trí nhớ dài hạn, nhưng không có phương pháp bảo đảm không bao giờ quên. Mốc 3 trắc nghiệm + 3 lần viết là một **quy tắc của Kotoba**, không phải thuật toán của Quizlet.

## JLPT N3
- Câu hỏi và bộ đề chính thức: https://www.jlpt.jp/e/samples/sampleindex.html
- FAQ: https://www.jlpt.jp/e/faq/index.html
- N3 hỏi cách đọc kanji, chính tả, nghĩa trong ngữ cảnh, gần nghĩa, cách dùng. JLPT không công bố danh sách chính thức từ/kanji/ngữ pháp; không có toàn bộ đề của mỗi kỳ được công khai.

## Dữ liệu
- Bốn bản PDF do người dùng cung cấp: Soumatome N3 Từ vựng (121 trang), Kanji (119), Ngữ pháp (115), Đọc hiểu (114). Các nguồn là bản scan.
- Dữ liệu OCR trước đó dùng Tesseract tiếng Nhật và Sudachi để tạo 7.210 ứng viên, nhưng OCR có thể đảo thứ tự chữ, bẻ từ, thiếu âm đọc và mất dấu tiếng Việt. Do đó không dùng tự động cho câu hỏi.
- Phiên bản v2 thêm các mục do người biên soạn viết vào TSV, khi có thể thì gắn trích dẫn trang từ chỉ mục OCR hiện hữu. Các mục chưa có quy trình xác nhận bằng ảnh PDF được ghi `verified:false`.
- Không dùng kho đề thi tải lại không xác minh để ghi nhãn "đã xuất hiện ở kỳ X".

## Bổ sung v4 — từ điển Nhật–Việt đối chiếu OCR
- Kho thẻ v4 có 2.980 từ/cụm từ, 141 mẫu ngữ pháp, trong đó phần lớn **chưa** được duyệt thủ công theo trang.
- Công cụ `dictionary_enrichment.py` tải file từ điển Yomichan tiếng Việt từ https://github.com/dreamofi/yomichan-Vietnamese-dictionary (chỉ khi người dùng bấm cập nhật), lấy cách đọc và nghĩa tiếng Việt, rồi chỉ đưa vào thẻ những từ có trùng *mặt chữ* với ứng viên OCR.
- Bộ từ điển này có thể chứa nghĩa tiếng Anh trước, nghĩa tiếng Việt sau; script chỉ sử dụng mục nghĩa có dấu/đặc trưng tiếng Việt và bỏ qua mục không có nghĩa Việt.
- Trường hợp một từ có nhiều cách đọc sẽ cần tín hiệu hình thái từ OCR để chọn; nếu thiếu thì bỏ qua thay vì đoán.
- Báo cáo `data/coverage_audit.json` chỉ đánh giá bề mặt chữ OCR khớp thẻ, không phải độ phủ nội dung học sách chính xác. OCR khớp từ không bảo đảm ngữ cảnh hoặc cách đọc đúng.
- Nguồn tra từ điển được tải trên máy cá nhân, không kèm trong gói phần mềm. Nội dung từ điển và giấy phép tuân theo nguồn phát hành của tác giả.
