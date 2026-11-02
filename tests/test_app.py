"""Run: python3 -m unittest -v tests.test_app"""
import datetime as dt
import json
import tempfile
import unittest
import uuid
import zipfile
import dictionary_enrichment as d_enrich
from pathlib import Path
from unittest.mock import patch
import server

class KotobaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old_db=server.DB
        server.DB=Path(self.tmp.name)/'progress.sqlite3'
        server.init()
        self.card=next(x for x in server.get_state()['cards'] if x['term']=='台所')
    def tearDown(self):
        server.DB=self.old_db
        self.tmp.cleanup()
    def answer(self,skill,word,day=0,eid=None):
        moment=dt.datetime(2026,11,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=day)
        with patch.object(server,'now',lambda:moment),patch.object(server,'today',lambda:moment.date().isoformat()):
            return server.submit_answer({'card_id':self.card['id'],'skill':skill,'answer':word,'event_id':eid or str(uuid.uuid4())})
    def p(self,skill):
        with server.connect() as c:
            return dict(c.execute('SELECT * FROM progress WHERE card_id=? AND skill=?',(self.card['id'],skill)).fetchone())
    def test_input_contains_reading_and_meaning(self):
        q=server.session({'new':'15'})['queue'];self.assertTrue(q)
        for item in q:
            if item['mode']=='choice':
                with server.connect() as c:
                    row=c.execute('SELECT body FROM cards WHERE id=?',(item['card_id'],)).fetchone()
                card=json.loads(row['body']);self.assertIn(server.target(card,item['skill']),item['options']);self.assertEqual(len(item['options']),4)

    def test_kanji_vocabulary_questions_are_adjacent_reading_then_meaning(self):
        items=server.session({'new':'15'})['queue']
        pair=next(i for i in range(len(items)-1)
                  if items[i]['skill']=='reading' and items[i+1]['card_id']==items[i]['card_id'])
        self.assertEqual([items[pair]['skill'],items[pair+1]['skill']],
                         ['reading','meaning'])
        self.assertEqual(items[pair]['group_step'],1)
        self.assertEqual(items[pair+1]['group_step'],2)
        self.assertEqual(items[pair]['group_id'],items[pair+1]['group_id'])

    def test_session_has_ten_unique_cards_and_can_exclude_previous_batch(self):
        first=server.session({})
        first_ids=[q['card_id'] for q in first['queue']]
        self.assertEqual(first['cards'],10)
        self.assertEqual(len(set(first_ids)),10)
        self.assertEqual({q['card_index'] for q in first['queue']},set(range(1,11)))
        self.assertTrue(all(q['card_total']==10 for q in first['queue']))
        second=server.session({'exclude':','.join(first_ids)})
        second_ids=[q['card_id'] for q in second['queue']]
        self.assertEqual(second['cards'],10)
        self.assertTrue(set(first_ids).isdisjoint(set(second_ids)))

    def test_session_mixes_vocabulary_and_grammar(self):
        kinds={q['kind'] for q in server.session({})['queue']}
        self.assertEqual(kinds,{'vocab','grammar'})

    def test_new_session_prioritizes_official_workbook_cards(self):
        items=server.session({})
        official={c['id'] for c in server.get_state()['cards']
                  if c.get('source_type')=='official_workbook'}
        self.assertTrue(any(item['card_id'] in official for item in items['queue']))

    def test_reading_distractors_are_close_and_unique(self):
        with server.connect() as c:pool=server.all_cards(c)
        options=server.reading_options(self.card,pool)
        self.assertEqual(len(options),4)
        self.assertEqual(len({server.norm(x,True) for x in options}),4)
        self.assertIn(self.card['reading'],options)
        wrong=[x for x in options if x!=self.card['reading']]
        self.assertTrue(any('っ' in x for x in wrong) or
                        any(server.norm(x,True) != server.norm(self.card['reading'],True) for x in wrong))

    def test_reading_and_meaning_progress_are_independent(self):
        reading=self.answer('reading','だいどころ',0)
        meaning=self.answer('meaning','sai',0)
        self.assertTrue(reading['correct'])
        self.assertFalse(meaning['correct'])
        self.assertEqual(self.p('reading')['successes'],1)
        self.assertEqual(self.p('reading')['errors'],0)
        self.assertEqual(self.p('meaning')['successes'],0)
        self.assertEqual(self.p('meaning')['errors'],1)

    def test_progress_stats_count_each_card_once(self):
        stats=server.get_state()['progress_stats']
        self.assertEqual(stats['total'],len(server.get_state()['cards']))
        self.assertEqual(stats['unlearned']+stats['learning']+stats['ready']+stats['mastered'],stats['total'])
        self.answer('reading','だいどころ',0)
        self.answer('meaning','sai',0)
        stats=server.get_state()['progress_stats']
        self.assertEqual(stats['started'],1)
        self.assertEqual(stats['learning'],1)
        self.assertEqual(stats['unlearned']+stats['learning']+stats['ready']+stats['mastered'],stats['total'])

    def test_progress_stats_ready_and_mastered(self):
        for day in [0,2,5,6,10,18]:
            self.answer('reading','だいどころ',day)
            self.answer('meaning','nhà bếp',day)
        stats=server.get_state()['progress_stats']
        self.assertEqual(stats['ready'],1)
        self.assertEqual(stats['mastered'],0)
        server.set_mastered({'card_id':self.card['id'],'mastered':True})
        stats=server.get_state()['progress_stats']
        self.assertEqual(stats['mastered'],1)
        self.assertEqual(stats['ready'],0)
    def test_three_choice_then_three_write_separate_skills(self):
        for i in [0,2,5]:self.answer('reading','だいどころ',i)
        p=self.p('reading');self.assertEqual(p['phase'],'write');self.assertEqual(p['streak'],0)
        self.assertIsNone(self.p_if('meaning'))
        for i in [6,10,18]:self.answer('reading','だいどころ',i)
        p=self.p('reading');self.assertEqual(p['phase'],'ready');self.assertEqual(p['streak'],3)
        
        with server.connect() as c:self.assertFalse(server.ready_to_master(c,self.card))
        for i in [0,2,5,6,10,18]:self.answer('meaning','nhà bếp',i)
        with server.connect() as c:self.assertTrue(server.ready_to_master(c,self.card))
        self.assertTrue(server.set_mastered({'card_id':self.card['id'],'mastered':True})['mastered'])
        self.assertEqual(self.p('reading')['mastered'],1)
        self.assertEqual(self.p('meaning')['mastered'],1)
        server.set_mastered({'card_id':self.card['id'],'mastered':False})
        self.assertEqual(self.p('reading')['mastered'],0)
    def p_if(self,s):
        with server.connect() as c:
            row=c.execute('SELECT * FROM progress WHERE card_id=? AND skill=?',(self.card['id'],s)).fetchone()
            return dict(row) if row else None
    def test_same_day_and_early_review_do_not_advance(self):
        self.answer('reading','だいどころ',0)
        self.answer('reading','だいどころ',0)
        self.answer('reading','だいどころ',0)
        self.assertEqual(self.p('reading')['streak'],1)
        self.answer('reading','だいどころ',0)
        self.assertEqual(self.p('reading')['successes'],1)
    def test_error_resets_streak_and_prevents_mastering(self):
        for day in [0,2,5,6,10,18]:self.answer('reading','だいどころ',day)
        self.assertEqual(self.p('reading')['phase'],'ready')
        self.answer('reading','sai',19)
        self.assertEqual(self.p('reading')['phase'],'write')
        self.assertEqual(self.p('reading')['streak'],0)
        self.assertGreater(self.p('reading')['errors'],0)
    def test_duplicate_event_is_idempotent(self):
        eid=str(uuid.uuid4())
        a=self.answer('reading','だいどころ',0,eid)
        b=self.answer('reading','sai',0,eid)
        self.assertEqual(a,b)
        self.assertEqual(self.p('reading')['errors'],0)
    def test_cannot_master_before_both_skills_pass(self):
        with self.assertRaises(ValueError):server.set_mastered({'card_id':self.card['id'],'mastered':True})
    def test_scripted_backup_restore_and_import(self):
        self.answer('meaning','nhà bếp',0)
        snapshot=server.export_data()
        self.assertEqual(snapshot['format'],'kotoba-v2')
        added=dict(self.card,id='my-test-id',term='試験用の実現',reading='しけんようのじつげん',meaning='hiện thực hóa')
        r=server.import_cards([added]);self.assertEqual(r['added'],1)
        self.assertEqual(server.import_cards([added])['added'],0)
        edited={**self.card, 'note':'ghi chú mới'}
        self.assertEqual(server.import_cards([edited])['reset_skills'],0)
        self.assertIsNotNone(self.p_if('meaning'))
        changed={**self.card,'meaning':'bếp'}
        self.assertEqual(server.import_cards([changed])['reset_skills'],1)
        self.assertIsNone(self.p_if('meaning'))
        server.restore(snapshot)
        self.assertEqual(self.p('meaning')['successes'],1)
        self.assertEqual(server.get_state()['sources']['available_cards'],len(server.get_state()['cards']))
    def test_clean_card_pool_and_normalize(self):
        self.assertEqual(server.norm('デンシャ',True),'でんしゃ')
        self.assertNotEqual(server.norm('きょう',True),server.norm('きよ',True))
        self.assertEqual(server.norm('NHÀ  BẾP'),'nhà bếp')
        with server.connect() as c:pool=server.all_cards(c)
        opts=server.choice_options(self.card,'reading',pool)
        self.assertIn('だいどころ',opts)
        self.assertEqual(4,len(set(opts)))
    def test_large_seed_is_unique_and_all_card_skills_covered(self):
        data=server.get_state()['cards']
        self.assertGreaterEqual(len(data),3000)
        self.assertEqual(len({c['id'] for c in data}),len(data))
        self.assertEqual(len({(c['term'],c['reading'],c['kind']) for c in data}),len(data))
        for card in data:
            server.validate_card(card)
            self.assertTrue(card['reading'] and card['meaning'])
            self.assertIn(card['kind'],('vocab','grammar'))
        self.assertGreater(sum(c['kind']=='vocab' for c in data),2800)

    def test_official_workbook_additions_are_metadata_tagged_and_keep_homonyms(self):
        data=server.get_state()['cards']
        expected={
            ('首都','しゅと'),('大量','たいりょう'),('インタビュー','インタビュー'),
            ('主張','しゅちょう'),('からから','からから'),('貯める','ためる'),
            ('訳','わけ'),('訓練','くんれん'),('豆','まめ'),('波','なみ'),
            ('組む','くむ'),('イメージ','イメージ'),('囲む','かこむ'),
            ('姿勢','しせい'),('輝く','かがやく'),('余る','あまる'),
            ('沸騰','ふっとう'),('慰める','なぐさめる')}
        added={ (c['term'],c['reading']):c for c in data if c.get('source_type')=='official_workbook' }
        self.assertTrue(expected.issubset(added))
        for key in expected:
            card=added[key]
            self.assertEqual(card['exam_priority'],'high')
            self.assertIsNone(card['source_page'])
            self.assertFalse(card['verified'])
        self.assertTrue(any(c['term']=='ためる' and c['meaning']=='tích trữ' for c in data))
        self.assertTrue(any(c['term']=='くむ' and c['meaning']=='múc nước' for c in data))
    def test_seed_import_from_prior_version_without_reset(self):
        # Existing progress is stored separately from the cards table.
        self.answer('reading','だいどころ',0)
        old=self.p('reading')
        with server.connect() as conn:
            conn.execute('DELETE FROM cards WHERE id NOT IN (?,?)',(self.card['id'],'impossible'))
        server.init()
        self.assertEqual(self.p('reading')['successes'],old['successes'])
        self.assertGreaterEqual(len(server.get_state()['cards']),3000)
    def test_dictionary_enrichment_matches_ocr_with_vietnamese_only(self):
        path=Path(self.tmp.name)/'fixture.zip'
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('index.json',json.dumps({'format':3}))
            z.writestr('term_bank_1.json',json.dumps([
              ['入る','はいる','','',1,['to enter','đi vào'],1,''],
              ['つける','つける','','',1,['to attach','gắn vào'],2,''],
              ['最も','もっとも','','',1,['most','nhất'],3,''],
              ['限定','げんてい','','',1,['to limit'],4,'']]))
        with patch.object(d_enrich,'get_zip',lambda *args:path):
            new,stats=d_enrich.dictionary_cards([])
            terms={c['term']:c for c in new}
            self.assertEqual(terms['入る']['reading'],'はいる')
            self.assertEqual(terms['入る']['meaning'],'đi vào')
            self.assertNotIn('限定',terms)
            self.assertTrue(all(not c['verified'] for c in new))
            before=server.get_state()['cards']
            add,report=d_enrich.dictionary_cards(before)
            self.assertFalse(any(c['term']=='入る' for c in add))
            self.assertGreaterEqual(stats['added'],3)

    def test_v5_verified_missing_list_all_imported(self):
        import csv
        deck={c['term']:c for c in server.get_state()['cards']}
        with (Path(__file__).resolve().parents[1]/'data'/'audited_missing_from_v4.csv').open(encoding='utf-8-sig',newline='') as inp:
            rows=list(csv.DictReader(inp))
        self.assertEqual(len(rows),45)
        for r in rows:
            item=deck.get(r['muc_trong_anh_pdf'])
            self.assertIsNotNone(item,r['muc_trong_anh_pdf'])
            self.assertTrue(item.get('reading') and item.get('meaning'))
            self.assertTrue(item.get('verified'),r['muc_trong_anh_pdf'])

    def test_v5_seed_increments_without_changing_old_cards(self):
        old=json.loads((Path(__file__).resolve().parents[1]/'data'/'cards_initial_137.json').read_text())
        by_id={c['id']:c for c in server.get_state()['cards']}
        preserved=('id','term','reading','meaning','meaning_aliases','kind','tier','topic')
        for c in old:
            self.assertEqual({key:by_id[c['id']].get(key) for key in preserved},
                             {key:c.get(key) for key in preserved})
        self.assertGreaterEqual(len(by_id),3600)

    def test_restore_invalid_no_data_loss(self):
        snap=server.export_data();snap['progress']=[{'card_id':'missing','skill':'meaning','stage':1}]
        with self.assertRaises(ValueError):server.restore(snap)
        self.assertGreaterEqual(len(server.get_state()['cards']),2500)

if __name__=='__main__':unittest.main()
