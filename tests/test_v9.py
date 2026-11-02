"""Regression checks for the source-gated v9 addition."""
import json,unittest,hashlib,tempfile
from unittest.mock import patch
from pathlib import Path
import server

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data'

class V9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.deck=json.loads((P/'cards.json').read_text(encoding='utf8'))
        cls.old_hashes=json.loads((P/'v8_baseline_hashes.json').read_text(encoding='utf8'))

    def test_446_unique_new_cards_with_kana_and_vietnamese(self):
        added=[c for c in self.deck if c['id'].startswith('v9-ocr-')]
        self.assertEqual(len(added),446)
        self.assertEqual(len({c['id'] for c in added}),446)
        for c in added:
            self.assertTrue(c['meaning'])
            self.assertTrue(c['reading'])
            self.assertTrue(c['source_refs'])
            self.assertFalse(c['verified'])

    def test_v9_source_refs_contained_in_source_ocr(self):
        pages={(x['book'],x['pdf_page']):x['text'] for x in json.loads((P/'source_pages.json').read_text())}
        for c in self.deck:
            if c['id'].startswith('v9-ocr-'):
                for loc in c['source_refs']:
                    if loc.get('type')=='official_workbook':continue
                    self.assertIn(c['term'],pages[(loc['book'],loc['pdf_page'])])

    def test_old_v8_cards_never_overwritten(self):
        byid={c['id']:c for c in self.deck}
        self.assertEqual(len(self.old_hashes),3953)
        for id,expected in self.old_hashes.items():
            self.assertIn(id,byid)
            # v10 adds source metadata; keep the v8 learning content immutable.
            original=dict(byid[id])
            for key in ('source_type','source_year','source_page','source_url','source_form','verification_status','exam_priority','exam_year_claim'):
                original.pop(key,None)
            if 'source_refs' in original:original['source_refs']=[x for x in original['source_refs'] if x.get('type')!='official_workbook']
            variants=[original]
            if not original.get('source_refs'):
                variants=[{**original,'source_refs':[]},{k:v for k,v in original.items() if k!='source_refs'}]
            results={hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest() for row in variants}
            self.assertIn(expected,results,id)

    def test_new_cards_in_live_local_db(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(server,'DB',Path(directory)/'fresh.sqlite3'):
                server.init()
                with server.connect() as c:cards=server.all_cards(c)
        self.assertGreaterEqual(len(cards),4399)
        self.assertEqual({c['id'] for c in cards},{c['id'] for c in self.deck})

if __name__=='__main__':unittest.main()
