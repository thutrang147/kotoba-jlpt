# Kotoba N3 — web học trên Mac, lưu tiến trình bằng SQLite

**Phiên bản v9 · mở rộng và kiểm kê nội dung sách, 01/11/2026.** Một app web cá nhân, chạy hoàn toàn trên máy Mac. Không phải deploy, không tài khoản, không API AI, không cần npm hoặc cài thư viện Python bên ngoài.

## Mới ở bản v9 — đọc trước

- Tổng **4.254 thẻ từ/cụm từ + 145 thẻ ngữ pháp = 4.399 thẻ**. Thêm **446 thẻ** so với v8.
- Tất cả 446 thẻ mới có cách đọc kana, nghĩa tiếng Việt, và vị trí mặt chữ OCR trong ít nhất một trong bốn sách. **Chưa xác nhận đầy đủ 469 trang**; xem `KIEM_KE_V9.md`.
- 3.953 thẻ cũ được giữ nguyên nội dung, ID; không reset lịch học. Chép DB `progress.sqlite3` của bản v8 vào thư mục này trước khi mở.
- File `data/v9_ocr_matched_added.csv` chứa danh sách thẻ mới, `data/v9_page_ocr_inventory.csv` chứa thống kê trang (mang tính OCR, không chứng nhận trang đầy đủ).
- Phần lịch sử v6-v8 ở dưới chỉ là mô tả bản cũ, không phản ánh số thẻ v9.

## 1. Mở app (2 bước)

1. Giải nén, mở thư mục **`jlpt-local`** bằng VSCode.
2. Mở Terminal ở thư mục đó, chạy:

   ```bash
   python3 server.py
   ```

Trình duyệt mở **http://localhost:8765**. Nếu không tự mở thì tự gõ địa chỉ. Giữ cửa sổ Terminal chạy khi đang học. Dừng bằng `Ctrl + C`. Lần sau chạy lại cùng lệnh là học tiếp.

**Cách khác:** mở Terminal và kéo `start.command` vào cửa sổ rồi Enter. Hoặc `cd` vào thư mục và `bash start.command` (tự chuyển về thư mục đúng). Cần Python 3.9+ trên Mac. Nếu cổng đã bận: `python3 server.py --port 8766`.

## 2. Cách học đã thiết kế

- **Tự trộn từ vựng, kanji và các mẫu ngữ pháp** trong một luồng; không cần chọn loại bài, chế độ hoặc phạm vi.
- Mỗi lượt học hiện tự chọn **10 thẻ** từ toàn bộ kho, ưu tiên thẻ đến hạn và thẻ từng trả lời sai. Không cần cấu hình trước; chọn `Học ngay — 10 thẻ →` để bắt đầu, hoặc `Tiếp tục học` nếu còn lượt đang dở.
- **Từ có kanji**: hai kỹ năng độc lập, ví dụ `台所 → だいどころ` và `台所 → nhà bếp`. Từ chỉ có kana thì không hỏi lại cách đọc hiện sẵn.
- Ở giai đoạn trắc nghiệm, từ có kanji luôn đi theo cặp liền nhau: chọn cách đọc hiragana trước rồi chọn nghĩa tiếng Việt. Đáp án kana được sinh động từ các lỗi dễ nhầm và đáp án nghĩa ưu tiên cùng chủ đề; thứ tự lựa chọn được xáo trộn mỗi lượt.
- **Ngữ pháp**: `Vる＋つもりだ → định làm gì`, và chiều ngược lại `định làm gì → chọn cấu trúc`.
- **Một kỹ năng:** đầu tiên 3 lần trắc nghiệm đúng *trong các buổi đến hạn khác ngày*, sau đó 3 lần tự viết đúng trong các buổi đến hạn; sai sẽ đặt lại chuỗi đúng của giai đoạn hiện tại. Câu sai quay lại sau vài câu trong cùng buổi để ôn lại, nhưng trả lời ngay sau khi xem đáp án **không** giúp tăng mốc trí nhớ.
- **Cách đánh dấu thuộc:** khi *tất cả kỹ năng* của một thẻ đạt mốc viết, app đề xuất `Đánh dấu đã thuộc` để dừng lên lịch từ đó. Có thể đánh dấu từ phần Kho thẻ hoặc chọn tiếp tục ôn. Tại Kho thẻ có nút **Học lại từ này**.
- **Hẹn ôn cách quãng:** trong giai đoạn trắc nghiệm cách 1/2 ngày, giai đoạn viết cách 1/3 ngày, sau khi viết đạt mốc vẫn có thể tự ôn; nếu chưa đánh dấu thuộc, hẹn sau 30 ngày.
- Gõ cách đọc bằng bộ gõ tiếng Nhật (hiragana hoặc katakana được chấp nhận). App không tự chuyển romaji thành kana. Với nghĩa tiếng Việt app chấm **cố định** theo `meaning` và `meaning_aliases`: có thể không hiểu một cách diễn đạt đúng nhưng không nằm trong danh sách.

