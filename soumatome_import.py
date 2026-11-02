"""Optional import of a public community Soumatome N3 word inventory.

IMPORTANT: Not a replacement for auditing the user's scanned textbooks.
Run only on an explicit user click. Fetch a bounded number of pages; reject
unexpected page structures rather than silently claim all source words arrived.
"""
from html.parser import HTMLParser
from html import unescape
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib,json,re,unicodedata

ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'data'/'soumatome_external_review.json'
BASE='https://jlpt180.com/jlpt-n3/tu-vung/soumatome/'
JP=re.compile(r'^[一-龯々ぁ-ゟァ-ヿー・]+[一-龯々ぁ-ゟァ-ヿー・するいな]*$')
KANA=re.compile(r'^[ぁ-ゟァ-ヿー]+$')
SOURCE=re.compile(r'Soumatome\s*[·•・|]\s*Tuần\s*(\d+)\s*[·•・|]\s*Ngày\s*(\d+)',re.I)
SOURCE_COUNT=re.compile(r'(?:Trang|Page)\s*(\d+)\s*/\s*(\d+)',re.I)

class Blocks(HTMLParser):
    CUT={'h1','h2','h3','h4','h5','h6','p','li','article','section','blockquote','br','div'}
    def __init__(self):super().__init__(convert_charrefs=True);self.vals=[];self.part=[];self.ignore=0
    def flush(self):
        t=unicodedata.normalize('NFKC',unescape(''.join(self.part))).strip()
        t=re.sub(r'\s+',' ',t)
        if t:self.vals.append(t)
        self.part=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript'):
            self.flush();self.ignore+=1;return
        if self.ignore:return
        if tag in self.CUT:self.flush()
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'):
            self.ignore=max(0,self.ignore-1);return
        if self.ignore:return
        if tag in self.CUT:self.flush()
    def handle_data(self,data):
        if not self.ignore:self.part.append(data)


def to_hira(s):
    return ''.join(chr(ord(k)-96) if '\u30a1'<=k<='\u30f6' else k for k in s)


def extract(html):
    p=Blocks();p.feed(html);p.flush()
    lines=p.vals
    # Block merging can create a duplicate line: harmless because of keyed dedup.
    items=[]
    for i,line in enumerate(lines):
        pieces=line.split()
        if len(pieces)==2 and JP.fullmatch(pieces[0]) and KANA.fullmatch(pieces[1]):term,reading=pieces
        elif JP.fullmatch(line):term,reading=line,''
        else:continue
        if i>0 and KANA.fullmatch(line) and re.search('[一-龯々]',lines[i-1]) and JP.fullmatch(lines[i-1]):
            continue  # furigana belongs to preceding kanji headword
        if len(term)>20 or len(term)<1:continue
        future=lines[i+1:i+10]
        found=None
        for j,s in enumerate(future):
            m=SOURCE.search(s)
            if m:found=j;week,day=map(int,m.groups());break
        if found is None or not 1<=week<=6 or not 1<=day<=7:continue
        context=future[:found]
        if not reading and context and KANA.fullmatch(context[0]) and re.search('[一-龯々]',term):reading=context.pop(0)
        if not reading:reading=term if KANA.fullmatch(term) else ''
        if not reading or re.search(r'[一-龯々]',reading):continue
        # First Vietnamese phrase before metadata, before example sentences.
        meanings=[]
        for part in context:
            if part.startswith('Hán Việt:'):continue
            if re.search('[一-龯々ぁ-ゟァ-ヿ]',part):continue
            if re.search('[A-Za-zÀ-ỹĐđ]',part) and not part.lower().startswith(('danh từ','động từ','tính từ','từ vựng','soumatome')):
                meanings.append(part)
        if not meanings:continue
        meaning=meanings[0].strip(' .,;')[:130]
        if len(meaning)<2:continue
        items.append({'term':term,'reading':reading,'meaning':meaning,'week':week,'day':day})
    unique={}
    for x in items:unique.setdefault((x['term'],to_hira(x['reading'])),x)
    return list(unique.values()),p.vals


def fetch_page(page):
    url=BASE if page==1 else BASE+'?page='+str(page)
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; KotobaJLPT/6; personal study)','Accept':'text/html'})
    with urlopen(req,timeout=25) as resp:
        raw=resp.read(1_500_001)
        if len(raw)>1_500_000:raise ValueError('HTML nguồn quá lớn')
        return raw.decode('utf-8',errors='replace')


def import_public_inventory(existing, fetcher=fetch_page, expected_min=700):
    # Reject partial and inconsistent page sequences to avoid labeling a partial import 'complete'.
    first=fetcher(1)
    items,lines=extract(first)
    match=SOURCE_COUNT.search(' '.join(lines))
    pages=int(match.group(2)) if match else 20
    if not 1<=pages<=30:raise ValueError('Số trang nguồn không hợp lệ')
    if len(items)<10:raise ValueError('Không đọc được cấu trúc danh sách từ nguồn')
    collected=list(items)
    with ThreadPoolExecutor(max_workers=4) as ex:
        for batch in ex.map(fetcher,range(2,pages+1)):
            group,line2=extract(batch)
            if len(group)<10:raise ValueError('Một trang nguồn không có đủ mục từ; dừng để tránh nhập thiếu')
            collected.extend(group)
    distinct={}
    for row in collected:distinct.setdefault((row['term'],to_hira(row['reading'])),row)
    if len(distinct)<expected_min:
        raise ValueError(f'Nguồn chỉ trả về {len(distinct)} mục, chưa đạt mức an toàn {expected_min}; không nhập dữ liệu không đầy đủ')
    known={(c['term'],to_hira(c['reading'])) for c in existing if c['kind']=='vocab'}
    additions=[]
    for (term,hira),row in distinct.items():
        if (term,hira) in known:continue
        original=row['meaning']
        parts=[v.strip() for v in re.split(r'[;,]',original) if v.strip()]
        meaning=parts[0] if parts else original
        uid=hashlib.sha256((term+'\0'+hira).encode()).hexdigest()[:18]
        additions.append({'id':'src6-v-'+uid,'term':term,'reading':row['reading'],
          'meaning':meaning,'meaning_aliases':parts[1:5],'kind':'vocab','tier':'core',
          'topic':f"Soumatome N3 · Tuần {row['week']} · Ngày {row['day']}",
          'source':f"Danh sách đối chiếu công khai JLPT180 · Tuần {row['week']} · Ngày {row['day']}; chưa đối chiếu ảnh PDF",
          'verified':False,'source_quality':'Nguồn cộng đồng (ngoài sách scan)',
          'external_source':BASE})
    CACHE.write_text(json.dumps(list(distinct.values()),ensure_ascii=False,indent=2),encoding='utf8')
    return additions,{'source_unique':len(distinct),'source_pages':pages,'already_existing':len(distinct)-len(additions),'new_cards':len(additions),'status':'DANH SÁCH CỘNG ĐỒNG; chưa xác minh đủ 4 sách'}

if __name__=='__main__':
    cards=json.loads((ROOT/'data'/'cards.json').read_text())
    additions,stats=import_public_inventory(cards)
    (ROOT/'data'/'soumatome_additions_preview.json').write_text(json.dumps(additions,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(stats,ensure_ascii=False,indent=2))
