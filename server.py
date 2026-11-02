#!/usr/bin/env python3
"""Kotoba N3, offline-first local-only quiz, Python standard library."""
import datetime as dt
import sys
import csv
import io
from zoneinfo import ZoneInfo
import database
import online
from contextlib import contextmanager
import json
import os
import random
import re
import sqlite3
import threading
import unicodedata
import uuid
from urllib.error import URLError
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('JLPT_DB', str(ROOT/'progress.sqlite3')))
LOCK = threading.RLock()
CHOICE_GOAL, WRITE_GOAL = 3, 3
# Consecutive correct answers on distinct scheduled practice days.
CHOICE_DELAYS = [1, 2, 3]
WRITE_DELAYS = [1, 3, 7]
READY_DELAY = 30

def connect():
    return database.connection(DB)

def now():return dt.datetime.now(dt.timezone.utc)
def today():return now().astimezone(ZoneInfo(os.environ.get('APP_TIMEZONE','Asia/Ho_Chi_Minh'))).date().isoformat()

def norm(x,reading=False):
    x=unicodedata.normalize('NFKC',str(x)).strip().lower()
    if reading:
        return ''.join(chr(ord(k)-96) if '\u30a1' <= k <= '\u30f6' else k for k in x if not k.isspace())
    return re.sub(r'[\s.,;:!?。！？]+',' ',x).strip()

def card_skills(c):
    if c['kind']=='grammar':return ['meaning','structure']
    return ['reading','meaning'] if re.search('[一-龯々]',c['term']) else ['meaning']

def target(c,skill):return c['reading'] if skill=='reading' else c['term'] if skill=='structure' else c['meaning']

def validate_card(c):
    for f in ['id','term','reading','meaning','kind','tier','topic']:
        if not isinstance(c.get(f),str) or not c[f].strip():raise ValueError('Thiếu dữ liệu '+f)
    if len(c['id'])>130 or c['kind'] not in ('vocab','grammar') or c['tier'] not in ('core','extra'):
        raise ValueError('Định dạng thẻ không hợp lệ')
    for f in ['meaning_aliases','reading_aliases','structure_aliases']:
        if f in c and (not isinstance(c[f],list) or any(not isinstance(a,str) for a in c[f])):
            raise ValueError('Danh sách đáp án tương đương không hợp lệ')

def seed_cards(c):
    seeds=json.loads((ROOT/'data/cards.json').read_text(encoding='utf8'))
    existing={row['id'] for row in c.execute('SELECT id FROM cards')}
    additions=[]
    for card in seeds:
        validate_card(card)
        if card['id'] not in existing:
            additions.append((card['id'],json.dumps(card,ensure_ascii=False)))
    # Batch writes avoid thousands of network round trips on a Neon cold start.
    for offset in range(0,len(additions),250):
        batch=additions[offset:offset+250]
        c.execute('INSERT INTO cards(id,body) VALUES '+','.join('(?,?)' for _ in batch)+
                  ' ON CONFLICT(id) DO NOTHING',tuple(value for row in batch for value in row))

