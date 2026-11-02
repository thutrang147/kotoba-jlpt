"""One-time optional Japanese-Vietnamese dictionary matching for OCR candidates.

Keeps uncertain OCR words out of quizzes. Download runs ONLY after the user presses
'Tra từ điển...' on the local data page. Can also use a local Yomichan ZIP.
The OCR page is evidence of possible occurrence, NOT proof of textbook coverage.
"""
from collections import Counter,defaultdict
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib,json,re,unicodedata,zipfile

BASE=Path(__file__).resolve().parent
SOURCE=BASE/'data'/'vocabulary_candidates.json'
ZIP=BASE/'data'/'jmdict_vietnamese.zip'
URL='https://raw.githubusercontent.com/dreamofi/yomichan-Vietnamese-dictionary/master/vietnameseDict/jmdict_vietnamese.zip'
MAX_ZIP=35_000_000

class StripHTML(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,x):self.parts.append(x)
    def text(self):return ''.join(self.parts)

def clean_gloss(x):
    if isinstance(x,str):
        parser=StripHTML();parser.feed(unescape(x));s=parser.text()
    elif isinstance(x,dict):
        if x.get('type')=='text':return clean_gloss(x.get('text',''))
        if x.get('type')=='structured-content':return ' '.join(filter(None,map(clean_gloss,x.get('content',[]))))
        return clean_gloss(x.get('content',x.get('text','')))
    elif isinstance(x,list):return ' ; '.join(filter(None,(clean_gloss(v) for v in x)))
    else:return ''
    s=unicodedata.normalize('NFKC',s)
    s=re.sub(r'\s+',' ',s).strip(' ,-;:')
    return s

def to_hira(x):
    return ''.join(chr(ord(c)-96) if '\u30a1'<=c<='\u30f6' else c for c in x)

def valid_reading(s):
    return bool(s) and not re.search('[一-龯々A-Za-z0-9]',s) and bool(re.search('[ぁ-ゟァ-ヿ]',s))

def clean_meanings(raw):
    if isinstance(raw,list):
        vals=[]
        for x in raw:
            v=clean_gloss(x)
            if v:vals.append(v)
        return vals
    return [clean_gloss(raw)]

def is_vi(text):
    # A Japanese-Vietnamese dictionary may have only a one-word gloss such as 'dao'.
    # Exclude markup, dictionary reference placeholders, Japanese-only entries, and giant articles.
    return bool(re.search('[A-Za-zÀ-ỹĐđ]',text)) and not re.search(r'https?://|</?\w+|\\u[0-9a-f]{4}',text,re.I) and len(text)<=250

def get_zip(local_path=None):
    if local_path:
        z=Path(local_path)
        if not z.exists():raise ValueError('Không tìm thấy file từ điển')
        return z
    if ZIP.is_file() and zipfile.is_zipfile(ZIP):return ZIP
    tmp=ZIP.with_suffix('.download')
    req=Request(URL,headers={'User-Agent':'KotobaJLPT-local/4 (personal study)'})
    try:
        with urlopen(req,timeout=50) as resp,open(tmp,'wb') as out:
            n=0
            while True:
                chunk=resp.read(256*1024)
                if not chunk:break
                n+=len(chunk)
                if n>MAX_ZIP:raise ValueError('File từ điển vượt quá kích thước tối đa')
                out.write(chunk)
        if not zipfile.is_zipfile(tmp):raise ValueError('Nguồn tải không phải ZIP từ điển hợp lệ')
        tmp.replace(ZIP)
        return ZIP
    finally:
        tmp.unlink(missing_ok=True)

