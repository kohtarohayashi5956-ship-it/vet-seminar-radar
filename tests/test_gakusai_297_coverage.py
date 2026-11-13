# -*- coding: utf-8 -*-
"""First card of Gakusai annual listing must not vanish."""
import datetime
import unittest
from free_extract import extract_free

URL = "https://www.gakusai.co.jp/doubutu/seminar-comingup/"
DETAIL = "https://www.gakusai.co.jp/vet/vet-seminar/35591/"
NOW = datetime.date(2026, 11, 13)
BODY = """獣医セミナー 年間スケジュール
2027 セミナー 開催スケジュール
1月
No.297 高木哲先生「失敗しない腸管吻合 ミニドライラボ&セミナー」 »詳細はこちら <https://www.gakusai.co.jp/vet/vet-seminar/35591/>
1月24日（日） 東京｜ ウェブ受講（3月1日～）
3月
No.298 手島健次先生「明日から使える！ 犬と猫の局所麻酔セミナー」 »詳細はこちら <https://www.gakusai.co.jp/vet/vet-seminar/35589/>
3月7日（日） 東京｜ ウェブ受講（4月1日～）
"""


class FirstGakusaiCardTests(unittest.TestCase):
    def test_first_card_present_with_verified_detail_url(self):
        stats = {}
        events = extract_free("学際企画", URL, "", BODY, NOW, stats)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["start_date"], "2027-01-24")
        self.assertEqual(events[0]["url"], DETAIL)
        self.assertTrue(events[0]["verified"])
        self.assertIn("腸管吻合", events[0]["title"])

    def test_missing_numbered_card_not_guessed(self):
        events = extract_free("学際企画", URL, "",
                              BODY.replace("No.297 ", ""), NOW, {})
        self.assertEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main()