def init():
    online.validate_config()
    if not os.environ.get('DATABASE_URL'):DB.parent.mkdir(parents=True,exist_ok=True)
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS cards(id TEXT PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS progress(card_id TEXT, skill TEXT, stage INTEGER DEFAULT 0,
        due TEXT, last_day TEXT, successes INTEGER DEFAULT 0, errors INTEGER DEFAULT 0,
        PRIMARY KEY(card_id,skill));
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, created TEXT, body TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);''')
        c.executescript(online.SCHEMA)
        cols=database.columns(c,'progress')
        for key,sql in [('phase',"TEXT NOT NULL DEFAULT 'choice'"),('streak','INTEGER NOT NULL DEFAULT 0'),('mastered','INTEGER NOT NULL DEFAULT 0'),('last_mode','TEXT')]:
            if key not in cols:c.execute('ALTER TABLE progress ADD COLUMN '+key+' '+sql)
        # A migrated user who already has >=3 spaced reviews can start typing.
        c.execute("UPDATE progress SET phase='write', streak=0 WHERE stage>=3 AND successes>=3 AND phase='choice'")
        seed_cards(c)

def all_cards(c):return [json.loads(r['body']) for r in c.execute('SELECT body FROM cards')]
def progress_rows(c):return [dict(r) for r in c.execute('SELECT * FROM progress')]

def progress_stats(records, progress, event_card_ids=()):
    rows={(p['card_id'],p['skill']):p for p in progress}
    result={'total':len(records),'started':0,'unlearned':0,'learning':0,
            'ready':0,'mastered':0,'vocab_total':0,'grammar_total':0,
            'vocab_mastered':0,'grammar_mastered':0,'reading_total':0,
            'reading_ready':0,'meaning_total':0,'meaning_ready':0}
    status_ids={key:[] for key in ('unlearned','learning','ready','mastered')}
    for card in records:
        skills=card_skills(card)
        states=[rows.get((card['id'],skill)) for skill in skills]
        started=card['id'] in event_card_ids or any(state is not None for state in states)
        mastered=all(state and state.get('mastered',0) for state in states)
        ready=not mastered and all(state and state.get('phase')=='ready' and not state.get('mastered',0)
                                   for state in states)
        status='mastered' if mastered else 'ready' if ready else 'learning' if started else 'unlearned'
        status_ids[status].append(card['id'])
        result[status]+=1
        result['started']+=int(started)
        kind_key='vocab' if card['kind']=='vocab' else 'grammar'
        result[kind_key+'_total']+=1
        result[kind_key+'_mastered']+=int(mastered)
        if 'reading' in skills:
            result['reading_total']+=1
            result['reading_ready']+=int(bool(rows.get((card['id'],'reading')) and
                                             rows[(card['id'],'reading')].get('phase')=='ready'))
        if 'meaning' in skills:
            result['meaning_total']+=1
            result['meaning_ready']+=int(bool(rows.get((card['id'],'meaning')) and
                                             rows[(card['id'],'meaning')].get('phase')=='ready'))
    result['status_ids']=status_ids
    return result

def get_state():
    with connect() as c:
        records=all_cards(c);ps=progress_rows(c)
        event_card_ids=set()
        for row in c.execute('SELECT body FROM events'):
            try:
                body=json.loads(row['body'])
                if body.get('card_id'):event_card_ids.add(body['card_id'])
            except (TypeError,ValueError):
                continue
        n=sum(1 for r in c.execute('SELECT created FROM events')
              if dt.datetime.fromisoformat(r['created']).astimezone(ZoneInfo(os.environ.get('APP_TIMEZONE','Asia/Ho_Chi_Minh'))).date().isoformat()==today())
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    manifest['available_cards']=len(records)
    manifest['vocab_cards']=sum(x['kind']=='vocab' for x in records)
    manifest['grammar_cards']=sum(x['kind']=='grammar' for x in records)
    verified=sum(bool(x.get('verified')) for x in records)
    manifest['verified_cards']=verified
    from soumatome_parts_import import CACHE
    if CACHE.is_file():
        try:
            cache_data=json.loads(CACHE.read_text(encoding='utf8'))
            manifest['soumatome_parts_imported']=len(cache_data)
        except (ValueError,OSError):
            manifest['soumatome_parts_imported']=0
    else:
        manifest['soumatome_parts_imported']=0
    manifest['coverage']=(f"{manifest['vocab_cards']:,} thẻ từ vựng/cụm từ, "
         f"{manifest['grammar_cards']} mẫu ngữ pháp. "
         f"{verified} thẻ được kiểm tra bằng ảnh sách; chưa kiểm đủ 469 trang.")
    return {'cards':records,'progress':ps,'progress_stats':progress_stats(records,ps,event_card_ids),
            'today_answers':n,'sources':manifest,
            'study':study_state(),
            'config':{'choice_goal':CHOICE_GOAL,'write_goal':WRITE_GOAL}}

def study_state():
    with connect() as c:return online.get_session(sys.modules[__name__],c)

def choice_options(card,skill,pool):
    correct=target(card,skill)
    accepted={norm(x,skill=='reading') for x in [correct]+card.get(skill+'_aliases',[])}
    candidates=[c for c in pool if c['kind']==card['kind'] and c['id']!=card['id']]
    if skill=='meaning':
        same_topic=[c for c in candidates if c.get('topic')==card.get('topic')]
        candidates=same_topic or candidates
    other=list({target(c,skill) for c in candidates
                if norm(target(c,skill),skill=='reading') not in accepted})
    random.shuffle(other)
    selected=[];seen={norm(correct,skill=='reading')}
    for option in other:
        key=norm(option,skill=='reading')
        if key not in seen:selected.append(option);seen.add(key)
        if len(selected)==3:break
    options=selected+[correct]
    random.shuffle(options)
    return options if len(options)==4 else []

def reading_distractors(reading,pool):
    """Create close kana alternatives without changing the stored reading."""
    reading=unicodedata.normalize('NFKC',reading)
    variants=[]
    def add(value):
        value=unicodedata.normalize('NFKC',value)
        if value and value!=reading and re.fullmatch(r'[ぁ-ゟー]+',value) and value not in variants:
            variants.append(value)
    pairs=(('か','が'),('き','ぎ'),('く','ぐ'),('け','げ'),('こ','ご'),
           ('さ','ざ'),('し','じ'),('す','ず'),('せ','ぜ'),('そ','ぞ'),
           ('た','だ'),('ち','ぢ'),('つ','づ'),('て','で'),('と','ど'),
           ('は','ば'),('ひ','び'),('ふ','ぶ'),('へ','べ'),('ほ','ぼ'))
    for i,ch in enumerate(reading):
        for left,right in pairs:
            if ch==left:add(reading[:i]+right+reading[i+1:])
            elif ch==right:add(reading[:i]+left+reading[i+1:])
    for i,ch in enumerate(reading):
        if ch=='っ':add(reading[:i]+reading[i+1:])
        elif ch in 'かきくけこさしすせそたちつてとはひふへほ':add(reading[:i]+'っ'+reading[i:])
    for before,after in (('おう','おお'),('おお','おう'),('えい','ええ'),('ええ','えい'),
                         ('うう','う'),('う','うう'),('いい','い'),('い','いい')):
        start=0
        while True:
            pos=reading.find(before,start)
            if pos<0:break
            add(reading[:pos]+after+reading[pos+len(before):]);start=pos+1
    contracted={'ゃ':'や','ゅ':'ゆ','ょ':'よ','や':'ゃ','ゆ':'ゅ','よ':'ょ'}
    for i,ch in enumerate(reading):
        if ch in contracted:add(reading[:i]+contracted[ch]+reading[i+1:])
    candidates=[c['reading'] for c in pool if c.get('kind')=='vocab' and c.get('reading')!=reading]
    key=lambda value:(abs(len(value)-len(reading)), sum(a!=b for a,b in zip(value,reading)))
    for value in sorted(set(candidates),key=key):
        if len(value)>=2 and abs(len(value)-len(reading))<=2:add(value)
        if len(variants)>=3:break
    return variants[:3]

def reading_options(card,pool):
    correct=card['reading']
    accepted={norm(x,True) for x in [correct]+card.get('reading_aliases',[])}
    options=[x for x in reading_distractors(correct,pool) if norm(x,True) not in accepted]
    if len(options)<3:
        fallback=[c['reading'] for c in pool if c.get('kind')=='vocab'
                   and c['id']!=card['id'] and norm(c['reading'],True) not in accepted]
        random.shuffle(fallback)
        for value in fallback:
            if norm(value,True) not in {norm(x,True) for x in options}:
                options.append(value)
            if len(options)==3:break
    if len(options)<3:return []
    options=options[:3]+[correct]
    random.shuffle(options)
    return options

def question(card,skill,allpool,p):
    phase=p.get('phase','choice')
    if skill=='reading':
        opts=reading_options(card,allpool) if phase=='choice' else []
    else:
        opts=choice_options(card,skill,allpool) if phase=='choice' else []
    mode='choice' if opts and phase=='choice' else 'write'
    prompt=card['meaning'] if skill=='structure' else card['term']
    question_text=('Cách đọc đúng là gì?' if skill=='reading' else
                   'Từ này có nghĩa là gì?' if skill=='meaning' else
                   'Cấu trúc tiếng Nhật tương ứng là gì?')
    return {'card_id':card['id'],'skill':skill,'mode':mode,'options':opts,
            'prompt':prompt,'question':question_text,'kind':card['kind'],'tier':card['tier'],
            'topic':card['topic'],'phase':phase,'streak':p.get('streak',0)}

def session(settings):
    batch_size=10
    with connect() as c:
        pool=all_cards(c); ps={(x['card_id'],x['skill']):x for x in progress_rows(c)}
    excluded={x for x in str(settings.get('exclude','')).split(',') if x}
    current_time=now()
    candidates=[];fallback=[]
    for card in pool:
        skills=card_skills(card)
        if skills and all(ps.get((card['id'],s),{}).get('mastered',0) for s in skills):continue
        states=[ps.get((card['id'],skill),{}) for skill in skills]
        due=any(p and p.get('due') and dt.datetime.fromisoformat(p['due'])<=current_time for p in states)
        failed=any(int(p.get('errors',0))>0 for p in states)
        is_new=all(not p for p in states)
        priority=0 if due else 1 if failed else 2 if is_new else 3
        item=(random.random(),card,states)
        (fallback if card['id'] in excluded else candidates).append((priority,item))
    def candidate_key(entry):
        priority,item=entry
        card=item[1]
        official_rank=0 if priority==2 and card.get('source_type')=='official_workbook' else 1
        return priority,official_rank,item[0]
    candidates.sort(key=candidate_key)
    fallback.sort(key=candidate_key)
    selected=[item for _,item in candidates[:batch_size]]
    if len(selected)<batch_size:
        selected.extend(item for _,item in fallback[:batch_size-len(selected)])
    selected=selected[:batch_size]
    kinds={card['kind'] for _,card,_ in selected}
    if len(kinds)==1:
        replacement=next((item for _,item in candidates[batch_size:]+fallback
                          if item[1]['kind'] not in kinds),None)
        if replacement:
            selected[-1]=replacement
    grouped={}
    for _,card,states in selected:
        grouped[card['id']]={skill:ps.get((card['id'],skill),{}) for skill in card_skills(card)
                             if not ps.get((card['id'],skill),{}).get('mastered',0)}
    groups=[]
    by_id={card['id']:card for card in pool}
    for card_index,(cid,skills) in enumerate(grouped.items(),1):
        card=by_id[cid]
        qs=[]
        for skill in card_skills(card):
            if skill in skills:
                q=question(card,skill,pool,skills[skill])
                q['group_id']=cid
                q['group_step']=len(qs)+1
                q['group_total']=len(skills)
                q['card_index']=card_index
                q['card_total']=len(grouped)
                qs.append(q)
        if qs:groups.append(qs)
    random.shuffle(groups)
    for card_index,group in enumerate(groups,1):
        for q in group:q['card_index']=card_index
    result=[q for group in groups for q in group]
    due_count=sum(1 for priority,_ in candidates if priority==0)
    return {'queue':result,'cards':len(groups),'due':due_count}

def ready_to_master(c,card):
    ps={r['skill']:dict(r) for r in c.execute('SELECT * FROM progress WHERE card_id=?',(card['id'],))}
    return all(s in ps and ps[s]['phase']=='ready' for s in card_skills(card))

def submit_answer(data):
    cid=str(data.get('card_id',''));sk=str(data.get('skill',''));eid=str(data.get('event_id',''))
    if not eid or len(eid)>100 or len(cid)>130:raise ValueError('ID không hợp lệ')
    with LOCK,connect() as c:
        old=c.execute('SELECT body FROM events WHERE id=?',(eid,)).fetchone()
        if old:return json.loads(old['body'])
        row=c.execute('SELECT body FROM cards WHERE id=?',(cid,)).fetchone()
        if not row:raise ValueError('Không tìm thấy từ')
        card=json.loads(row['body'])
        if sk not in card_skills(card):raise ValueError('Kỹ năng không hợp lệ')
        p=c.execute('SELECT * FROM progress WHERE card_id=? AND skill=?',(cid,sk)).fetchone()
        p=dict(p) if p else {}
        if p.get('mastered',0):raise ValueError('Từ này đã được đánh dấu thuộc')
        mode=p.get('phase','choice')
        aliases=[target(card,sk)]+card.get(sk+'_aliases',[])
        typed=str(data.get('answer',''))
        correct=not data.get('give_up',False) and norm(typed,sk=='reading') in {norm(a,sk=='reading') for a in aliases}
        # Early review does not add to streak or shift the schedule, unless the previous answer was wrong.
        due_old=dt.datetime.fromisoformat(p['due']) if p.get('due') else None
        eligible=(due_old is None or due_old<=now()) and p.get('last_day')!=today()
        streak=int(p.get('streak',0));success=int(p.get('successes',0));errors=int(p.get('errors',0));phase=mode
        if not correct:
            errors+=1;streak=0;due=now()+dt.timedelta(minutes=10)
            if mode=='ready':phase='write'
        elif eligible:
            success+=1;streak+=1
            if mode=='choice':
                if streak>=CHOICE_GOAL:
                    phase='write';streak=0;days=1
                else:
                    days=CHOICE_DELAYS[streak-1]
            elif mode=='write':
                if streak>=WRITE_GOAL:
                    phase='ready';streak=WRITE_GOAL;days=READY_DELAY
                else:
                    days=WRITE_DELAYS[streak-1]
            else:
                phase='ready';streak=WRITE_GOAL;days=READY_DELAY
            due=now()+dt.timedelta(days=days)
        else:
            due=due_old or now()+dt.timedelta(days=1)
        prev_last=p.get('last_day')
        last=today() if correct and eligible else prev_last
        values=(min(success,7),due.isoformat(),last,success,errors,phase,streak,0,
                'write' if mode=='write' else 'choice',cid,sk)
        updated=c.execute('''UPDATE progress SET stage=?,due=?,last_day=?,successes=?,
           errors=?,phase=?,streak=?,mastered=?,last_mode=? WHERE card_id=? AND skill=?''',
           values).rowcount
        if not updated:
            c.execute('''INSERT INTO progress(card_id,skill,stage,due,last_day,successes,errors,phase,streak,mastered,last_mode)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
               (cid,sk,*values[:9]))
        ready=ready_to_master(c,card)
        r={'correct':correct,'card':card,'expected':target(card,sk),'accepted':aliases,'skill':sk,
           'phase':phase,'streak':streak,'ready_to_master':ready,'due':due.isoformat(),'event_id':eid,
           'answer':typed,'card_id':cid,'eligible':eligible}
        c.execute('INSERT INTO events VALUES (?,?,?)',(eid,now().isoformat(),json.dumps(r,ensure_ascii=False)))
        return r

