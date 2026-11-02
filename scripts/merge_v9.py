#!/usr/bin/env python3
"""Source-gated v9 vocabulary expansion.

Only add hand-curated readings/glosses for Japanese terms with an exact OCR
surface in the learning pages of the user's four source PDFs. OCR is EVIDENCE
of occurrence, not verification of pronunciation/meaning or complete coverage.
Old card IDs, meanings and progress are left unchanged.
"""
from __future__ import annotations
from collections import defaultdict,Counter
from pathlib import Path
import csv, hashlib, json, re, unicodedata

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data'
CARDS=P/'cards.json'
SEED=P/'v9_curation_candidates.txt'
JP=re.compile(r'[一-龯々ぁ-ゟァ-ヿー]')
KANA=re.compile(r'^[ぁ-ゟァ-ヿー]+$')
BOOK_PRIORITY={'Từ vựng':0,'Kanji':1,'Ngữ pháp':2,'Đọc hiểu':3}
LEARNING={'Từ vựng':(12,107),'Kanji':(8,109),'Ngữ pháp':(8,109),'Đọc hiểu':(8,105)}

def normalize_reading(s):
    return ''.join(chr(ord(c)-96) if '\u30a1'<=c<='\u30f6' else c for c in unicodedata.normalize('NFKC',s))

def load_rows():
    for n,line in enumerate(SEED.read_text(encoding='utf8').splitlines(),1):
        if not line.strip() or line.startswith('#'):continue
        v=line.split('|')
        if len(v)!=3:raise ValueError(f'Line {n}: expected 3 fields')
        term,read,meaning=[x.strip() for x in v]
        if not JP.search(term) or not KANA.fullmatch(read) or re.search('[一-龯々]',read) or not meaning or len(meaning)>180:
            raise ValueError(f'Invalid Japanese candidate at line {n}: {line}')
        yield term,read,meaning

def build():
    cards=json.loads(CARDS.read_text(encoding='utf8'))
    known={(x['term'],normalize_reading(x['reading'])) for x in cards if x['kind']=='vocab'}
    names={x['term'] for x in cards if x['kind']=='vocab'}
    locs=defaultdict(list)
    for page in json.loads((P/'source_pages.json').read_text(encoding='utf8')):
        b=page['book'];i=int(page['pdf_page'])
        if LEARNING[b][0]<=i<=LEARNING[b][1]:
            locs[b].append((i,page.get('text','')))
    seen=set();added=[];unmatched=[];old=0;duplicate=0
    for term,reading,meaning in load_rows():
        key=(term,normalize_reading(reading))
        if key in seen:duplicate+=1;continue
        seen.add(key)
        if key in known:old+=1;continue
        refs=[{'book':book,'pdf_page':page}
              for book,plist in locs.items() for page,text in plist if term in text]
        refs.sort(key=lambda r:(BOOK_PRIORITY[r['book']],r['pdf_page']))
        if not refs:
            unmatched.append((term,reading,meaning));continue
        uid='v9-ocr-'+hashlib.sha256((term+'\0'+normalize_reading(reading)).encode()).hexdigest()[:18]
        tier='core' if any(ref['book'] in ('Từ vựng','Kanji') for ref in refs) else 'extra'
        primary=refs[0]
        glosses=[x.strip() for x in re.split('[;；]',meaning) if x.strip()]
        card={'id':uid,'term':term,'reading':reading,'meaning':glosses[0],
              'meaning_aliases':glosses[1:], 'kind':'vocab','tier':tier,
              'topic':f"Sách {primary['book']} · từ/cụm đối chiếu OCR",
              'source':f"OCR sách {primary['book']} PDF {primary['pdf_page']} (đã chuẩn hóa nghĩa/cách đọc; CHƯA duyệt ảnh trang)",
              'verified':False,'curated':True,
              'source_quality':'Đối chiếu chuỗi OCR, chưa kiểm tra thủ công từng mục trên ảnh',
              'source_refs':refs[:30]}
        cards.append(card);added.append(card);known.add(key);names.add(term)
    if len({c['id'] for c in cards})!=len(cards):raise ValueError('Duplicate card IDs')
    if len({(c['term'],normalize_reading(c['reading']),c['kind']) for c in cards})!=len(cards):
        # Existing v8 can contain accidental duplicates; only validate new cards.
        assert len(set(x['id'] for x in added))==len(added)
    CARDS.write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    all_v9=[c for c in cards if c['id'].startswith('v9-ocr-')]
    with (P/'v9_ocr_matched_added.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['term','reading','meaning','tier','first_book','first_pdf_page','all_refs','id','status'])
        for c in all_v9:
            refs=c['source_refs'];w.writerow([c['term'],c['reading'],c['meaning'],c['tier'],refs[0]['book'],refs[0]['pdf_page'],
                                    '; '.join(f"{r['book']}:{r['pdf_page']}" for r in refs),c['id'],'OCR-matched; NOT image verified'])
    with (P/'v9_not_added_without_ocr.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['term','reading','meaning','reason']);w.writerows((*x,'no exact OCR match in learning pages') for x in unmatched)
    manifest=json.loads((P/'manifest.json').read_text(encoding='utf8'))
    manifest.update({'version':'v9 source-gated additions','available_cards':len(cards),
            'vocab_cards':sum(x['kind']=='vocab' for x in cards),'grammar_cards':sum(x['kind']=='grammar' for x in cards),
            'v9_curated_ocr_added':len(all_v9),'v9_held_no_ocr':len(unmatched),
            'v9_note':'Các thẻ v9 được chuẩn hóa từ vựng và gắn trang OCR nhưng CHƯA xác minh toàn bộ ảnh sách',
            'completeness_claim':'NOT COMPLETE: no 100% page-by-page visual review of 469 pages yet'})
    (P/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return {'old':old,'duplicates_curated':duplicate,'added_this_run':len(added),'v9_total_added':len(all_v9),'held':len(unmatched),
            'cards':len(cards),'vocab':manifest['vocab_cards'],
            'books_new_refs':dict(Counter(b for card in added for b in set(x['book'] for x in card['source_refs']))),
            'verified_cards':sum(bool(c.get('verified')) for c in cards)}

if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
