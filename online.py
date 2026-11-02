"""Single-user authentication and authoritative, versioned study sessions."""
import datetime as dt
import hashlib
import json
import os
import secrets
from http.cookies import SimpleCookie
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

class Conflict(ValueError): pass

SCHEMA = '''
CREATE TABLE IF NOT EXISTS study_session(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS auth_sessions(token TEXT PRIMARY KEY, expires TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS login_guard(id TEXT PRIMARY KEY, failures INTEGER NOT NULL, until_time TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY, created TEXT NOT NULL, reason TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS import_log(id TEXT PRIMARY KEY, created TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS migrations(id TEXT PRIMARY KEY, created TEXT NOT NULL);
'''

def auth_required(): return os.environ.get('APP_AUTH_REQUIRED', '0') != '0'

def validate_config():
    production = os.environ.get('APP_ENV') == 'production' or os.environ.get('RENDER') == 'true'
    password_hash = os.environ.get('APP_PASSWORD_HASH', '')
    if production and (not os.environ.get('DATABASE_URL') or (auth_required() and (not password_hash or os.environ.get('COOKIE_SECURE', '1') != '1'))):
        raise RuntimeError('Production requires DATABASE_URL, APP_PASSWORD_HASH and secure cookies')
    if auth_required() and password_hash:
        PasswordHasher().check_needs_rehash(password_hash)  # validate format; never log it

def auth_enabled(): return auth_required() and bool(os.environ.get('APP_PASSWORD_HASH'))
def cookie_name(): return '__Host-kotoba' if os.environ.get('COOKIE_SECURE', '1') == '1' else 'kotoba_local'
def token_from(headers):
    try:
        cookie = SimpleCookie(); cookie.load(headers.get('Cookie', ''))
        value = cookie.get(cookie_name())
        return hashlib.sha256(value.value.encode()).hexdigest() if value else ''
    except Exception: return ''

def authenticated(app, headers):
    if not auth_required(): return True
    if not auth_enabled(): return os.environ.get('APP_ENV') != 'production' and os.environ.get('RENDER') != 'true'
    with app.connect() as c:
        return c.execute('SELECT token FROM auth_sessions WHERE token=? AND expires>?',
                         (token_from(headers), app.now().isoformat())).fetchone() is not None

def login(app, password):
    if not auth_enabled(): raise ValueError('Chưa cấu hình mật khẩu')
    if not isinstance(password, str) or len(password) > 1024: raise ValueError('Mật khẩu không hợp lệ')
    with app.connect() as c:
        guard = c.execute("SELECT * FROM login_guard WHERE id='owner'").fetchone()
        if guard and guard['failures'] >= 10 and guard['until_time'] > app.now().isoformat():
            return None
        try: valid = PasswordHasher().verify(os.environ['APP_PASSWORD_HASH'], password)
        except (VerificationError, InvalidHashError): valid = False
        if not valid:
            failures = guard['failures'] + 1 if guard and guard['until_time'] > app.now().isoformat() else 1
            c.execute("DELETE FROM login_guard WHERE id='owner'")
            c.execute('INSERT INTO login_guard VALUES (?,?,?)', ('owner', failures, (app.now()+dt.timedelta(minutes=15)).isoformat()))
            return None
        c.execute("DELETE FROM login_guard WHERE id='owner'")
        c.execute('DELETE FROM auth_sessions WHERE expires<=?', (app.now().isoformat(),))
        token = secrets.token_urlsafe(32)
        c.execute('INSERT INTO auth_sessions VALUES (?,?)',
                  (hashlib.sha256(token.encode()).hexdigest(), (app.now()+dt.timedelta(days=30)).isoformat()))
        return token

def cookie(value, logout=False):
    return (f'{cookie_name()}={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={0 if logout else 2592000}'
            + ('; Secure' if os.environ.get('COOKIE_SECURE', '1') == '1' else ''))

def get_session(app, c):
    row = c.execute("SELECT * FROM study_session WHERE id='owner'").fetchone()
    return {'revision': row['revision'], 'snapshot': json.loads(row['body'])} if row else {'revision': 0, 'snapshot': None}

def save_session(c, revision, snapshot):
    c.execute("DELETE FROM study_session WHERE id='owner'")
    c.execute('INSERT INTO study_session VALUES (?,?,?)', ('owner', revision+1, json.dumps(snapshot, ensure_ascii=False)))
    return {'revision': revision+1, 'snapshot': snapshot}

def assign_current(s):
    s['current'] = s['queue'].pop(0) if s['queue'] else None
    if s['current']: s['current']['event_id'] = secrets.token_urlsafe(24)
    else: s['finished'] = True

