# -*- coding: utf-8 -*-
"""Official No.297 detail fallback and canonical deduplication."""
import datetime
import unittest

from free_extract import extract_free
from merge import event_id
from gakusai_enrich import parse_gakusai

TODAY = datetime.date(2026, 11, 13)
LISTING = "https://www.gakusai.co.jp/doubutu/seminar-comingup/"
DETAIL = "https://www.gakusai.co.jp/vet/vet-seminar/35591/"
DETAIL_TEXT = """# No.297 失敗しない腸管吻合 ミニドライラボ&セミナー
獣医 2027年1月24日
失敗しない腸管吻合
高木 哲 先生
開催日時・会場
東京会場 2027年1月24日（日）10：00～16：00
駐健保会館
来場受講料
法人・個人会員 | 9,000円（税込9,900円）＋ミニドライラボ材料費 4,500円（税込4,950円）
一般獣医師 | 27,000円（税込29,700円）＋ミニドライラボ材料費 4,500円（税込4,950円）
ウェブ受講料
"""
LIST_TEXT = """2027 セミナー 開催スケジュール
No.297 高木哲先生「失敗しない腸管吻合 ミニドライラボ&セミナー」 »詳細はこちら <https://www.gakusai.co.jp/vet/vet-seminar/35591/>
1月24日（日） 東京｜ウェブ受講（3月1日～）
No.298 手島健次先生「明日から使える！ 犬と猫の局所麻酔セミナー」
3月7日（日） 東京
"""


class No297FallbackTests(unittest.TestCase):
    def test_detail_extracts_one_official_event(self):
        events = extract_free("学際企画", DETAIL, "", DETAIL_TEXT, TODAY, {})
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e["title"], "失敗しない腸管吻合 ミニドライラボ&セミナー")
        self.assertEqual(e["start_date"], "2027-01-24")
        self.assertEqual(e["format"], "現地")
        self.assertEqual(e["topics"], ["外科", "消化器"])
        self.assertEqual(e["start_time"], "10:00")
        self.assertEqual(e["end_time"], "16:00")
        self.assertEqual(e["url"], DETAIL)
        self.assertTrue(e["verified"])
        self.assertFalse(e["url_is_page"])

    def test_listing_and_detail_share_same_event_id(self):
        rows = extract_free("学際企画", LISTING, "", LIST_TEXT, TODAY, {})
        detail = extract_free("学際企画", DETAIL, "", DETAIL_TEXT, TODAY, {})
        self.assertEqual(len(rows), 2)
        self.assertEqual(event_id("gakusai", rows[0]["title"], rows[0]["start_date"]),
                         event_id("gakusai", detail[0]["title"], detail[0]["start_date"]))

    def test_missing_event_schedule_does_not_invent(self):
        self.assertEqual(extract_free("学際企画", DETAIL, "", DETAIL_TEXT.replace(
            "10：00～16：00", "時間未定"), TODAY, {}), [])

    def test_wrong_detail_url_does_not_trigger(self):
        self.assertEqual(extract_free("学際企画",
                         "https://www.gakusai.co.jp/vet/vet-seminar/35590/",
                         "", DETAIL_TEXT, TODAY, {}), [])


if __name__ == "__main__":
    unittest.main()
