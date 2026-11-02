import unittest, json
from unittest.mock import patch
from soumatome_parts_import import reading_from_mixed,parse_part
from source_coverage import coverage,get_page
import server

class V7Test(unittest.TestCase):
    def test_mixed_kanji_reading_only_from_known_vocabulary(self):
        d={'予定':'よてい','連絡':'れんらく'}
        self.assertEqual(reading_from_mixed('予定をたてる',d),'よていをたてる')
        self.assertEqual(reading_from_mixed('連絡がつく',d),'れんらくがつく')
        self.assertIsNone(reading_from_mixed('未知の漢字',d))

    def test_parser_rejects_corrupt_meaning_and_ambiguous_reading(self):
        h='<table><tr><th>STT</th><th>Kanji</th><th>Tiếng Nhật</th><th>Ý nghĩa</th></tr>'
        h+='<tr><td>1</td><td>予定を立てる</td><td>予定をたてる</td><td>Lập kế hoạch</td></tr>'
        h+='<tr><td>2</td><td>買い物かごを下げる</td><td>かいものかごをさげる</td><td>4</td></tr></table>'
        cards,invalid=parse_part(h,35,{'予定':'よてい'})
        self.assertEqual(len(cards),1)
        self.assertEqual(cards[0]['reading'],'よていをたてる')
        self.assertEqual(len(invalid),1)

    def test_all_469_pages_audited_without_false_complete(self):
        with server.connect() as c: cards=server.all_cards(c)
        summary,rows=coverage(cards)
        self.assertEqual(len(rows),469)
        self.assertEqual(summary['full_page_reviews'],0)
        self.assertEqual(set(summary['by_book']),{'Kanji','Từ vựng','Ngữ pháp','Đọc hiểu'})

    def test_book_page_source(self):
        p=get_page('tuvung',42)
        self.assertIn('停車駅',p['ocr_text'])
        with self.assertRaises(ValueError):get_page('tuvung',500)

    def test_all_sources_partial_failure_must_report_error(self):
        with patch.object(server,'import_community_soumatome',side_effect=ValueError('missing part 16')):
            with patch.object(server,'enrich_dictionary',return_value={'added':17}):
                with patch.object(server,'audit_source_pages',return_value={'source_pages':469}):
                    result=server.import_all_sources()
        self.assertFalse(result['ok'])
        self.assertIn('soumatome_35_parts',result['errors'])
        self.assertEqual(result['imports']['japanese_vietnamese_dictionary']['added'],17)

if __name__=='__main__':unittest.main()