def set_mastered(data):
    cid=data.get('card_id');flag=bool(data.get('mastered'))
    with LOCK,connect() as c:
        row=c.execute('SELECT body FROM cards WHERE id=?',(cid,)).fetchone()
        if not row:raise ValueError('Không tìm thấy từ')
        card=json.loads(row['body'])
        if flag and not ready_to_master(c,card):raise ValueError('Cần hoàn thành cả cách đọc và nghĩa trước khi đánh dấu thuộc')
        for sk in card_skills(card):
            c.execute('UPDATE progress SET mastered=? WHERE card_id=? AND skill=?',(int(flag),cid,sk))
        return {'ok':True,'mastered':flag}

def import_cards(rows):
    if not isinstance(rows,list) or not rows:raise ValueError('Chưa có thẻ để nhập')
    if len(rows)>15000:raise ValueError('Một lần tối đa 15.000 thẻ')
    for card in rows:validate_card(card)
    added=updated=reset=0
    invalidate=False
    with LOCK,connect() as c:
        backup_id=online.backup(sys.modules[__name__],c,'before-import')
        existing={x['id']:x for x in all_cards(c)}
        identities={(unicodedata.normalize('NFKC',x['term']).strip(),norm(x['reading'],True),x['kind']):x['id'] for x in existing.values()}
        seen=set()
        for card in rows:
            if card['id'] in seen:raise ValueError('ID trùng trong file nhập')
            seen.add(card['id'])
            identity=(unicodedata.normalize('NFKC',card['term']).strip(),norm(card['reading'],True),card['kind'])
            if identity in identities and identities[identity]!=card['id']:
                raise ValueError('Thẻ đã tồn tại với ID '+identities[identity]+'. Hãy dùng ID đó.')
            identities[identity]=card['id']
        for card in rows:
            body=json.dumps(card,ensure_ascii=False)
            old=c.execute('SELECT body FROM cards WHERE id=?',(card['id'],)).fetchone()
            if old:
                prev=json.loads(old['body'])
                if prev!=card:
                    # A changed answer invalidates only the affected skill's progress.
                    for sk in set(card_skills(prev)+card_skills(card)):
                        if sk not in card_skills(card) or target(prev,sk)!=target(card,sk):
                            c.execute('INSERT INTO import_log VALUES (?,?,?)',(str(uuid.uuid4()),now().isoformat(),json.dumps({'card_id':card['id'],'skill':sk,'old':prev,'new':card,'previous_progress':[dict(p) for p in c.execute('SELECT * FROM progress WHERE card_id=? AND skill=?',(card['id'],sk))]},ensure_ascii=False)))
                            c.execute('DELETE FROM progress WHERE card_id=? AND skill=?',(card['id'],sk));reset+=1;invalidate=True
                    c.execute('UPDATE cards SET body=? WHERE id=?',(body,card['id']));updated+=1
            else:
                c.execute('INSERT INTO cards VALUES (?,?)',(card['id'],body));added+=1
        if invalidate:
            saved=online.get_session(sys.modules[__name__],c)
            online.save_session(c,saved['revision'],None)
    return {'ok':True,'added':added,'updated':updated,'reset_skills':reset,'backup_id':backup_id}

