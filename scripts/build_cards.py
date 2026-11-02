"""Rebuild Kotoba offline cards from original source-reviewed seed + curated data.

Full vocabulary TSV entries have a Vietnamese gloss and a kana reading, checked
at entry level, but are NOT claimed as 100% sourced from a specific textbook page.
OCR evidence only identifies possible occurrence and never proves correctness.
"""
from pathlib import Path
import json, hashlib, collections, re
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data'
base=json.loads((P/'cards_initial_137.json').read_text(encoding='utf8'))
candidates=json.loads((P/'vocabulary_candidates.json').read_text(encoding='utf8'))
sources={}
for candidate in candidates:
    for loc in candidate['sources']:
        sources.setdefault(candidate['term'],set()).add((loc['book'],loc['pdf_page']))
order={'Từ vựng':0,'Kanji':1,'Ngữ pháp':2,'Đọc hiểu':3}

def locations(term):
    return sorted(sources.get(term,()),key=lambda x:(order.get(x[0],4),x[1]))

def getlines(filename,n):
    for lineno,line in enumerate((P/filename).read_text(encoding='utf8').splitlines(),1):
        if not line or line.startswith('#'):continue
        parts=line.split('\t')
        if len(parts)!=n:raise ValueError(f'{filename}:{lineno}: expected {n} tab fields, got {len(parts)}')
        yield [p.strip() for p in parts]

cards=base.copy()
existing={(c['term'],c['reading'],c['kind']) for c in base}
source_summary=collections.Counter()

def add_vocab(term,reading,meaning,group):
    key=(term,reading,'vocab')
    if key in existing:return False
    if not term or not reading or not meaning:raise ValueError(f'Empty value in vocabulary: {term!r}')
    if len(term)>26 or len(reading)>35 or len(meaning)>160:raise ValueError(f'Implausible length: {term!r}')
    if not re.search(r'[\u3040-\u30ff\u3400-\u9fff]',term):raise ValueError(f'Non-Japanese term: {term!r}')
    if re.search(r'[一-龯々]',reading):raise ValueError(f'Reading still contains kanji: {term!r} -> {reading!r}')
    locs=locations(term)
    tier='core' if any(book in ('Từ vựng','Kanji') for book,page in locs) else 'extra'
    refs=[{'book':book,'pdf_page':p} for book,p in locs[:30]]
    tag='OCR nhận diện (chưa kiểm trang): '+', '.join(f'{book} · PDF {p}' for book,p in locs[:3]) if locs else 'Từ N3 bổ sung (chưa đối chiếu sách)'
    aliases=list(dict.fromkeys(s.strip() for s in re.split(r'\s*;\s*',meaning) if s.strip())) if ';' in meaning else []
    card={'id':('cur-v-' if group=='v2' else 'full-v-')+hashlib.sha256((term+'\0'+reading).encode()).hexdigest()[:18],
        'term':term,'reading':reading,'meaning':meaning,'meaning_aliases':aliases,
        'kind':'vocab','tier':tier,'topic':('Từ vựng N3 · mở rộng' if group=='v2' else 'Từ vựng N3 · bộ bổ sung lớn'),
        'source':tag,'verified':False,'curated':True,'source_quality':'OCR-khớp từ' if locs else 'biên soạn',
        'source_refs':refs}
    cards.append(card);existing.add(key)
    source_summary[locs[0][0] if locs else 'Không nhận diện trong OCR']+=1
    return True

for term,reading,meaning in getlines('curated_additions.tsv',3):
    add_vocab(term,reading,meaning,'v2')
for term,reading,meaning in getlines('vocab_full_additions.tsv',3):
    add_vocab(term,reading,meaning,'full')
for term,reading,meaning in getlines('source_vocab_v4.tsv',3):
    add_vocab(term,reading,meaning,'full')
for term,meaning,alias in getlines('curated_grammar.tsv',3):
    key=(term,term,'grammar')
    if key in existing:continue
    id='cur-g-'+hashlib.sha256(term.encode()).hexdigest()[:18]
    cards.append({'id':id,'term':term,'reading':term,'meaning':meaning,
        'meaning_aliases':[alias] if alias else [],'kind':'grammar','tier':'extra',
        'topic':'Mẫu ngữ pháp · mở rộng',
        'source':'Mẫu ôn tập biên soạn; chưa đối chiếu từng trang sách',
        'verified':False,'curated':True})
    existing.add(key)

# v5: additional book-specific candidates and page-reviewed missing entries.
# Preserve all earlier card IDs. An OCR-match is not proof of a manually verified page.
book_page_terms={(x['term'],z['book'],int(z['pdf_page']))
                 for x in candidates for z in x['sources']}
source_counts=collections.Counter()