## 3. Dữ liệu bản v6 (lịch sử; xem số v9 ở trên)

- **3.785** thẻ từ vựng/cụm từ, đều có **cách đọc kana và nghĩa tiếng Việt**.
- **145** thẻ ngữ pháp (cấu trúc + nghĩa), trộn cùng từ vựng.
- **3.930 thẻ** có thể học ngay; trùng cặp `(từ, cách đọc)` đã được loại bỏ.
- **191** thẻ đã được kiểm tra qua hình ảnh từng trang (137 gốc + 50 từ/cụm + 4 ngữ pháp); các thẻ còn lại được **biên soạn** bằng cách đối chiếu kết quả OCR với kiến thức N3, có mức xác minh ghi riêng. **Không khẳng định đã lấy được chính xác 100% mục của 469 trang sách** vì bản scan OCR thiếu và sai khá nhiều.
- **469** trang của 4 sách đã có bản OCR và có sẵn bản PDF gốc trong bản ZIP; **7.210** ứng viên từ được giữ ở `data/vocabulary_candidates.json` nhưng những mục chưa có nghĩa/đọc đáng tin **không** đưa vào quiz.
- Các thẻ mở rộng có `source_refs` nếu OCR tìm được từ đó trong sách (dữ liệu nguồn chỉ là gợi ý, chưa phải kiểm tra đối chiếu từng dòng). Nhãn `Trọng tâm` dựa trên việc tìm thấy trong sách Từ vựng/Kanji; `Bổ sung` gồm từ tìm thấy ở sách còn lại và từ N3 mở rộng.
- Chưa có phân tích chính thức tần suất từng năm JLPT (không thể xác thực đề thật công bố đầy đủ theo từng kỳ).

**Độ phủ chưa được xác nhận đủ:** chỉ 18/469 trang PDF có ít nhất một thẻ được xác nhận từ ảnh, và **451 trang chưa được rà đầy đủ**. Điều này KHÔNG phải 451 trang thiếu thẻ: có trang mục lục, trang giải thích, trang đã có từ nhưng chưa được kiểm. Các file `page_coverage_v5.csv` và `ocr_unresolved_by_page_v5.csv` lưu chi tiết để xử lý tiếp; số mục OCR không khớp KHÔNG đồng nghĩa số từ thiếu.

**Nguồn dữ liệu:** 4 bản scan Soumatome do người dùng cung cấp, file OCR đã được tạo từ bộ này, và bộ từ JLPT N3 biên soạn bổ sung. Không dùng API AI hoặc dịch tự động trong khi học. Có thể xem và sửa TSV gốc nếu phát hiện sai.

**Chú ý:** nếu mở câu hỏi tự viết nghĩa Việt, bạn có thể nhập riêng một phần nghĩa phân cách bằng dấu `;`; hệ thống lưu chúng ở `meaning_aliases`. Các cách diễn đạt khác nhưng cùng nghĩa có thể cần thêm alias thủ công.

## 4. Tiến trình và việc cập nhật

Sau mỗi câu trả lời, server ghi vào **`progress.sqlite3`** ở thư mục `jlpt-local`. Đóng Chrome, restart Mac hay xóa cache trình duyệt không làm mất tiến trình đã ghi vào DB. Một buổi học *đang dở* được lưu thêm vào `localStorage` (nếu xóa cache thì mất hàng câu chưa học của buổi, **không** mất tiến trình các câu đã trả lời).

