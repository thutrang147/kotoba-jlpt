"""Inspect OCR evidence versus cards in the *actual* SQLite collection.

A match means that an OCR candidate shares the Japanese written form with a
card; it never means a page's vocabulary was exhaustively transcribed.
"""
from pathlib import Path
from collections import defaultdict
import csv, json, re

ROOT=Path(__file__).resolve().parent
P=ROOT/'data'
BOOKS=('Ngữ pháp','Kanji','Đọc hiểu','Từ vựng')
BOOK_KEY={'nguphap':'Ngữ pháp','kanji':'Kanji','dochien':'Đọc hiểu','tuvung':'Từ vựng'}


def coverage(cards, export=False):
    pages=json.loads((P/'source_pages.json').read_text(encoding='utf-8'))
    candidates=json.loads((P/'vocabulary_candidates.json').read_text(encoding='utf-8'))
    bypage=defaultdict(set)
    for x in candidates:
        for s in x.get('sources',[]):
            bypage[s['book'],int(s['pdf_page'])].add(x['term'])
    terms={x['term'] for x in cards if x.get('kind')=='vocab'}
    refs=defaultdict(set)
    for x in cards:
        for r in x.get('source_refs',[]):
            if r.get('book') in BOOKS and r.get('pdf_page'):
                refs[r['book'],int(r['pdf_page'])].add(x['term'])
        # Old manually checked cards may include their PDF page only as a string
        if x.get('verified'):
            m=re.search(r'PDF\s+(\d+)',x.get('source',''))
            book=next((b for b in BOOKS if b in x.get('source','')),None)
            if m and book:refs[book,int(m.group(1))].add(x['term'])
    rows=[];unresolved=[]
    for x in pages:
        key=(x['book'],int(x['pdf_page']))
        items=bypage[key]
        match=items & terms
        missing=items - terms
        # This flag means "reviewed and exhaustive", not just has known words.
        rows.append({'book':key[0],'pdf_page':key[1],
           'ocr_chars':len(x.get('text','')),'ocr_candidates':len(items),
           'ocr_candidates_in_deck':len(match),'ocr_candidates_not_in_deck':len(missing),
           'cards_with_page_ref':len(refs[key]),
           'exhaustively_verified':False,
           'status':'not_exhaustively_verified'})
        for term in sorted(missing):
            unresolved.append({'book':key[0],'pdf_page':key[1],
                               'ocr_term_unchecked':term,
                               'status':'candidate only; transcription/meaning unverified'})
    summary={'source_pages':len(rows),'full_page_reviews':0,
        'pages_with_empty_ocr':sum(r['ocr_chars']==0 for r in rows),
        'ocr_candidate_occurrences':sum(r['ocr_candidates'] for r in rows),
        'candidate_occurrences_not_in_deck':len(unresolved),
        'by_book':{},'disclaimer':'OCR candidate matches are NOT textbook completeness rates.'}
    for book in BOOKS:
        group=[x for x in rows if x['book']==book]
        summary['by_book'][book]={'pages':len(group),'ocr_empty':sum(x['ocr_chars']==0 for x in group),
            'candidate_occurrences_not_in_deck':sum(x['ocr_candidates_not_in_deck'] for x in group)}
    if export:
        for name,data in [('book_page_audit.csv',rows),('ocr_not_in_deck.csv',unresolved)]:
            with (P/name).open('w',encoding='utf-8-sig',newline='') as f:
                wr=csv.DictWriter(f,fieldnames=data[0].keys());wr.writeheader();wr.writerows(data)
        (P/'LATEST_COVERAGE.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return summary,rows


def get_page(book_id,page):
    book=BOOK_KEY.get(book_id)
    if not book or not isinstance(page,int) or page<1 or page>150:
        raise ValueError('Trang hoặc tên sách không hợp lệ')
    pages=json.loads((P/'source_pages.json').read_text(encoding='utf-8'))
    x=next((p for p in pages if p['book']==book and int(p['pdf_page'])==page),None)
    if x is None:raise ValueError('Không có trang PDF này')
    return {'book':book,'pdf_page':page,'ocr_text':x.get('text',''),
        'disclaimer':'Văn bản OCR có thể sai; bản PDF gốc mới là nguồn đối chiếu.'}

if __name__=='__main__':
    import sqlite3
    db=ROOT/'progress.sqlite3'; conn=sqlite3.connect(db)
    cards=[json.loads(t) for (t,) in conn.execute('SELECT body FROM cards')]
    summary,_=coverage(cards,True)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

def search_book_ocr(query,limit=40):
    """Search OCR evidence (not a verified Japanese dictionary entry)."""
    query=query.strip()
    if not 1<=len(query)<=50:raise ValueError('Nhập từ khóa 1–50 ký tự')
    pages=json.loads((P/'source_pages.json').read_text(encoding='utf-8'))
    hits=[]
    for p in pages:
        text=p.get('text','')
        i=text.casefold().find(query.casefold())
        if i<0:continue
        hits.append({'book':p['book'],'pdf_page':p['pdf_page'],
                     'preview':text[max(0,i-50):i+max(70,len(query)+40)].replace('\n',' ')})
        if len(hits)>=limit:break
    return {'query':query,'results':hits,'warning':'Chỉ tìm chuỗi OCR, có thể bỏ sót hoặc nhận sai.'}
