"""Read 35 community Soumatome N3 vocabulary tables for optional personal study.

Source: https://www.nguphaptiengnhat.net/tu-vung-tieng-nhat-n3.html
Does NOT attest to every term in the user's four scanned PDFs. Explicit click
only; never silently use partial pages or assign readings from OCR guesses.
Requires only the Python standard library.
"""
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from collections import Counter
import json,hashlib,re,unicodedata

BASE='https://www.nguphaptiengnhat.net/tu-vung-tieng-nhat-n3-part{part}.html'
ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'data'/'soumatome_35parts_cache.json'
JP='[一-龯々ぁ-ゟァ-ヿー・]'
KANA=re.compile(r'^[ぁ-ゟァ-ヿー\s]+$')
ROMAN=re.compile('[A-Za-z]')

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nesting=0;self.current_row=None;self.current_cell=None;self.rows=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.nesting+=1
        if not self.nesting:return
        if tag=='tr' and self.current_row is None:self.current_row=[]
        if tag in ('td','th') and self.current_row is not None:self.current_cell=[]
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(self.skip-1,0)
        if not self.nesting:return
        if tag in ('td','th') and self.current_cell is not None:
            self.current_row.append(' '.join(''.join(self.current_cell).split()));self.current_cell=None
        if tag=='tr' and self.current_row is not None:
            if len(self.current_row)>=4:self.rows.append(self.current_row)
            self.current_row=None
        if tag=='table':self.nesting=max(0,self.nesting-1)
    def handle_data(self,data):
        if self.current_cell is not None and not self.skip:self.current_cell.append(data)


def hira(s):return ''.join(chr(ord(c)-96) if '\u30a1'<=c<='\u30f6' else c for c in s)


def reading_from_mixed(raw, readings):
    """Resolve a *partly annotated* reading only with unambiguous known entries.

    Example: 予定をたてる -> よていをたてる, where 予定:よてい is
    independently known. Never invent the reading of an unknown kanji.
    """
    raw=unicodedata.normalize('NFKC',raw).replace(' ', '')
    raw=re.sub(r'[()（）\[\]{}【】]', '', raw)
    if KANA.fullmatch(raw):return raw
    chunks=[];i=0
    while i<len(raw):
        if re.fullmatch(r'[ぁ-ゟァ-ヿー]',raw[i]):
            chunks.append(raw[i]);i+=1;continue
        choices=[]
        for word,reading in readings.items():
            if raw.startswith(word,i) and re.search('[一-龯々]',word):
                choices.append((len(word),reading))
        if not choices:return None
        length,reading=max(choices)
        chunks.append(reading);i+=length
    result=''.join(chunks)
    return result if KANA.fullmatch(result) else None


def parse_part(html,part,known_readings=None):
    p=Tables();p.feed(html)
    parsed=[];errors=[]
    for cells in p.rows:
        if not cells[0].strip().isdigit():continue
        term=cells[1].strip();reading=cells[2].replace('🔊','').strip()
        if not term:term=reading
        term=unicodedata.normalize('NFKC',term)
        # Some sources add an audible button's text; allow only Japanese kana in reading.
        reading=re.sub(r'\s+','',reading)
        if not reading or not KANA.fullmatch(reading):
            corrected=reading_from_mixed(reading,known_readings or {})
            if corrected:reading=corrected
            else:
                errors.append({'part':part,'term':term,'reading':reading,'reason':'cannot confirm kana'});continue
        if not term or len(term)>38 or not re.search(JP,term):
            errors.append({'part':part,'term':term,'reason':'invalid term'});continue
        if len(term)==1 and term.isdigit():continue
        gloss=cells[3].split('💡')[0].split('Mẹo nhớ Từ')[0].strip(' .;,')
        if not gloss or len(gloss)>140 or not ROMAN.search(gloss) or not re.search('[A-Za-zÀ-ỹĐđ]',gloss) or gloss.isdigit():
            errors.append({'part':part,'term':term,'reason':'no Vietnamese gloss'});continue
        parsed.append({'term':term,'reading':reading,'meaning':gloss,'part':part})
    uniq={}
    for x in parsed:uniq.setdefault((x['term'],hira(x['reading'])),x)
    return list(uniq.values()),errors