def enrich_dictionary():
    # Invoked only by an explicit local user click. This may fetch a ZIP once,
    # and subsequent runs use the cached copy without requiring Internet.
    from dictionary_enrichment import dictionary_cards
    with connect() as c:existing=all_cards(c)
    additions,stats=dictionary_cards(existing)
    outcome=import_cards(additions) if additions else {'added':0,'updated':0,'reset_skills':0}
    return {'ok':True,'stats':stats,**outcome}

def import_community_soumatome():
    """Optional internet source, imported ONLY when the user clicks a button."""
    from soumatome_parts_import import import_35_parts
    with connect() as c:existing=all_cards(c)
    additions,stats=import_35_parts(existing)
    imported=import_cards(additions) if additions else {'added':0,'updated':0,'reset_skills':0}
    return {'ok':True,'source':stats,**imported}

def audit_source_pages():
    from source_coverage import coverage
    with connect() as c: records=all_cards(c)
    summary,_=coverage(records,export=True)
    return summary


def inspect_source_page(query):
    from source_coverage import get_page
    return get_page(query.get('book',''),int(query.get('page','1')))


def import_all_sources():
    """One-click import. Never report success if even one source fails.

    Both sources are optional online data, not proof of completeness of PDF.
    Preserve progress and return accurate per-source outcomes.
    """
    successes={};errors={}
    for key,fn in [('soumatome_35_parts',import_community_soumatome),
                   ('japanese_vietnamese_dictionary',enrich_dictionary)]:
        try:successes[key]=fn()
        except Exception as e:errors[key]=str(e)
    result=audit_source_pages()
    return {'ok':not bool(errors),'imports':successes,'errors':errors,'coverage':result}


