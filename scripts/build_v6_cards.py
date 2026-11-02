#!/usr/bin/env python3
"""Merge manually normalized, textbook-OCR-backed v6 candidates without losing IDs.

The source is not marked scan-verified unless the exact page was visually checked.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,re,hashlib,csv
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data'
FILE=P/'cards.json'
cards=json.loads(FILE.read_text(encoding='utf8'))
candidates=json.loads((P/'vocabulary_candidates.json').read_text(encoding='utf8'))
known={(c['term'],c['reading'],c['kind']) for c in cards}
byterm=defaultdict(set)
for x in candidates:
    for s in x['sources']:
        if s['book'] in ['Từ vựng','Kanji','Ngữ pháp','Đọc hiểu']:
            byterm[x['term']].add((s['book'],int(s['pdf_page'])))
rank={'Từ vựng':0,'Kanji':1,'Ngữ pháp':2,'Đọc hiểu':3}
made=[];skips=0
for line_num,line in enumerate((P/'book_lexical_review_v6.tsv').read_text(encoding='utf8').splitlines(),1):
    if not line or line.startswith('#'):continue
    values=line.split('\t')
    if len(values)!=4:raise ValueError(f'Bad TSV line {line_num}')
    term,reading,gloss,category=[v.strip() for v in values]
    if not re.search('[一-龯々ぁ-ゟァ-ヿ]',term) or not re.fullmatch('[ぁ-ゟァ-ヿー]+',reading):raise ValueError(f'Bad Japanese {line_num}: {term}/{reading}')
    if (term,reading,'vocab') in known:skips+=1;continue
    items=[x.strip() for x in re.split('[;；]',gloss) if x.strip()]
    meaning=items[0]
    refs=sorted(byterm.get(term,()),key=lambda x:(rank.get(x[0],4),x[1]))
    tier='core' if any(x[0] in ('Từ vựng','Kanji') for x in refs) else 'extra'
    if refs:
        source='OCR: '+', '.join(f'{book} · PDF {p}' for book,p in refs[:4])+' (chưa kiểm ảnh)'
    else:source='Từ bổ sung biên soạn khi kiểm kê; chưa xác nhận vị trí chính xác trong sách'
    uid=hashlib.sha256((term+'\0'+reading).encode()).hexdigest()[:18]
    card={'id':'rev6-v-'+uid,'term':term,'reading':reading,'meaning':meaning,
      'meaning_aliases':items[1:], 'kind':'vocab','tier':tier,
      'topic':'Từ bổ sung sau kiểm kê · '+('Từ vựng' if category=='vocab' else 'Kanji'),
      'source':source,'source_quality':'đã chuẩn hóa nghĩa; chưa duyệt ảnh sách',
      'verified':False,'curated':True,'source_refs':[{'book':b,'pdf_page':p} for b,p in refs[:30]]}
    cards.append(card);made.append(card);known.add((term,reading,'vocab'))
assert len(set(c['id'] for c in cards))==len(cards)
FILE.write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
manifest=json.loads((P/'manifest.json').read_text())
manifest.update({'available_cards':len(cards),'vocab_cards':sum(c['kind']=='vocab' for c in cards),
                 'grammar_cards':sum(c['kind']=='grammar' for c in cards),
                 'v6_curated_added':len(made),'version':'v6 source audit',
                 'coverage':f"{sum(c['kind']=='vocab' for c in cards):,} từ/cụm từ và {sum(c['kind']=='grammar' for c in cards)} mẫu ngữ pháp. OCR 469 trang, chưa duyệt thủ công đủ. Không khẳng định bao phủ 100%.",
                 'v6_source_import':'Có chức năng nhập bổ sung danh sách Soumatome N3 từ nguồn cộng đồng khi có mạng, kết quả phải kiểm chứng sau nhập'})
(P/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'total':len(cards),'vocab':manifest['vocab_cards'],'added':len(made),'not_added_as_existing':skips,'ocr_matched':sum(bool(c['source_refs']) for c in made),'unreferenced':sum(not c['source_refs'] for c in made)},ensure_ascii=False))