def fetch_part(n):
    req=Request(BASE.format(part=n),headers={'User-Agent':'Mozilla/5.0 (Kotoba N3 personal study)', 'Accept':'text/html'})
    with urlopen(req,timeout=25) as r:
        raw=r.read(1_200_001)
        if len(raw)>1_200_000:raise ValueError(f'Part {n} HTML too large')
        return raw.decode('utf8',errors='replace')


def load_full_cache(expected_min=900):
    if not CACHE.is_file():raise ValueError('Chưa có bản cache 35 phần')
    raw=json.loads(CACHE.read_text(encoding='utf8'))
    if not isinstance(raw,list):raise ValueError('Cache không đúng định dạng')
    count=Counter(x.get('part') for x in raw if isinstance(x,dict))
    if set(count)!={*range(1,36)} or min(count.values())<15 or len(raw)<expected_min:
        raise ValueError('Cache chưa đủ 35 phần, không dùng dữ liệu thiếu')
    return raw


def import_35_parts(existing,fetcher=fetch_part,expected_min=900):
    # All 35 parts must be available, each with a plausible number of rows.
    data=[];failed=[];invalid=[];counts={};cache_used=False
    reading_by_term={}
    reading_ambiguity=set()
    for card in existing:
        term=card.get('term','');reading=card.get('reading','')
        if not re.search('[一-龯々]',term) or not KANA.fullmatch(reading):continue
        if term in reading_by_term and hira(reading_by_term[term])!=hira(reading):
            reading_ambiguity.add(term)
        reading_by_term[term]=reading
    for term in reading_ambiguity:reading_by_term.pop(term,None)
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            for n,raw in zip(range(1,36),pool.map(fetcher,range(1,36))):
                result,bad=parse_part(raw,n,reading_by_term);counts[n]=len(result)
                if len(result)<15:failed.append(n)
                data.extend(result);invalid.extend(bad)
        if failed:raise ValueError('Chưa tải/đọc đủ dữ liệu các bài: '+', '.join(map(str,failed)))
        bykey={}
        for x in data:bykey.setdefault((x['term'],hira(x['reading'])),x)
        if len(bykey)<expected_min:
            raise ValueError(f'Chỉ có {len(bykey)} mục khác nhau, chưa đạt kiểm tra độ đầy đủ {expected_min}')
    except Exception:
        # Only a previously validated *complete* local cache is acceptable.
        if not CACHE.is_file():raise
        cached=load_full_cache(expected_min=expected_min)
        bykey={(x['term'],hira(x['reading'])):x for x in cached}
        counts=Counter(x['part'] for x in bykey.values())
        cache_used=True
    known={(c['term'],hira(c['reading'])) for c in existing if c['kind']=='vocab'}
    cards=[]
    for (term,read),x in bykey.items():
        if (term,read) in known:continue
        items=[p.strip() for p in re.split('[;；]',x['meaning']) if p.strip()]
        uid=hashlib.sha256((term+'\0'+read).encode()).hexdigest()[:18]
        cards.append({'id':'part6-v-'+uid,'term':term,'reading':x['reading'],
          'meaning':items[0] if items else x['meaning'],'meaning_aliases':items[1:5],
          'kind':'vocab','tier':'core', 'topic':f"Soumatome N3 · Bài {x['part']}",
          'source':f"Danh sách tham khảo Soumatome N3 · Phần {x['part']} · Nguphaptiengnhat.net (chưa đối chiếu ảnh PDF)",
          'verified':False,'source_quality':'Nguồn cộng đồng chưa xác minh ảnh gốc',
          'external_source':BASE.format(part=x['part'])})
    if not cache_used:
        CACHE.write_text(json.dumps(list(bykey.values()),ensure_ascii=False,indent=2),encoding='utf8')
    return cards,{'source_unique':len(bykey),'source_pages':35,'already_existing':len(bykey)-len(cards),
      'new_cards':len(cards),'used_local_cache':cache_used,'invalid_source_rows':len(invalid),'min_source_part':min(counts.values()),
      'max_source_part':max(counts.values()),'status':'Nguồn cộng đồng; không chứng nhận đủ 469 trang'}

if __name__=='__main__':
    cards=json.loads((ROOT/'data'/'cards.json').read_text())
    added,stats=import_35_parts(cards)
    print(json.dumps(stats,ensure_ascii=False))
