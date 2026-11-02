# Kiểm kê Kotoba v9 — dùng kèm app và 4 PDF gốc

## Đã bổ sung thực tế

- v8: 3.808 từ/cụm từ, 145 thẻ ngữ pháp = **3.953 thẻ**.
- v9: **4.254 từ/cụm từ**, **145 thẻ ngữ pháp** = **4.399 thẻ**.
- **446 thẻ mới**, mỗi thẻ có mặt chữ, cách đọc kana, nghĩa Việt được biên soạn, và ít nhất một vị trí mặt chữ khớp OCR trong trang học của bốn PDF.
- **3.953 thẻ cũ giữ nguyên byte-nội dung logic (ID, nghĩa, cách đọc, nguồn)**, đã xác nhận bằng SHA-256.
- 129 mục trong danh sách biên soạn chưa khớp mặt chữ OCR trên trang học được giữ ở bảng riêng, KHÔNG nhập làm thẻ.
- 191 thẻ từ các phiên bản trước có cờ kiểm tra trực tiếp ảnh. **446 thẻ v9 mới là đối chiếu OCR, không đánh dấu đã kiểm tra ảnh.**

## Thẻ mới khớp theo từng sách

| Sách | Số thẻ mới có tham chiếu OCR trong sách | Mục OCR ứng viên chưa khớp tên thẻ sau cập nhật |
|---|---:|---:|
| Từ vựng | 208 | 1170 |
| Kanji | 132 | 1390 |
| Ngữ pháp | 119 | 968 |
| Đọc hiểu | 243 | 1464 |

*Một thẻ có thể xuất hiện trong nhiều sách, nên không cộng số ở cột tham chiếu thành 446.*

## Những việc vẫn chưa chứng nhận được

- Chưa có trang PDF nào được rà soát hoàn chỉnh từng mục qua ảnh sách; do đó **KHÔNG được khẳng định đã đủ 100% từ/cụm của 469 trang**.
- OCR còn nhiều lỗi tách động từ, từ ví dụ, tiêu đề, tên người, dạng chia. Từ chưa khớp OCR không đồng nghĩa với từ thiếu thật.
- Các thẻ có cùng nghĩa có thể vẫn cần thêm đáp án đồng nghĩa khi tự viết tiếng Việt.
- Danh sách thống kê từ xuất hiện trong các đề JLPT thật từng năm chưa được xác minh.

## File kiểm toán và phục hồi

- `data/v9_ocr_matched_added.csv`: 446 thẻ mới có chữ đọc nghĩa, vị trí OCR, ID và trạng thái xác minh.
- `data/v9_not_added_without_ocr.csv`: 129 mục không khớp OCR, giữ riêng, không đưa vào câu hỏi.
- `data/v9_page_ocr_inventory.csv`: bảng 469 trang, giúp thấy trang chưa đối chiếu đủ.
- `docs/COVERAGE_REPORT.md` và `data/coverage_audit.json`: thống kê OCR cập nhật.
- `data/v8_baseline_hashes.json`: mã băm 3.953 thẻ cũ để kiểm tra không thay đổi.
- File SQLite cũ vẫn dùng được, chỉ cần sao lưu và chép `progress.sqlite3` vào thư mục bản mới trước khi chạy.

## Kiểm thử

Chạy `python3 -m unittest discover -s tests -t . -p "test*.py" -v` từ thư mục `jlpt-local`. 29 bài kiểm thử đã đạt trong môi trường xây dựng, bao gồm kiểm tra tham chiếu OCR 446 thẻ và bảo toàn nội dung 3.953 thẻ cũ.

## Quy tắc dữ liệu v9

Thẻ mới chỉ được tạo từ danh sách do người biên soạn đọc/nghĩa và có mặt chữ khớp trực tiếp với văn bản OCR trang học. Không dùng readings tự động bị cắt đuôi động từ hoặc dịch đoán từ OCR thô. Tuy vậy, OCR có thể khớp từ trong ví dụ nên không chứng minh đó là từ trọng tâm hay đáp án chuẩn sách.
