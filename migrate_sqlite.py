#!/usr/bin/env python3
"""Read-only SQLite -> PostgreSQL import. Never overwrite newer online history."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import server
import online

FIELDS = {
    'cards': ['id','body'],
    'progress': ['card_id','skill','stage','due','last_day','successes','errors','phase','streak','mastered','last_mode'],
    'events': ['id','created','body'],
    'settings': ['key','value'],
    'study_session': ['id','revision','body'],
}

def migrate(source, backup_dir):
    if not os.environ.get('DATABASE_URL'): raise ValueError('Cần DATABASE_URL PostgreSQL đích')
    source = Path(source).resolve()
    if not source.is_file(): raise ValueError('Không tìm thấy SQLite nguồn')
    backup_dir=Path(backup_dir);backup_dir.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=backup_dir/('before-neon-'+stamp+'.sqlite3')
    # Online backup API includes committed WAL contents and leaves source untouched.
    src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);src.row_factory=sqlite3.Row
    try:
        with sqlite3.connect(backup) as dst: src.backup(dst)
    finally: src.close()
    backup.chmod(0o600)
    src=sqlite3.connect(backup);src.row_factory=sqlite3.Row
    try:
        tables={r['name'] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        data={}
        for table,fields in FIELDS.items():
            if table in tables:
                data[table]=[dict(r) for r in src.execute('SELECT * FROM '+table)]
            else: data[table]=[]
    finally: src.close()
    # Fingerprint logical rows, independent of physical SQLite page layout.
    canonical=json.dumps({k:sorted(v,key=lambda x:json.dumps(x,sort_keys=True)) for k,v in data.items()},sort_keys=True,ensure_ascii=False)
    fingerprint=hashlib.sha256(canonical.encode()).hexdigest()
    defaults={'phase':'choice','streak':0,'mastered':0,'last_mode':None}
    with server.connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS cards(id TEXT PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS progress(card_id TEXT, skill TEXT, stage INTEGER DEFAULT 0,
        due TEXT,last_day TEXT,successes INTEGER DEFAULT 0,errors INTEGER DEFAULT 0,
        phase TEXT NOT NULL DEFAULT 'choice',streak INTEGER NOT NULL DEFAULT 0,
        mastered INTEGER NOT NULL DEFAULT 0,last_mode TEXT,PRIMARY KEY(card_id,skill));
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,created TEXT,body TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);''')
        c.executescript(online.SCHEMA)
        if c.execute('SELECT id FROM migrations WHERE id=?',(fingerprint,)).fetchone():
            return {'already_migrated':True,'backup':str(backup)}
        # A nonempty target can contain post-migration work. Refuse to merge it.
        if any(c.execute('SELECT 1 FROM '+t+' LIMIT 1').fetchone() for t in ('progress','events','study_session','migrations')):
            raise ValueError('Database đích đã có tiến trình. Không ghi đè; dùng Neon branch/database trống.')
        online.backup(server,c,'before-sqlite-migration')
        # Seed-only deployments may exist; source card content has priority.
        for table,fields in FIELDS.items():
            normalized=[]
            for raw in data[table]:
                row={**defaults,**raw} if table=='progress' else raw
                if table=='cards':server.validate_card(json.loads(row['body']))
                for key in ('due','created'):
                    if row.get(key):
                        value=dt.datetime.fromisoformat(row[key])
                        if value.tzinfo is None:raise ValueError('Ngày giờ không có timezone: '+table+'.'+key)
                        row[key]=value.astimezone(dt.timezone.utc).isoformat()
                if table=='progress' and 'phase' not in raw and row.get('stage',0)>=3 and row.get('successes',0)>=3:
                    row['phase']='write'
                conflict='id' if table not in ('progress','settings') else 'card_id,skill' if table=='progress' else 'key'
                update=','.join(f+'=excluded.'+f for f in fields if f not in conflict.split(','))
                normalized.append(tuple(row.get(f) for f in fields))
            for offset in range(0,len(normalized),250):
                batch=normalized[offset:offset+250]
                c.execute('INSERT INTO '+table+' ('+','.join(fields)+') VALUES '+
                          ','.join('('+','.join('?' for _ in fields)+')' for _ in batch)+
                          ' ON CONFLICT('+conflict+') DO UPDATE SET '+update,
                          tuple(value for row in batch for value in row))
        # Validate each source field as well as counts before commit.
        for table,fields in FIELDS.items():
            actual=[dict(r) for r in c.execute('SELECT * FROM '+table)]
            if table!='cards' and len(actual)!=len(data[table]):raise ValueError('Sai số bản ghi '+table)
            primary=['card_id','skill'] if table=='progress' else ['key'] if table=='settings' else ['id']
            index={tuple(row[k] for k in primary):row for row in actual}
            for raw in data[table]:
                expected={**defaults,**raw} if table=='progress' else dict(raw)
                if table=='progress' and 'phase' not in raw and raw.get('stage',0)>=3 and raw.get('successes',0)>=3:expected['phase']='write'
                for key in ('due','created'):
                    if expected.get(key):expected[key]=dt.datetime.fromisoformat(expected[key]).astimezone(dt.timezone.utc).isoformat()
                target=index[tuple(expected[k] for k in primary)]
                if any(target[k]!=expected.get(k) for k in fields):raise ValueError('Nội dung không khớp '+table)
        c.execute('INSERT INTO migrations VALUES (?,?)',(fingerprint,server.now().isoformat()))
    return {'already_migrated':False,'backup':str(backup),'counts':{k:len(v) for k,v in data.items()}}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',default='progress.sqlite3')
    parser.add_argument('--backup-dir',default='backups')
    args=parser.parse_args()
    try: print(json.dumps(migrate(args.source,args.backup_dir),ensure_ascii=False,indent=2))
    except Exception as e:
        # Do not leak database URLs from driver exception messages.
        if isinstance(e,ValueError):parser.exit(1,str(e)+'\n')
        parser.exit(1,'Migration thất bại; transaction đã rollback. Kiểm tra kết nối PostgreSQL.\n')
