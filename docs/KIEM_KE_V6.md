# Kiểm kê dữ liệu — Kotoba JLPT N3 v6 (29/10/2026)

## Dữ liệu đã thực sự được đóng trong app

- **3,930 thẻ:** 3,785 từ/cụm từ + 145 cấu trúc ngữ pháp.
- **261 từ/cụm mới** so với v5, cách viết–cách đọc–nghĩa đã được biên soạn. **Không** đánh dấu “kiểm ảnh” nếu chỉ khớp OCR.
- **191 thẻ** có nhãn đã xác minh qua ảnh PDF từ các bước trước; 3,739 thẻ chưa có xác nhận như vậy.
- Có **2,156 thẻ có ít nhất một tham chiếu tới vị trí OCR trong sách. Vị trí OCR KHÔNG có nghĩa là từng dòng đã được đối chiếu thủ công.
- Đóng kèm **toàn bộ bốn bản PDF scan nguồn**: 121 trang Từ vựng, 119 trang Kanji, 115 trang Ngữ pháp, 114 trang Đọc hiểu; tổng 469 trang. Mở từ phần “Dữ liệu & sao lưu” hoặc mục nguồn thẻ.
- Dữ liệu 137 thẻ gốc và toàn bộ 3,669 ID thẻ của v5 **được giữ nguyên**; chuyển file `progress.sqlite3` từ bản cũ sẽ không đặt lại tiến trình.

## So khớp văn bản OCR với mặt chữ thẻ (KHÔNG phải tỷ lệ hoàn thành sách)

| Sách | Số trang PDF | Ứng viên OCR có từ trùng mặt chữ | Ứng viên OCR chưa trùng |
|---|---:|---:|---:|
| Từ vựng | 121 | 4,304 | 2,290 |
| Kanji | 119 | 3,360 | 2,472 |
| Ngữ pháp | 115 | 3,520 | 2,267 |
| Đọc hiểu | 114 | 3,836 | 3,027 |

Các cột OCR gồm nhiều dạng từ bị chia, tiêu đề, đáp án câu hỏi, mảnh câu, lỗi scan, từ trùng nhưng khác dạng biến đổi; không được hiểu “chưa trùng” là từng ấy từ thiếu thực tế. Ngược lại, OCR có thể bỏ sót toàn bộ từ trên một trang.

## Nguồn cộng đồng 35 phần Soumatome N3 (tùy chọn)

Vào **Dữ liệu & sao lưu → Đối chiếu danh sách Soumatome**, hoặc từ nút nhắc trên trang chính, khi Mac có mạng. App đọc danh sách có cách viết, kana, nghĩa Việt từ [nguphaptiengnhat.net](https://www.nguphaptiengnhat.net/tu-vung-tieng-nhat-n3.html). App:

1. Đọc các trang `part1`–`part35`, kiểm từng phần phải có ít nhất 15 mục hợp lệ và toàn nguồn có ít nhất **900 mục khác nhau** trước khi thêm thẻ; nếu thiếu 1 phần sẽ **không nhập bộ thiếu**.
2. Bỏ những mục không có kana hoặc nghĩa rõ ràng, không tự đoán đáp án từ OCR lỗi; gộp trùng cặp chữ–kana.
3. Thêm thẻ chưa có vào SQLite và giữ nguyên tiến trình cũ. Kết quả sẽ ghi rõ số từ đã có và số thẻ mới. Có thể chạy lại từ bản cache đầy đủ nếu mất mạng.
4. Đây là nguồn **cộng đồng**, có thể có lỗi dịch; không đánh dấu các mục này “kiểm trực tiếp PDF”.

**Không có số lượng tăng thêm được bảo đảm.** Trong môi trường xây dựng không truy cập trực tiếp toàn bộ HTML để xác nhận số từ của 35 trang nên bản ZIP chưa bao gồm từ của nguồn này; nó có công cụ để tải trên Mac. Khi học bình thường thì hoàn toàn offline.

## Điều chưa hoàn tất — quan trọng cho kế hoạch ôn thi

**Chưa thể chứng nhận đã lấy 100% từ vựng, cụm từ, đáp án và ví dụ của tất cả 469 trang.** Còn cần mở từng trang PDF, ghi danh sách từng mục dạy và từng từ bổ sung, kiểm cách đọc và nghĩa theo ngữ cảnh, sau đó so khớp từng mục với ID thẻ để đạt độ phủ có thể kiểm toán. Đếm 3.930 thẻ hoặc tải danh sách N3 online không chứng minh sự đầy đủ của 4 quyển.

Không có bộ đề thật JLPT N3 từng năm đầy đủ được xác thực và đưa vào dữ liệu. Không ghi nhãn “hay ra thi” dựa trên suy đoán.

## Kiểm tra và kỹ thuật

- `data/cards.json`: bộ thẻ thực có. `data/book_lexical_review_v6.tsv`: 320 ứng viên đã biên soạn; **261** mục mới được thêm sau khi lọc trùng.
- `data/page_coverage_v5.csv`, `data/ocr_unresolved_by_page_v5.csv`: bảng kiểm kê từ OCR của 469 trang; tên file v5 là vì phương pháp lập nguồn gốc từ vòng trước.
- `source_books/*.pdf`: 4 bản scan nguồn để kiểm tra thủ công.
- `soumatome_parts_import.py`: nguồn 35 phần chỉ lấy khi có mạng; không ảnh hưởng học offline.
- `python3 -m unittest -q tests.test_app tests.test_import_v6` để chạy **20 bài kiểm thử**; chạy `python3 server.py` để mở web.