Vào **Dữ liệu & sao lưu → Tải bản sao lưu** mỗi tuần. Backup JSON gồm thẻ, tiến trình và câu trả lời. Có thể phục hồi từ backup v1; hệ thống tự thêm thẻ mới của phiên bản v6 mà không xóa tiến trình cũ. Việc nhập lại thẻ trùng ID sẽ cập nhật nội dung, **giữ tiến trình các kỹ năng không đổi đáp án**, chỉ xóa tiến trình kỹ năng có đáp án đổi.

Để **nâng từ các bản cũ lên v6 và giữ tiến trình**: giữ nguyên file `progress.sqlite3` cũ, sao lưu nó, sau đó chép vào **thư mục `jlpt-local` mới** trước khi chạy lệnh. Không đặt hai app cùng cổng 8765. Bản ZIP này **không chứa DB tiến trình** của người dùng.

## 5. File dữ liệu cho những lần bổ sung sau

- `data/cards.json`: bộ thẻ dùng thực tế, có ID ổn định.
- `data/cards_initial_137.json`: bản gốc 137 thẻ để không làm mất ID.
- `data/curated_additions.tsv`: từ mới biên soạn (cách viết, kana, nghĩa Việt).
- `data/vocab_full_additions.tsv`: **danh sách từ/cụm từ bổ sung**, có kanji/kana/tiếng Việt, được loại trùng với thẻ hiện có khi sinh bộ học.
- `data/curated_grammar.tsv`: mẫu ngữ pháp bổ sung.
- `build_cards.py`: ghép các bộ từ vựng TSV và ngữ pháp với thẻ gốc, gắn trang OCR nếu gặp, sau đó sinh lại `data/cards.json` (một lần chạy bằng `python3 scripts/build_cards.py`). **Không chạy khi đang sửa file cards.json thủ công** vì nó sẽ ghi đè những sửa đổi đó.
- `data/vocabulary_candidates.json`: để hỗ trợ công đoạn đối chiếu sau này, không phải bộ thẻ đã duyệt.

- `data/verified_missing_v5.tsv`: 50 mục/cụm tìm thấy qua kiểm tra hình ảnh trang PDF (bao gồm trang Kanji PDF 69 đã bị OCR bỏ trống).
- `data/verified_grammar_v5.tsv`: 4 mẫu ngữ pháp thể bị động ở sách Ngữ pháp trang 14 (trang bị OCR rỗng).
- `data/ocr_reviewed_v5.tsv`: danh sách từ/cụm bổ sung có cách đọc và nghĩa Việt đã được chọn lọc từ gợi ý OCR; **vị trí OCR chưa được kiểm tra bằng mắt toàn bộ**.
- `audit_pages_v5.py`: tạo lại hai bảng kiểm kê theo từng trang từ OCR, không coi đó là chứng nhận đã đủ từ. Chạy: `python3 scripts/audit_pages_v5.py`.
- Nếu nâng cấp từ v4: **sao lưu rồi sao chép `progress.sqlite3` sang thư mục `jlpt-local` v6 trước khi chạy**; thẻ mới được thêm tự động, thẻ cũ và lịch sử ôn giữ nguyên.

## 6. Kiểm thử

```bash
python3 -m unittest -v tests.test_app
```

20 bài kiểm thử dữ liệu và nguồn nhập: hẹn ôn, lên dạng viết, tách cách đọc/nghĩa, sai đặt lại chuỗi, chống ghi trùng, lưu/khôi phục, nhập cập nhật thẻ, chặn đánh dấu thuộc sớm. Đã kiểm tra luồng giao diện bằng Chromium trong môi trường thử nghiệm (mock API) và chạy thử API local. **Chưa kiểm tra trực tiếp trên Mac người dùng.**

## 7. Giới hạn cần biết

Không có AI chấm câu trả lời, không đồng bộ điện thoại. Lúc học thường ngày hoàn toàn offline. Nút mở rộng từ điển cần kết nối Internet khi dùng lần đầu. “Không bao giờ quên” không phải mục tiêu có thể chứng minh; đánh dấu thuộc chỉ có nghĩa vượt ngưỡng do app quy định. Chất lượng nghĩa và từ đồng nghĩa nên được rà soát thêm qua các buổi học. Chưa hoàn thành đối chiếu toàn bộ 469 trang và chưa tổng hợp từng kỳ JLPT N3.

## 8. Bổ sung từ còn thiếu theo OCR bằng từ điển Nhật–Việt

