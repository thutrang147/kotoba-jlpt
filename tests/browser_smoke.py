"""Chrome smoke test against a disposable SQLite database, never personal data.
Requires: pip install playwright; installed Google Chrome, or PLAYWRIGHT_CHROMIUM.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from argon2 import PasswordHasher
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
NO_AUTH=os.environ.get('SMOKE_NO_AUTH')=='1'
with tempfile.TemporaryDirectory() as directory:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env={**os.environ,'JLPT_DB':directory+'/test.sqlite3','JLPT_NO_BROWSER':'1','COOKIE_SECURE':'0',
         'APP_ENV':'development','APP_PASSWORD_HASH':PasswordHasher().hash('test-browser-password')}
    env['APP_AUTH_REQUIRED']='0' if NO_AUTH else '1'
    # An explicit empty value prevents CLI dotenv loading the personal Neon URL.
    env['DATABASE_URL']=''
    process=subprocess.Popen([sys.executable,'server.py','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL)
    try:
        with sync_playwright() as p:
            executable=os.environ.get('PLAYWRIGHT_CHROMIUM','/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
            a=p.chromium.launch_persistent_context(directory+'/chrome-profile',executable_path=executable,headless=True,viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            browser=a.browser
            b=browser.new_context(viewport={'width':1280,'height':900})
            page=a.new_page();other=b.new_page();errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            url=f'http://127.0.0.1:{port}'
            for _ in range(100):
                try:
                    import urllib.request
                    urllib.request.urlopen(url+'/healthz');break
                except Exception:time.sleep(.1)
            def login(pg):
                pg.goto(url)
                if not NO_AUTH:
                    pg.locator('#password').fill('test-browser-password')
                    pg.locator('#loginForm button').click()
                pg.locator('#start').wait_for()
            login(page);login(other)
            page.locator('#start').click();page.locator('#answerArea').wait_for()
            for width in (320,390,430,1280):
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'overflow at {width}'
            page.set_viewport_size({'width':390,'height':844})
            (ROOT/'artifacts').mkdir(exist_ok=True)
            page.screenshot(path=str(ROOT/'artifacts/mobile-study.png'),full_page=True)
            first=page.evaluate('current.event_id')
            page.reload();page.locator('#start').click();page.locator('#answerArea').wait_for()
            assert page.evaluate('current.event_id')==first
            other.reload();other.locator('#start').click();other.locator('#answerArea').wait_for()
            assert other.evaluate('current.event_id')==first
            # Offline UI says unconfirmed; the server must have zero events.
            a.set_offline(True);page.locator('[data-choice]').first.click()
            page.wait_for_function("()=>document.querySelector('#notice').textContent.includes('Chưa xác nhận lưu')")
            a.set_offline(False)
            assert page.evaluate("api('/api/export').then(x=>x.events.length)")==0
            # Complete a whole batch through the real answer controls.
            for _ in range(50):
                if page.locator('#continue').count():break
                if page.locator('#next').count():
                    page.locator('#next').click();page.wait_for_timeout(80);continue
                page.wait_for_function('()=>!busy && (!!current||!!document.querySelector("#continue"))')
                if page.locator('#continue').count():break
                expected=page.evaluate("(()=>{const c=state.cards.find(c=>c.id===current.card_id);return current.skill==='reading'?c.reading:current.skill==='structure'?c.term:c.meaning;})()")
                if page.locator('#typed').count():
                    page.locator('#typed').fill(expected);page.locator('#typed').press('Enter')
                else:
                    index=page.evaluate('(value)=>current.options.indexOf(value)',expected)
                    assert index>=0
                    page.locator(f'[data-choice="{index}"]').click()
                page.wait_for_function('()=>!busy')
            if not page.locator('#continue').count():print(page.evaluate('({done,correct,completedCards,current,queue:queue.length,notice:document.querySelector("#notice").textContent})'),flush=True)
            page.locator('#continue').wait_for()
            assert page.evaluate('completedCards')==10
            assert page.evaluate("api('/api/export').then(x=>x.events.length)")>=10
            other.reload();other.locator('#start').wait_for()
            assert other.evaluate('state.progress_stats.started')==10
            # PWA metadata, SW registration and Chromium installability diagnostics.
            manifest=page.evaluate("fetch('/manifest.webmanifest').then(r=>r.json())")
            assert manifest['name']=='Kotoba JLPT N3'
            assert page.evaluate('navigator.serviceWorker.ready.then(x=>!!x.active)')
            diagnostics=page.context.new_cdp_session(page).send('Page.getInstallabilityErrors')
            assert not diagnostics['installabilityErrors'],diagnostics
            assert not errors,errors
            page.locator('#continue').click();page.locator('#answerArea').wait_for()
            assert page.evaluate('total')==10
            # Check split feedback with Reading right and Meaning wrong.
            for _ in range(25):
                page.wait_for_function('()=>!busy&&!!current')
                if page.evaluate('current.skill')=='reading':break
                if page.locator('#next').count():page.locator('#next').click();continue
                page.evaluate("()=>{const c=state.cards.find(c=>c.id===current.card_id);return submit(current.skill==='structure'?c.term:c.meaning);}")
            assert page.evaluate('current.skill')=='reading'
            page.evaluate("()=>submit(state.cards.find(c=>c.id===current.card_id).reading)")
            assert page.evaluate('current.skill')=='meaning'
            page.evaluate("()=>submit('__wrong__')")
            assert page.locator('.skill-result.is-correct').count()==1
            assert page.locator('.skill-result.is-wrong').count()==1
            page.screenshot(path=str(ROOT/'artifacts/mobile-feedback.png'),full_page=True)
            if NO_AUTH:
                assert not page.locator('#logout').is_visible()
                assert page.evaluate("fetch('/api/export').then(r=>r.status)")==200
            else:
                page.locator('#logout').click();page.locator('#password').wait_for()
                assert page.evaluate("fetch('/api/export').then(r=>r.status)")==401
            browser.close()
            print(json.dumps({'browser':'Chrome','widths':[320,390,430,1280],'batch_cards':10,'resume':True,
                              'two_contexts':True,'offline_no_answer_saved':True,'installability_errors':diagnostics['installabilityErrors'],
                              'javascript_errors':errors},indent=2))
    finally:
        process.terminate();process.wait(timeout=10)