def add_book_v5(book,page_text,term,reading,meaning,verified=False):
    page=int(page_text)
    key=(term,reading,'vocab')
    if key in existing:return False
    if len(term)>26 or len(reading)>35 or len(meaning)>160 or not all((term,reading,meaning)):
        raise ValueError(f'Invalid supplementary vocabulary: {term}')
    if re.search(r'[一-龯々]',reading) or not re.search(r'[\u3040-\u30ff\u3400-\u9fff]',term):
        raise ValueError(f'Invalid Japanese/reading in supplementary vocabulary: {term}, {reading}')
    seen_in_ocr=(term,book,page) in book_page_terms
    evidence='đã kiểm tra bằng ảnh sách' if verified else 'đối chiếu chuỗi OCR; chưa xác minh ảnh' if seen_in_ocr else 'vị trí từ bản OCR; chưa xác minh ảnh'
    tier='core' if book in ('Từ vựng','Kanji') else 'extra'
    uid=hashlib.sha256((term+'\0'+reading).encode('utf8')).hexdigest()[:18]
    aliases=list(dict.fromkeys(t.strip() for t in meaning.split(';') if t.strip())) if ';' in meaning else []
    card={'id':'book5-v-'+uid,'term':term,'reading':reading,'meaning':meaning,'meaning_aliases':aliases,
          'kind':'vocab','tier':tier,'topic':book+' · bổ sung có đối chiếu',
          'source':f'Soumatome N3 {book} · PDF {page} ({evidence})',
          'verified':verified,'curated':True,
          'source_quality': 'ảnh sách xác nhận' if verified else 'chưa kiểm tra thủ công theo trang',
          'source_refs':[{'book':book,'pdf_page':page}] if verified or seen_in_ocr else []}
    cards.append(card);existing.add(key)
    source_counts['verified' if verified else 'ocr_candidate']+=1
    if not verified and not seen_in_ocr:source_counts['unmatched_source_hint']+=1
    return True

for book,page,term,reading,meaning in getlines('verified_missing_v5.tsv',5):
    add_book_v5(book,page,term,reading,meaning,verified=True)
for book,page,term,reading,meaning in getlines('ocr_reviewed_v5.tsv',5):
    add_book_v5(book,page,term,reading,meaning,verified=False)

for book,page,term,meaning in getlines('verified_grammar_v5.tsv',4):
    key=(term,term,'grammar')
    if key in existing:continue
    card={'id':'book5-g-'+hashlib.sha256(term.encode()).hexdigest()[:18],
          'term':term,'reading':term,'meaning':meaning,'meaning_aliases':[],
          'kind':'grammar','tier':'core','topic':'Ngữ pháp · cấu trúc bị động',
          'source':f'Soumatome N3 {book} · PDF {page} (đã kiểm tra ảnh sách)',
          'verified':True,'curated':True,'source_quality':'ảnh sách xác nhận',
          'source_refs':[{'book':book,'pdf_page':int(page)}]}
    cards.append(card);existing.add(key)
    source_counts['verified_grammar']+=1

from collections import Counter
ids=[c['id'] for c in cards]
if len(set(ids))!=len(ids):raise RuntimeError('ID collision')
(P/'cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
manifest=json.loads((P/'manifest.json').read_text(encoding='utf8'))
manifest.update({'available_cards':len(cards),
    'vocab_cards':sum(x['kind']=='vocab' for x in cards),
    'grammar_cards':sum(x['kind']=='grammar' for x in cards),
    'verified_cards':sum(bool(x.get('verified')) for x in cards),
    'coverage':f"{sum(x['kind']=='vocab' for x in cards):,} thẻ từ vựng/cụm từ, {sum(x['kind']=='grammar' for x in cards)} ngữ pháp. Có {sum(bool(x.get('verified')) for x in cards)} thẻ xác nhận theo ảnh PDF, còn lại chưa kiểm hết; chưa bảo đảm đầy đủ 469 trang.",
    'ocr_status':'Đã OCR 469 trang; 7.210 ứng viên chưa xác minh. Dữ liệu OCR sai được giữ riêng, không tự động đưa vào câu hỏi.',
    'past_exam_status':'Chưa thống kê theo từng kỳ JLPT; không có bộ đề thật đầy đủ được JLPT công bố công khai.',
    'tier_rule':'Trọng tâm = từ được OCR nhận diện trong Từ vựng/Kanji (không đồng nghĩa được sách trực tiếp dạy); còn lại bổ sung. 137 thẻ đầu là thẻ gốc xác minh trang.',
    'expanded_vocab_tsv':'vocab_full_additions.tsv + source_vocab_v4.tsv',
    'source_evidence_summary':dict(source_summary),
    'v5_additions':dict(source_counts),
    'rebuild_command':'python3 scripts/build_cards.py',
    'verified_missing_v5':'verified_missing_v5.tsv',
    'additional_review_v5':'ocr_reviewed_v5.tsv'})
(P/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Card deck total:',len(cards),'vocab:',manifest['vocab_cards'],'grammar:',manifest['grammar_cards'],'v5 additions:',source_counts)
