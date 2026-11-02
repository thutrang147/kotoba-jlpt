# Kiểm kê dữ liệu v10 — Official Workbook và Soumatome

Ngày kiểm kê: 01/11/2026

## Kết quả thay đổi thực tế

- Số thẻ trước cập nhật: **4.399**.
- Số thẻ sau cập nhật trong `data/cards.json`: **4.417**.
- Database runtime hiện tại trước seed có **5.240** thẻ; sau seed an toàn có **5.258** thẻ.
- Thẻ mới thêm: **18 từ vựng** từ danh sách kiểm tra workbook chính thức.
- Cặp `(term, reading)` trong báo cáo 64 mục sau cập nhật: **64/64**.
- Thẻ hiện có được gắn metadata workbook: **64**.
- Không sửa `term`, `reading` hoặc `meaning` của thẻ cũ; `ためる` và `くむ` cũ được giữ nguyên vì là đồng âm khác nghĩa.
- Không đổi ID hoặc xóa tiến trình SQLite.
- Khi seed database runtime: thêm 18 dòng `cards`, giữ nguyên **48** dòng `progress` và **85** dòng `events`.

## Phạm vi nguồn chính thức

Đã tải và đối chiếu báo cáo với hai URL workbook chính thức:

- [N3V.pdf 2012](https://www.jlpt.jp/samples/sample2012/pdf/N3V.pdf)
- [N3V.pdf 2018](https://www.jlpt.jp/samples/sample2018/pdf/N3V.pdf)

Năm 2012/2018 trong metadata là **năm phát hành workbook**, không phải năm một từ
được thi. Không có trường `exam_year_claim` nào được gán.

### 18 thẻ mới

| Năm workbook | Từ | Cách đọc | Nghĩa chuẩn hóa | Ghi chú dạng nguồn |
|---:|---|---|---|---|
| 2012 | 首都 | しゅと | thủ đô | mục từ |
| 2012 | 大量 | たいりょう | số lượng lớn | mục từ |
| 2012 | インタビュー | インタビュー | phỏng vấn | mục từ |
| 2012 | 主張 | しゅちょう | khẳng định; chủ trương | mục từ |
| 2012 | からから | からから | khô khốc; khô rang | mục từ |
| 2012 | 貯める | ためる | tiết kiệm; dành dụm | chuẩn hóa từ dạng ためて |
| 2012 | 訳 | わけ | lý do | chuẩn hóa từ dạng わけ |
| 2018 | 訓練 | くんれん | huấn luyện | mục từ |
| 2018 | 豆 | まめ | đậu; hạt đậu | mục từ |
| 2018 | 波 | なみ | sóng | đề dùng なみ, phương án có 波 |
| 2018 | 組む | くむ | khoanh; ghép; tổ chức | chuẩn hóa từ dạng くんで |
| 2018 | イメージ | イメージ | hình ảnh; ấn tượng | mục từ |
| 2018 | 囲む | かこむ | bao quanh | chuẩn hóa từ dạng 囲み |
| 2018 | 姿勢 | しせい | tư thế | mục từ |
| 2018 | 輝く | かがやく | tỏa sáng | chuẩn hóa từ dạng かがやいて |
| 2018 | 余る | あまる | dư; thừa | chuẩn hóa từ dạng あまりました |
| 2018 | 沸騰 | ふっとう | sôi | mục từ |
| 2018 | 慰める | なぐさめる | an ủi | mục từ |

Các thẻ mới có `source_type=official_workbook`, `source_year`, `source_page=null`,
`source_form`, `verification_status`, `exam_priority=high` và URL workbook. Trạng thái
giữ `verified=false` vì chưa có xác minh ảnh trang độc lập trong môi trường này.

## Soumatome và OCR

- Dữ liệu dự án có OCR của **469 trang** và các PDF gốc của 4 sách.
- Số trang đã kiểm tra trực tiếp bằng ảnh trong lần này: **0/469**.
- `full_page_reviews` vẫn là **0**; không tuyên bố bao phủ 100%.
- `LATEST_COVERAGE.json` ghi nhận **10.056 ứng viên OCR chưa có exact term trong deck**.
- Các ứng viên OCR chưa xác minh vẫn không được tự động biến thành thẻ.
- Không tự gán các mục workbook vào trang Soumatome khi không có bằng chứng trang.

## Kiểm thử dữ liệu

- Kiểm tra không trùng ID và không trùng cặp term–reading–meaning khi thêm 18 thẻ.
- Kiểm tra 2 đồng âm khác nghĩa: `貯める/ためる` và `組む/くむ` không ghi đè thẻ cũ.
- Bộ kiểm thử ứng dụng cần chạy sau khi khởi động lại server để `seed_cards` nhập 18 thẻ mới
  mà không thay đổi các dòng `progress` hiện có.

## Giới hạn còn lại

Chưa thể kết luận đủ toàn bộ từ trong 4 sách hoặc toàn bộ đề JLPT. Các mục chưa xác minh
ảnh, nghĩa theo ngữ cảnh hoặc trang cụ thể tiếp tục nằm ngoài bộ học cho đến khi được duyệt
thủ công.
