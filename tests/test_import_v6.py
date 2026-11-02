import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile,json
from soumatome_parts_import import parse_part,import_35_parts
from soumatome_import import extract
class ImportTests(unittest.TestCase):
    def test_table_parser_including_kana_only_and_phrase(self):
        h='<table><tr><th>STT</th><th>Kanji</th><th>Tiếng Nhật</th><th>Ý Nghĩa</th></tr>'
        h+='<tr><td>1</td><td>台所</td><td>だいどころ<button>🔊</button></td><td>Nhà bếp 💡 Mẹo nhớ</td></tr>'
        h+='<tr><td>2</td><td></td><td>ワイングラス</td><td>Cốc uống rượu 💡Mẹo nhớ</td></tr>'
        h+='<tr><td>3</td><td>電源を切る</td><td>でんげんをきる</td><td>Tắt nguồn</td></tr></table>'
        c,errors=parse_part(h,1)
        self.assertEqual(len(c),3);self.assertEqual(c[0]['meaning'],'Nhà bếp')
        self.assertEqual(c[1]['term'],'ワイングラス');self.assertEqual(c[2]['reading'],'でんげんをきる')
    def test_incomplete_source_does_not_write(self):
        raw='<table><tr><td>1</td><td>台所</td><td>だいどころ</td><td>Nhà bếp</td></tr></table>'
        with tempfile.TemporaryDirectory() as d:
            with patch('soumatome_parts_import.CACHE',Path(d)/'empty.json'):
                with self.assertRaisesRegex(ValueError,'Chưa tải/đọc đủ'):
                    import_35_parts([],fetcher=lambda i:raw,expected_min=1)
    def test_complete_source_dedup_and_preview(self):
        def one(n):
            h='<table>'
            for j in range(25):
                word='単語'+chr(0x4e00 + n*30 + j)
                h+=f'<tr><td>{j+1}</td><td>{word}</td><td>たんご</td><td>từ mới {j+1}</td></tr>'
            return h+'</table>'
        with tempfile.TemporaryDirectory() as d:
            with patch('soumatome_parts_import.CACHE',Path(d)/'cache.json'):
                cards,meta=import_35_parts([],fetcher=one,expected_min=400)
                self.assertEqual(len(cards),875)
                self.assertEqual(meta['source_pages'],35)
                self.assertTrue((Path(d)/'cache.json').is_file())
    def test_cache_fallback_only_when_complete(self):
        # A prior complete 35-part import can be reused if the network fails.
        with tempfile.TemporaryDirectory() as d:
            raw=[]
            for n in range(1,36):
                for j in range(16):
                    raw.append({'part':n,'term':'語'+chr(0x4e00+n*17+j),'reading':'ご',
                                'meaning':'từ mới'})
            cache=Path(d)/'full.json';cache.write_text(json.dumps(raw,ensure_ascii=False),encoding='utf8')
            with patch('soumatome_parts_import.CACHE',cache):
                added,meta=import_35_parts([],fetcher=lambda n: (_ for _ in ()).throw(OSError('network down')),
                                           expected_min=400)
                self.assertTrue(meta['used_local_cache'])
                self.assertEqual(meta['source_pages'],35)
                self.assertEqual(len(added),len(raw))
    def test_partial_cache_does_not_mask_network_failure(self):
        with tempfile.TemporaryDirectory() as d:
            cache=Path(d)/'partial.json'
            cache.write_text(json.dumps([{'part':1,'term':'台所','reading':'だいどころ','meaning':'nhà bếp'}],
                                        ensure_ascii=False),encoding='utf8')
            with patch('soumatome_parts_import.CACHE',cache):
                with self.assertRaisesRegex(ValueError,'Cache chưa đủ'):
                    import_35_parts([],fetcher=lambda n: (_ for _ in ()).throw(OSError('network down')),
                                    expected_min=1)
    def test_second_import_parser_no_false_furigana_card(self):
        h='<h1>Trang 1/1</h1><h2>台所</h2><p>だいどころ</p><p>nhà bếp</p><p>Danh từ · Soumatome · Tuần 1 · Ngày 1</p>'
        cards,_=extract(h)
        self.assertEqual(len(cards),1)

if __name__=='__main__':unittest.main()
