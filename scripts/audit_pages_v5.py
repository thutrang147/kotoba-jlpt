#!/usr/bin/env python3
"""Record inspectable *OCR text-match*, never claim this is verified book coverage.

Run from project: python3 scripts/audit_pages_v5.py
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,re
P=Path(__file__).resolve().parents[1]/'data'
books=('Ngữ pháp','Kanji','Đọc hiểu','Từ vựng')
source=json.loads((P/'source_pages.json').read_text(encoding='utf8'))
candidates=json.loads((P/'vocabulary_candidates.json').read_text(encoding='utf8'))
cards=json.loads((P/'cards.json').read_text(encoding='utf8'))
by_term=defaultdict(list)
by_page=defaultdict(list)
for x in candidates:
    for loc in x['sources']:
        by_page[(loc['book'],int(loc['pdf_page']))].append(x)
        by_term[x['term']].append((loc['book'],int(loc['pdf_page'])))

terms={c['term'] for c in cards if c['kind']=='vocab'}
verified_by_page=defaultdict(set)
for card in cards:
    if not card.get('verified'):continue
    for loc in card.get('source_refs',[]):
        verified_by_page[(loc['book'],int(loc['pdf_page']))].add(card['term'])
    # Pre-v5 manually reviewed cards recorded a PDF page directly in source string
    if not card.get('source_refs',[]):
        match=re.search(r'PDF\s+(\d+)',card.get('source',''))
        if match:
            book=next((b for b in books if b in card['source']),None)
            if book:verified_by_page[(book,int(match.group(1)))].add(card['term'])

report=[];unmatched=[]
for page in source:
    key=(page['book'],int(page['pdf_page']))
    group=by_page[key]
    unique=sorted({x['term'] for x in group})
    matched=[x for x in unique if x in terms]
    missing=[x for x in unique if x not in terms]
    confirmed=verified_by_page[key]
    report.append({'book':key[0],'pdf_page':key[1],
                   'ocr_characters':len(page['text'] or ''),
                   'ocr_candidates':len(unique),
                   'ocr_candidates_with_exact_term_in_deck':len(matched),
                   'ocr_candidates_without_exact_term':len(missing),
                   'manually_verified_cards_on_page':len(confirmed),
                   'status':'image_checked_some' if confirmed else 'not_fully_reviewed',
                   'notes':'OCR có thể sai hoặc bỏ sót; các số không phải % hoàn thành sách'})
    for term in missing:
        c=next(x for x in group if x['term']==term)
        unmatched.append({'book':key[0],'pdf_page':key[1],'ocr_candidate':term,
                          'ocr_reading_unverified':c.get('dictionary_reading',''),
                          'ocr_pos':c.get('pos',''),
                          'status':'OCR only; do not add to quiz before validating'})

for out,data in [('page_coverage_v5.csv',report),('ocr_unresolved_by_page_v5.csv',unmatched)]:
    with (P/out).open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=data[0].keys());wr.writeheader();wr.writerows(data)

summary={'total_pdf_pages':len(report),'total_cards':len(cards),
         'vocab_cards':sum(c['kind']=='vocab' for c in cards),
         'grammar_cards':sum(c['kind']=='grammar' for c in cards),
         'manually_verified_cards':sum(bool(c.get('verified')) for c in cards),
         'pages_with_at_least_one_manually_verified_card':sum(bool(x['manually_verified_cards_on_page']) for x in report),
         'pages_without_manual_card_verification':sum(not x['manually_verified_cards_on_page'] for x in report),
         'pages_ocr_empty':[{'book':x['book'],'pdf_page':x['pdf_page']} for x in report if x['ocr_characters']==0],
         'ocr_unresolved_occurrences':len(unmatched),
         'warning':'Do not read OCR-match counts as fraction of verified vocabulary completeness.'}
(P/'audit_summary_v5.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