def parse_zip(zip_path):
    index=defaultdict(list)
    with zipfile.ZipFile(zip_path) as f:
        members=[n for n in f.namelist() if re.search(r'(^|/)term_bank_\d+\.json$',n) and not n.startswith('__MACOSX')]
        if not members:raise ValueError('ZIP không có term_bank_*.json (định dạng từ điển Yomichan)')
        if sum(f.getinfo(n).file_size for n in members)>180_000_000:raise ValueError('Dữ liệu từ điển giải nén quá lớn')
        for name in members:
            entries=json.loads(f.read(name))
            if not isinstance(entries,list):continue
            for row in entries:
                if not isinstance(row,list) or len(row)<6:continue
                term,reading=row[0],row[1]
                if not isinstance(term,str) or not isinstance(reading,str):continue
                reading=reading or term
                if not valid_reading(reading):continue
                meanings=clean_meanings(row[5]);meanings=[m for m in meanings if is_vi(m) and re.search('[\u00c0-\u01b0\u1ea0-\u1ef9\u0110\u0111]',m)]
                if not meanings:continue
                # Yomichan source ships English glosses first, appends Vietnamese at end.
                # Use the Vietnamese part only, not the English dictionary gloss.
                m=meanings[-1].split(' ; ')[0].strip()
                if len(m)>140:m=m[:140].rsplit(' ',1)[0]
                if len(m)<2:continue
                index[term].append((reading,m, row[4] if isinstance(row[4],(float,int)) else 0))
    return index

def dictionary_cards(existing, zip_path=None):
    source=json.loads(SOURCE.read_text(encoding='utf8'))
    known={(c['term'],to_hira(c['reading'])) for c in existing if c['kind']=='vocab'}
    index=parse_zip(get_zip(zip_path))
    made=[];no_match=[];ambiguous=[];matched=0
    for candidate in source:
        term=candidate['term'];raw=to_hira(candidate.get('dictionary_reading',''))
        if not any(ch in term for ch in 'ぁあいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン') and not re.search('[一-龯々]',term):continue
        options=index.get(term,[])
        if not options:
            no_match.append(term);continue
        # OCR morphology sometimes gives verb stems; normal dictionary reading wins,
        # but exact reading evidence is required when the kanji has multiple readings.
        unique={to_hira(k) for k,_,_ in options}
        ranked=[]
        for reading,meaning,score in options:
            hira=to_hira(reading)
            if (term,hira) in known:continue
            exact=hira==raw
            prefix=(len(raw)>=2 and (hira.startswith(raw) or raw.startswith(hira)))
            if re.search('[一-龯々]',term) and len(unique)>1 and not (exact or prefix):continue
            if not (exact or prefix or len(unique)==1 or term==reading):continue
            ranked.append((2 if exact else 1 if prefix else 0,score,reading,meaning))
        if not ranked:
            ambiguous.append(term);continue
        ranked.sort(reverse=True)
        # Don't hallucinate extra readings of the same term from separate dictionary senses.
        _,_,reading,meaning=ranked[0];hira=to_hira(reading)
        if (term,hira) in known:continue
        if len(meaning)>150:continue
        locs=[x for x in candidate['sources'] if x['book'] in ('Từ vựng','Kanji','Ngữ pháp','Đọc hiểu')]
        if not locs:continue
        tier='core' if any(x['book'] in ('Từ vựng','Kanji') for x in locs) else 'extra'
        refs=[{'book':x['book'],'pdf_page':x['pdf_page']} for x in locs[:30]]
        uid=hashlib.sha256((term+'\0'+reading).encode()).hexdigest()[:18]
        made.append({'id':'dict-v-'+uid,'term':term,'reading':reading,'meaning':meaning,
          'meaning_aliases':[],'kind':'vocab','tier':tier,'topic':'Từ có trong OCR · tra Nhật–Việt',
          'source':'Khớp OCR sách + từ điển Nhật–Việt; chưa soát thủ công theo trang',
          'verified':False,'source_quality':'tự động, chưa kiểm tra ngữ cảnh',
          'source_refs':refs,'dictionary':'yomichan-vietnamese-dictionary'})
        known.add((term,hira));matched+=1
    return made,{'dictionary_entries':sum(len(v) for v in index.values()),'added':matched,
          'unmatched_candidates':len(no_match),'ambiguous_candidates':len(ambiguous),
          'source_total_candidates':len(source)}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--zip',help='Yomichan Japanese-Vietnamese ZIP on disk');p.add_argument('--out',default='data/dictionary_enriched_preview.json')
    args=p.parse_args()
    old=json.loads((BASE/'data/cards.json').read_text(encoding='utf8'))
    cards,stats=dictionary_cards(old,args.zip)
    (BASE/args.out).write_text(json.dumps(cards,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(stats,ensure_ascii=False,indent=2))