def search_books(query):
    from source_coverage import search_book_ocr
    return search_book_ocr(query)


def export_data():
    with connect() as c:
        return {'format':'kotoba-v2','exported':now().isoformat(),'cards':all_cards(c),
                'progress':progress_rows(c),'events':[dict(r) for r in c.execute('SELECT * FROM events')],
                'study':online.get_session(sys.modules[__name__],c),
                'settings':[dict(r) for r in c.execute('SELECT * FROM settings')]}

def restore(data):
    if data.get('format') not in ('kotoba-v2','jlpt-local-v1'):raise ValueError('Không đúng định dạng sao lưu')
    for card in data.get('cards',[]):validate_card(card)
    ids={x['id'] for x in data['cards']};checked=[]
    for p in data.get('progress',[]):
        if p['card_id'] not in ids or p['skill'] not in ('reading','meaning','structure') or not 0<=p['stage']<=7:
            raise ValueError('Tiến trình không hợp lệ')
        if p['due']:dt.datetime.fromisoformat(p['due'])
        p={**{'phase':'choice','streak':0,'mastered':0,'last_mode':None},**p}
        if p['phase'] not in ('choice','write','ready'):raise ValueError('Phase không hợp lệ')
        checked.append(p)
    with LOCK,connect() as c:
        online.backup(sys.modules[__name__],c,'before-restore')
        for table in ('cards','progress','events','settings'):c.execute('DELETE FROM '+table)
        for card in data['cards']:c.execute('INSERT INTO cards VALUES (?,?)',(card['id'],json.dumps(card,ensure_ascii=False)))
        for p in checked:
            fields=['card_id','skill','stage','due','last_day','successes','errors','phase','streak','mastered','last_mode']
            c.execute('INSERT INTO progress VALUES ('+','.join('?'*len(fields))+')',tuple(p.get(k) for k in fields))
        for e in data.get('events',[]):c.execute('INSERT INTO events VALUES (?,?,?)',(e['id'],e['created'],e['body']))
        for setting in data.get('settings',[]):c.execute('INSERT INTO settings VALUES (?,?)',(setting['key'],setting['value']))
        saved=online.get_session(sys.modules[__name__],c)
        online.save_session(c,saved['revision'],data.get('study',{}).get('snapshot'))
        seed_cards(c)
    return {'ok':True}