Trong **Dữ liệu & sao lưu**, bấm **Đối chiếu và bổ sung từ sách** khi Mac có mạng. App tải một lần file từ điển Nhật–Việt Yomichan (~14 MB) về `data/jmdict_vietnamese.zip`, rồi:

1. Lấy các **mặt chữ** mà OCR phát hiện trong 469 trang; tra từ điển xem đó có thực sự là mục từ hay không.
2. Lấy **cách đọc** kana và **nghĩa tiếng Việt** từ từ điển. Khi có nhiều cách đọc Kanji mà nguồn OCR không đủ phân biệt thì bỏ qua thay vì đoán.
3. Gộp trùng với thẻ sẵn có, chỉ thêm phần còn thiếu vào SQLite và **giữ nguyên tiến trình**. Số lượng thêm thực tế phụ thuộc bản từ điển và dữ liệu OCR; xem thông báo sau khi chạy, không có số lượng bảo đảm.
4. Các từ khớp tự động có nhãn `verified: false` và tên nguồn; chưa được xác minh từng ví dụ hoặc trang thủ công. Có thể nhấn lại khi đã có file từ điển trong máy, kể cả khi mất mạng.

**Lưu ý quan trọng:** Đây là bước *mở rộng tự động*, không phải chứng nhận đã đủ 100% mọi từ của cả bốn quyển. Dữ liệu OCR thường chứa tiêu đề, câu ví dụ, từ sai do scan; báo cáo `docs/COVERAGE_REPORT.md` và `data/coverage_audit.json` cho phép kiểm tra những mục chưa khớp. Không nên đưa tất cả mục OCR vào câu hỏi khi chưa xác minh nghĩa.

Nguồn tải thêm theo lựa chọn của người dùng: [yomichan-Vietnamese-dictionary](https://github.com/dreamofi/yomichan-Vietnamese-dictionary) (dữ liệu từ điển tổng hợp; cần đối chiếu nghĩa khi gặp nhiều nghĩa). Không kèm từ điển nguồn trong file ZIP này và không chuyển dữ liệu cá nhân lên Internet. Bộ đề JLPT sau cải cách 2010 không có danh sách từ vựng chính thức; thống kê đề thi từng năm chưa xác minh.

Để dùng file từ điển đã tải thủ công thay vì tải qua app: đặt tên file là `data/jmdict_vietnamese.zip`. Lần đầu cập nhật có thể cần vài chục giây tùy tốc độ mạng; đừng đóng cửa sổ Terminal trước khi có phản hồi.

## 9. Bản v6 và việc đối chiếu theo 35 bài Soumatome

**Có thêm 261 mục từ/cụm** so với v5; không làm mất 3.669 thẻ cũ. Bản v6 kèm cả bốn sách PDF để mở đúng trang từ thẻ. Dữ liệu nguồn và các lỗi chưa hoàn tất được ghi tại `KIEM_KE_V6.md`.

Từ màn **Học hôm nay**, bấm **Bổ sung danh sách 35 bài Soumatome**, sau đó ở màn **Dữ liệu & sao lưu** bấm **Đối chiếu danh sách Soumatome**. Lúc này cần kết nối internet. App đọc nguồn cộng đồng `nguphaptiengnhat.net` (không phải toàn bộ từ trong PDF), kiểm đủ 35 phần và tối thiểu 900 cặp chữ–kana trước khi nhập thêm; nếu website lỗi mà trước đó có cache đầy đủ thì có thể dùng cache. Kết quả thực tế sẽ hiện số đã có và số thẻ được thêm. **Không có số lượng thêm được bảo đảm**, và không được hiểu nút này giúp sách đạt 100% độ phủ.

Cập nhật từ v5: sao lưu `progress.sqlite3`, chép vào thư mục `jlpt-local` v6 trước khi chạy `python3 server.py`.

## v7: kiểm kê và nhập nguồn một lần

Bản v7 **chưa chứng nhận đủ từ trong 469 trang**. Đọc `KIEM_KE_V7.md` để xem giới hạn. Có thêm nút **Bổ sung cả hai nguồn** (35 phần Soumatome và từ điển Nhật–Việt, cần internet), **Kiểm kê 469 trang**, tìm chữ OCR mở PDF gốc. Báo cáo trang: `data/book_page_audit.csv`, `data/ocr_not_in_deck.csv`. Những mục OCR không đủ cách đọc/nghĩa không được đưa vào bài học.