def transition(app, data):
    with app.LOCK, app.connect() as c:
        saved = get_session(app,c)
        if data.get('revision') != saved['revision']: raise Conflict('Tiến trình đã đổi trên thiết bị khác. Đã tải lại; hãy tiếp tục từ câu hiện tại.')
        s = saved['snapshot']; action = data.get('action')
        if action == 'start':
            if s and not s.get('finished'): return saved
            previous = s.get('sessionSeen', []) if s else []
            batch = app.session({'exclude': ','.join(previous)})
            s = dict(queue=batch['queue'], total=batch['cards'], done=0, correct=0,
                     completedCards=0, groupResults=[], sessionSeen=list(dict.fromkeys(previous+[q['card_id'] for q in batch['queue']]))[-15000:])
            assign_current(s)
        elif action == 'next':
            if not s or s.get('finished'): return saved
            if not s['current'].get('feedback'): raise ValueError('Cần trả lời câu hiện tại')
            s['groupResults'] = []; assign_current(s)
        else: raise ValueError('Thao tác không hợp lệ')
        return save_session(c, saved['revision'], s)

def answer(app, data):
    with app.LOCK, app.connect() as c:
        saved = get_session(app,c)
        # Retry after lost response returns current state, never applies again.
        old = c.execute('SELECT body FROM events WHERE id=?', (str(data.get('event_id','')),)).fetchone()
        if old: return {**saved, 'result': json.loads(old['body'])}
        if data.get('revision') != saved['revision']: raise Conflict('Tiến trình đã đổi trên thiết bị khác. Đã tải lại; hãy tiếp tục từ câu hiện tại.')
        s = saved['snapshot']; q = s.get('current') if s else None
        if not q or q.get('feedback') or any(data.get(k)!=q.get(k) for k in ('event_id','card_id','skill')):
            raise Conflict('Câu hỏi đã thay đổi. Hãy tải lại lượt học.')
        # The event was checked above under this same transaction's advisory lock.
        r = app.submit_answer(data, _event_checked=True)
        s['done'] += 1; s['correct'] += int(r['correct'])
        results = s['groupResults']
        while len(results) < q['group_step']: results.append(None)
        results[q['group_step']-1] = r
        retry = None
        if not r['correct']:
            if sum(x['card_id']==q['card_id'] and x['skill']==q['skill'] and x.get('retry',False) for x in s['queue']) < 2:
                retry = {k:v for k,v in q.items() if k not in ('event_id','feedback')}; retry['retry'] = True
        if q['group_step'] < q['group_total'] and s['queue'] and s['queue'][0]['group_id']==q['group_id']:
            if retry: s['queue'].insert(1,retry)
            assign_current(s)
        else:
            if not q.get('retry'):s['completedCards'] += 1
            if retry: s['queue'].insert(min(4,len(s['queue'])),retry)
            q['feedback'] = r
        return {**save_session(c,saved['revision'],s), 'result':r}

def backup(app, c, reason):
    snapshot = app.export_data()
    ident = secrets.token_urlsafe(18)
    c.execute('INSERT INTO snapshots VALUES (?,?,?,?)',
              (ident, app.now().isoformat(), reason, json.dumps(snapshot, ensure_ascii=False)))
    # Bounded automatic backups; downloadable export is the long-term archive.
    rows = list(c.execute('SELECT id FROM snapshots ORDER BY created DESC'))
    for row in rows[5:]: c.execute('DELETE FROM snapshots WHERE id=?', (row['id'],))
    return ident

if __name__ == '__main__':
    import getpass
    password = getpass.getpass('Mật khẩu Kotoba (ít nhất 12 ký tự): ')
    if len(password) < 12: raise SystemExit('Cần ít nhất 12 ký tự')
    print(PasswordHasher().hash(password))

def adopt_legacy(app, data):
    """One-time transfer from the original browser, without replacing server work."""
    with app.LOCK, app.connect() as c:
        saved=get_session(app,c)
        if saved['revision'] or saved['snapshot']:return saved
        s=data.get('snapshot')
        if not isinstance(s,dict):raise ValueError('Lượt học cũ không hợp lệ')
        pool={x['id']:x for x in app.all_cards(c)}
        items=s.get('queue',[])+([s['current']] if s.get('current') else [])
        if len(items)>500:raise ValueError('Lượt học cũ quá lớn')
        for q in items:
            if q.get('card_id') not in pool or q.get('skill') not in app.card_skills(pool[q['card_id']]):
                raise ValueError('Lượt học cũ chứa thẻ không hợp lệ')
        for key in ('total','done','correct','completedCards'):
            s[key]=int(s.get(key,0))
            if not 0<=s[key]<=10000:raise ValueError('Thống kê lượt học không hợp lệ')
        s.setdefault('groupResults',[]);s.setdefault('sessionSeen',[])
        q=s.get('current')
        if q and not q.get('feedback'):
            event=c.execute('SELECT body FROM events WHERE id=?',(q.get('event_id',''),)).fetchone()
            if event:
                r=json.loads(event['body']);q['feedback']=r
                while len(s['groupResults'])<q['group_step']:s['groupResults'].append(None)
                s['groupResults'][q['group_step']-1]=r
        return save_session(c,0,s)