BOOK_PDFS={'nguphap':'nguphap.pdf','kanji':'kanji.pdf','dochien':'dochien.pdf','tuvung':'tuvung.pdf'}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,data,status=200,mime='application/json; charset=utf-8'):
        raw=json.dumps(data,ensure_ascii=False).encode() if mime.startswith('application/json') else data
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','same-origin')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if getattr(self,'response_cookie',None):self.send_header('Set-Cookie',self.response_cookie)
        self.end_headers();self.wfile.write(raw)
    def send_book_pdf(self,book):
        """Serve a user-supplied source PDF with HTTP byte ranges for Chrome's viewer."""
        filename=BOOK_PDFS.get(book)
        if not filename:return self.send({'error':'Không có sách'},404)
        path=ROOT/'source_books'/filename
        if not path.is_file():return self.send({'error':'File PDF không có trong bản app'},404)
        length=path.stat().st_size
        requested=self.headers.get('Range','')
        if requested:
            m=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
            if not m or not any(m.groups()):
                self.send_response(416);self.send_header('Content-Range',f'bytes */{length}');self.end_headers();return
            lo,hi=m.groups()
            if lo:
                start=int(lo);end=int(hi) if hi else length-1
            else:
                take=int(hi);start=max(0,length-take);end=length-1
            if start>=length or end<start:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{length}');self.end_headers();return
            end=min(end,length-1);status=206
        else:start,end,status=0,length-1,200
        self.send_response(status)
        self.send_header('Content-Type','application/pdf')
        self.send_header('Content-Length',str(end-start+1))
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Cache-Control','private, max-age=1800')
        self.send_header('X-Content-Type-Options','nosniff')
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{length}')
        self.end_headers()
        with path.open('rb') as stream:
            stream.seek(start);remaining=end-start+1
            while remaining:
                chunk=stream.read(min(1024*1024,remaining))
                if not chunk:break
                self.wfile.write(chunk);remaining-=len(chunk)

    def do_GET(self):
        try:
            u=urlparse(self.path);q={k:v[0] for k,v in parse_qs(u.query).items()}
            if u.path=='/healthz':return self.send({'ok':True})
            if u.path=='/api/auth':return self.send({'authenticated':online.authenticated(sys.modules[__name__],self.headers),'enabled':online.auth_enabled()})
            if (u.path.startswith('/api/') or u.path.startswith('/books/')) and not online.authenticated(sys.modules[__name__],self.headers):
                return self.send({'error':'Cần đăng nhập'},401)
            if u.path=='/api/backups':
                with connect() as c:return self.send([dict(r) for r in c.execute('SELECT id,created,reason FROM snapshots ORDER BY created DESC')])
            if u.path=='/api/backup':
                with connect() as c:
                    row=c.execute('SELECT body FROM snapshots WHERE id=?',(q.get('id',''),)).fetchone()
                    return self.send(json.loads(row['body']) if row else {'error':'Không tìm thấy'},200 if row else 404)
            if u.path.startswith('/books/') and u.path.endswith('.pdf'):
                return self.send_book_pdf(u.path.split('/')[-1][:-4])
            if u.path=='/api/state':
                with connect():return self.send(get_state())
            if u.path=='/api/session':return self.send(study_state())
            if u.path=='/api/export':return self.send(export_data())
            if u.path=='/api/coverage':return self.send(audit_source_pages())
            if u.path=='/api/book_page':return self.send(inspect_source_page(q))
            if u.path=='/api/search_books':return self.send(search_books(q.get('q','')))
            path=(ROOT/'web'/('index.html' if u.path=='/' else u.path.lstrip('/'))).resolve()
            if path.parent != (ROOT/'web').resolve() or not path.is_file():return self.send({'error':'Không tìm thấy'},404)
            return self.send(path.read_bytes(),mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'application/javascript; charset=utf-8','.webmanifest':'application/manifest+json','.png':'image/png','.svg':'image/svg+xml'}.get(path.suffix,'application/octet-stream'))
        except (ValueError,KeyError) as e:self.send({'error':str(e)},400)
        except Exception:self.send({'error':'Không kết nối được database. Hãy thử lại.'},503)
    def do_POST(self):
        try:
            origin=self.headers.get('Origin')
            if origin and urlparse(origin).netloc!=self.headers.get('Host'):return self.send({'error':'Origin không hợp lệ'},403)
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>60_000_000:raise ValueError('Dữ liệu quá lớn hoặc trống')
            data=json.loads(self.rfile.read(size))
            if self.path=='/api/login':
                token=online.login(sys.modules[__name__],data.get('password',''))
                if not token:return self.send({'error':'Sai mật khẩu hoặc tạm khóa 15 phút sau nhiều lần thử.'},401)
                self.response_cookie=online.cookie(token)
                return self.send({'ok':True})
            if not online.authenticated(sys.modules[__name__],self.headers):return self.send({'error':'Cần đăng nhập'},401)
            if self.path=='/api/logout':
                with connect() as c:c.execute('DELETE FROM auth_sessions WHERE token=?',(online.token_from(self.headers),))
                self.response_cookie=online.cookie('',True)
                return self.send({'ok':True})
            if self.path=='/api/adopt-session':res=online.adopt_legacy(sys.modules[__name__],data)
            elif self.path=='/api/session':res=online.transition(sys.modules[__name__],data)
            elif self.path=='/api/answer':res=online.answer(sys.modules[__name__],data)
            elif self.path=='/api/master':res=set_mastered(data)
            elif self.path=='/api/restore':res=restore(data)
            elif self.path=='/api/import':
                rows=data.get('cards',[])
                if 'csv' in data:
                    rows=list(csv.DictReader(io.StringIO(data['csv'].lstrip('\ufeff'))))
                    for card in rows:
                        for key in ('reading_aliases','meaning_aliases','structure_aliases','source_refs'):
                            if key in card:card[key]=json.loads(card[key]) if card[key] else []
                        if 'verified' in card:
                            if card['verified'].lower() not in ('true','false','1','0',''):raise ValueError('verified cần true hoặc false')
                            card['verified']=card['verified'].lower() in ('true','1')
                res=import_cards(rows)
            elif self.path=='/api/enrich':res=enrich_dictionary()
            elif self.path=='/api/import_soumatome':res=import_community_soumatome()
            elif self.path=='/api/import_all_sources':res=import_all_sources()
            else:return self.send({'error':'Không tìm thấy'},404)
            return self.send(res)
        except online.Conflict as e:self.send({'error':str(e)},409)
        except (ValueError,KeyError,TypeError,sqlite3.Error,URLError,TimeoutError,ConnectionError,OSError,zipfile.BadZipFile) as e:self.send({'error':str(e)},400)
        except Exception:self.send({'error':'Không kết nối được database. Gửi lại an toàn bằng cùng câu hỏi.'},503)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','8765')));args=parser.parse_args()
    init();server=ThreadingHTTPServer((os.environ.get('HOST','127.0.0.1'),args.port),Handler)
    print(f'Kotoba N3: http://localhost:{args.port} | Ctrl+C để tắt',flush=True)
    if os.environ.get('JLPT_NO_BROWSER')!='1' and os.environ.get('APP_ENV')!='production':webbrowser.open(f'http://localhost:{args.port}')
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
