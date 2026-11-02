"""OCR-candidate coverage check, NOT an audited textbook word count."""
import json,collections, pathlib
P=pathlib.Path(__file__).resolve().parents[1]/'data'
words=json.loads((P/'cards.json').read_text(encoding='utf8'))
candidates=json.loads((P/'vocabulary_candidates.json').read_text(encoding='utf8'))
active={c['term'] for c in words if c['kind']=='vocab'}
books=['Từ vựng','Kanji','Ngữ pháp','Đọc hiểu']
summary={};pages={};missing={}
for book in books:
    entries=[x for x in candidates if any(loc['book']==book for loc in x['sources'])]
    unique={x['term'] for x in entries}; covered=unique&active
    summary[book]={'ocr_candidates_unique':len(unique),'exact_surface_in_cards':len(covered),
                   'unmatched_ocr_candidates':len(unique-covered),
                   'ocr_surface_match_rate':round(100*len(covered)/len(unique),1)}
    pp=collections.defaultdict(lambda:{'all':set(),'matched':set()})
    for x in entries:
        for loc in x['sources']:
            if loc['book']==book:
                p=pp[loc['pdf_page']];p['all'].add(x['term'])
                if x['term'] in active:p['matched'].add(x['term'])
    pages[book]=[{'pdf_page':k,'ocr_candidate_count':len(v['all']),
                  'exact_surface_in_cards':len(v['matched'])} for k,v in sorted(pp.items())]
    missing[book]=sorted(unique-covered)
out={'warning':'Đây KHÔNG phải số mục từ vựng có trong sách. OCR có nhiều từ sai, hình thái chia động từ, từ của đề bài/đáp án và tiêu đề; chỉ dùng để truy dấu khả năng thiếu.',
     'books':summary,'pages':pages,'missing_ocr_terms':missing}
(P/'coverage_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
text=['# Báo cáo độ phủ OCR (đối chiếu bề mặt chữ)', '',
'**Không được coi là chứng nhận đã trích đủ từ sách.** Các mục OCR bao gồm chữ nhiễu, hình thái động từ, từ trong đề bài, ví dụ và cả tiêu đề.', '',
'| Sách | Mục OCR riêng biệt | Mục khớp mặt chữ với thẻ | Chưa khớp |', '|---|---:|---:|---:|']
for b,v in summary.items():text.append(f"| {b} | {v['ocr_candidates_unique']} | {v['exact_surface_in_cards']} | {v['unmatched_ocr_candidates']} |")
text+=['','Xem `data/coverage_audit.json` để tra từng trang PDF. Không nhập thẳng phần chưa khớp vào quiz vì chưa có đáp án nghĩa/cách đọc đã kiểm chứng.']
(P.parent/'docs'/'COVERAGE_REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf8')
print('\n'.join(text[:9]))
