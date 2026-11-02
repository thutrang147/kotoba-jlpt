"""Durable sessions, concurrency, HTTP auth and PostgreSQL migration regression tests.
Run SQLite: python -m unittest -v tests.test_online
Run PostgreSQL: TEST_DATABASE_URL=... python -m unittest -v tests.test_online
Uses a temporary schema, never the public schema or personal SQLite.
"""
import concurrent.futures
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch
from argon2 import PasswordHasher
import server
import online
import migrate_sqlite

class OnlineTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{},clear=False);self.env.start()
        os.environ.pop('DATABASE_URL',None)
        os.environ.pop('APP_PASSWORD_HASH',None)
        os.environ['APP_ENV']='development';os.environ['COOKIE_SECURE']='0'
        self.tmp=tempfile.TemporaryDirectory();self.old_db=server.DB
        server.DB=Path(self.tmp.name)/'test.sqlite3'
        self.url=os.environ.get('TEST_DATABASE_URL')
        if self.url:
            import psycopg
            self.schema='test_'+uuid.uuid4().hex
            with psycopg.connect(self.url,autocommit=True) as c:c.execute('CREATE SCHEMA '+self.schema)
            # libpq conninfo retains source SSL options and appends a search_path.
            os.environ['DATABASE_URL']=psycopg.conninfo.make_conninfo(self.url,options='-c search_path='+self.schema)
        server.init()
        self.app=None
    def tearDown(self):
        if self.app:self.app.shutdown();self.app.server_close();self.thread.join()
        if self.url:
            import psycopg
            with psycopg.connect(self.url,autocommit=True) as c:c.execute('DROP SCHEMA '+self.schema+' CASCADE')
        server.DB=self.old_db;self.tmp.cleanup();self.env.stop()
    def start(self):return online.transition(server,{'action':'start','revision':server.study_state()['revision']})
    def test_nested_transaction_rolls_back_and_next_request_can_commit(self):
        with self.assertRaises(ValueError):
            with server.connect() as outer:
                with server.connect() as inner:
                    self.assertIs(inner,outer)
                    inner.execute('INSERT INTO settings VALUES (?,?)',('rollback-test','discard'))
                raise ValueError('abort request')
        with server.connect() as c:
            self.assertIsNone(c.execute('SELECT value FROM settings WHERE key=?',('rollback-test',)).fetchone())
            c.execute('INSERT INTO settings VALUES (?,?)',('rollback-test','keep'))
        with server.connect() as c:
            self.assertEqual(c.execute('SELECT value FROM settings WHERE key=?',('rollback-test',)).fetchone()['value'],'keep')
    def answer(self,s,wrong=False):
        q=s['snapshot']['current']
        with server.connect() as c:card=json.loads(c.execute('SELECT body FROM cards WHERE id=?',(q['card_id'],)).fetchone()['body'])
        data={k:q[k] for k in ('card_id','skill','event_id')}
        data.update(revision=s['revision'],answer='__wrong__' if wrong else server.target(card,q['skill']))
        return online.answer(server,data),data
    def test_resume_after_restart(self):
        s=self.start();self.answer(s);before=server.export_data();server.init()
        self.assertEqual(server.export_data()['progress'],before['progress'])
        self.assertEqual(server.study_state(),before['study'])
    def test_two_devices_and_stale_answer(self):
        a=self.start();b=server.study_state();self.assertEqual(a,b)
        x,data=self.answer(a)
        self.assertEqual(server.study_state()['snapshot'],x['snapshot'])
        # Different event against an old question must not overwrite newer state.
        data['event_id']='different'
        with self.assertRaises(online.Conflict):online.answer(server,data)
        self.assertEqual(len(server.export_data()['events']),1)
    def test_concurrent_duplicate_answer(self):
        s=self.start();q=s['snapshot']['current']
        data={k:q[k] for k in ('card_id','skill','event_id')};data.update(revision=s['revision'],answer='wrong')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            rows=list(pool.map(lambda _:online.answer(server,data),range(2)))
        self.assertEqual(rows[0],rows[1]);self.assertEqual(len(server.export_data()['events']),1)
    def test_cross_worker_duplicate_answer(self):
        # Independent processes have separate Python LOCKs; DB must serialize them.
        import subprocess
        s=self.start();q=s['snapshot']['current']
        data={k:q[k] for k in ('card_id','skill','event_id')};data.update(revision=s['revision'],answer='wrong')
        env={**os.environ,'JLPT_DB':str(server.DB)}
        code='import json,online,server; online.answer(server,json.loads('+repr(json.dumps(data))+'))'
        import sys
        jobs=[subprocess.Popen([sys.executable,'-c',code],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
        for job in jobs:
            out,err=job.communicate(timeout=30);self.assertEqual(job.returncode,0,err.decode())
        self.assertEqual(len(server.export_data()['events']),1)
    def test_lost_response_retry_current_snapshot(self):
        s=self.start();x,data=self.answer(s)
        y=online.answer(server,data);self.assertEqual(x,y)
    def test_reading_meaning_independent_and_stats(self):
        card=next(x for x in server.get_state()['cards'] if x['term']=='台所')
        for sk,answer in [('reading',card['reading']),('meaning','__wrong__')]:
            server.submit_answer(dict(card_id=card['id'],skill=sk,answer=answer,event_id=str(uuid.uuid4())))
        p={x['skill']:x for x in server.export_data()['progress']}
        self.assertEqual(p['reading']['successes'],1);self.assertEqual(p['meaning']['errors'],1)
        self.assertEqual(server.get_state()['progress_stats']['started'],1)
    def test_import_preserves_metadata_progress_and_rejects_duplicate_identity(self):
        s=self.start();self.answer(s);before=server.export_data()
        card=next(c for c in before['cards'] if c['id']==before['progress'][0]['card_id'])
        server.import_cards([{**card,'note':'new note'}])
        self.assertEqual(server.export_data()['progress'],before['progress'])
        with self.assertRaises(ValueError):server.import_cards([{**card,'id':'new-id'}])
        self.assertEqual(len(server.export_data()['cards']),len(before['cards']))
        with server.connect() as c:self.assertTrue(c.execute('SELECT 1 FROM snapshots').fetchone())
    def test_import_answer_change_logs_before_reset(self):
        s=self.start();self.answer(s);before=server.export_data()
        p=before['progress'][0];card=next(c for c in before['cards'] if c['id']==p['card_id'])
        field='reading' if p['skill']=='reading' else 'term' if p['skill']=='structure' else 'meaning'
        server.import_cards([{**card,field:card[field]+'x'}])
        with server.connect() as c:
            entry=json.loads(c.execute('SELECT body FROM import_log').fetchone()['body'])
        self.assertEqual(entry['previous_progress'],[p])
        self.assertEqual(len(server.export_data()['events']),1)
    def test_restore_atomic_and_sessions_included(self):
        self.start();snapshot=server.export_data()
        self.answer(server.study_state());server.restore(snapshot)
        self.assertEqual(server.study_state()['snapshot'],snapshot['study']['snapshot'])
        self.assertEqual(server.export_data()['progress'],snapshot['progress'])
        bad={**snapshot,'events':[{'id':'dup','created':'x','body':'{}'}]*2}
        with self.assertRaises(Exception):server.restore(bad)
        self.assertEqual(server.export_data()['progress'],snapshot['progress'])
    def http_server(self):
        os.environ['APP_PASSWORD_HASH']=PasswordHasher().hash('test-password-long')
        self.app=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.thread=threading.Thread(target=self.app.serve_forever,daemon=True);self.thread.start()
    def request(self,path,body=None,cookie=None,origin=None):
        c=http.client.HTTPConnection('127.0.0.1',self.app.server_port)
        headers={'Content-Type':'application/json'}
        if cookie:headers['Cookie']=cookie
        if origin:headers['Origin']=origin
        c.request('GET' if body is None else 'POST',path,None if body is None else json.dumps(body),headers)
        r=c.getresponse();data=r.read();result=(r.status,dict(r.getheaders()),json.loads(data));c.close();return result
    def test_auth_protects_all_private_routes_and_logout(self):
        self.http_server()
        for path in ['/api/state','/api/session','/api/export','/api/backups','/api/backup?id=x','/api/coverage','/api/search_books?q=x']:
            self.assertEqual(self.request(path)[0],401,path)
        for path in ['/api/answer','/api/master','/api/restore','/api/import','/api/adopt-session','/api/enrich','/api/import_all_sources']:
            self.assertEqual(self.request(path,{})[0],401,path)
        self.assertEqual(self.request('/api/login',{'password':'wrong'})[0],401)
        status,headers,_=self.request('/api/login',{'password':'test-password-long'})
        self.assertEqual(status,200);cookie=headers['Set-Cookie']
        self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
        self.assertEqual(self.request('/api/state',cookie=cookie)[0],200)
        self.assertEqual(self.request('/api/logout',{},cookie=cookie,origin='https://evil.example')[0],403)
        self.assertEqual(self.request('/api/logout',{},cookie=cookie)[0],200)
        self.assertEqual(self.request('/api/state',cookie=cookie)[0],401)
    def test_csv_import_idempotent_and_authenticated(self):
        self.http_server()
        csv='id,term,reading,meaning,kind,tier,topic,verified\nmy-csv-1,試験専用,しけんせんよう,từ kiểm thử,vocab,extra,test,false\n'
        self.assertEqual(self.request('/api/import',{'csv':csv})[0],401)
        _,headers,_=self.request('/api/login',{'password':'test-password-long'})
        cookie=headers['Set-Cookie']
        status,_,body=self.request('/api/import',{'csv':csv},cookie)
        self.assertEqual(status,200);self.assertEqual(body['added'],1)
        self.assertEqual(self.request('/api/import',{'csv':csv},cookie)[2]['added'],0)
        card=next(c for c in server.export_data()['cards'] if c['id']=='my-csv-1')
        self.assertIs(card['verified'],False)
    def test_login_lockout_persists_restart(self):
        self.http_server()
        for _ in range(10):self.assertIsNone(online.login(server,'wrong'))
        server.init();self.assertIsNone(online.login(server,'test-password-long'))
    def test_production_fail_closed(self):
        with patch.dict(os.environ,{'APP_ENV':'production','COOKIE_SECURE':'1'}):
            with self.assertRaises(RuntimeError):online.validate_config()
            self.assertIn('; Secure',online.cookie('test'))
    @unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'),'requires temporary PostgreSQL')
    def test_sqlite_migration_exact_idempotent_and_refuses_new_source(self):
        pg_url=os.environ['DATABASE_URL']
        del os.environ['DATABASE_URL']
        server.init();self.start();self.answer(server.study_state())
        original=server.export_data();source=server.DB
        original_bytes=source.read_bytes()
        os.environ['DATABASE_URL']=pg_url
        # Drop empty destination app rows seeded in setUp; source progress is separate.
        first=migrate_sqlite.migrate(source,Path(self.tmp.name)/'backups')
        self.assertFalse(first['already_migrated'])
        migrated=server.export_data()
        for key in ('cards','progress','events','settings','study'):
            if key=='study':self.assertEqual(migrated[key],original[key])
            else:self.assertEqual(sorted(migrated[key],key=str),sorted(original[key],key=str))
        self.assertEqual(source.read_bytes(),original_bytes)
        self.assertTrue(migrate_sqlite.migrate(source,Path(self.tmp.name)/'backups')['already_migrated'])
        # A changed source must never replace online progress.
        del os.environ['DATABASE_URL']
        q=server.study_state()['snapshot']['current']
        server.submit_answer(dict(card_id=q['card_id'],skill=q['skill'],event_id=str(uuid.uuid4()),answer='wrong'))
        os.environ['DATABASE_URL']=pg_url
        with self.assertRaises(ValueError):migrate_sqlite.migrate(source,Path(self.tmp.name)/'backups')
        self.assertEqual(server.export_data()['events'],migrated['events'])

if __name__=='__main__':unittest.main()
