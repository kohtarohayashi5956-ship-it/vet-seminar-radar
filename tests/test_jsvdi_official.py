# -*- coding: utf-8 -*-
"""Official JSVDI 79th congress: no guessed course dates or viewing dates."""
import datetime
import unittest
from free_extract import extract_free

URL = "https://jsvdi.com/conference/3332/"
PAGE = """第79回 日本獣医画像診断学会【福岡開催】
日時：2026年12月5日（土）・6日（日）
場所：福岡国際会議場（福岡県福岡市）
開催方法：ハイブリッド開催（現地対面式参加／後日動画配信）
12月5日（土）
▼第2会場（405+406）
●10：00～11：30
認定講習「各種画像検査法の物理学とアーティファクト」
講師：池田 彬人（東京大学）
●13：05～14：35
認定講習「腹部レントゲン読影法1」
講師：新坊 弦也（北海道大学）
●14：50～16：20
認定講習「腹部レントゲン読影法2」
講師：新坊 弦也（北海道大学）
12月6日（日）
▼第2会場（405+406）
●10：00～11：30
認定講習「胸部レントゲン読影法1」
講師：戸島 篤史（日本小動物医療センター）
●12：40～14：10
認定講習「胸部レントゲン読影法2」
講師：戸島 篤史（日本小動物医療センター）
参加料：【会員】10,000円　【非会員】13,000円
【学生参加】無料
お申込受付期間
【現地参加】10月9日（金）〜12月1日（火）まで
【後日動画配信】10月9日（金）〜2027年1月11日（月）まで
"""


class JsvdiOfficialTests(unittest.TestCase):
    def extract(self, text=PAGE, day=datetime.date(2026, 11, 14)):
        stats = {}
        result = extract_free("日本獣医画像診断学会", URL, "", text, day, stats)
        return result, stats

    def test_five_certification_lectures_and_conference(self):
        events, stats = self.extract()
        self.assertEqual(len(events), 6)
        self.assertEqual(stats["jsvdi_certification_lectures"], 5)
        congress = next(x for x in events if x["title"].startswith("第79回"))
        self.assertEqual(congress["start_date"], "2026-12-05")
        self.assertEqual(congress["end_date"], "2026-12-06")
        self.assertEqual(congress["format"], "ハイブリッド")
        self.assertIn("13,000円", congress["price"])
        self.assertIsNone(congress["is_free"])
        self.assertTrue(congress["verified"])
        lectures = [x for x in events if x["certification_program"]]
        self.assertEqual(sum(x["start_date"] == "2026-12-05" for x in lectures), 3)
        self.assertEqual(sum(x["start_date"] == "2026-12-06" for x in lectures), 2)
        self.assertEqual(lectures[0]["start_time"], "10:00")
        self.assertEqual(lectures[0]["end_time"], "11:30")
        self.assertEqual(lectures[-1]["start_time"], "12:40")
        self.assertTrue(all(x["deadline"] is None for x in lectures))
        self.assertTrue(all(x["verified"] for x in lectures))
        self.assertTrue(all(x["certification_note"] for x in lectures))

    def test_missing_congress_schedule_fails_closed(self):
        bad = PAGE.replace("日時：2026年12月5日（土）・6日（日）",
                           "日時は調整中")
        self.assertEqual(self.extract(bad)[0], [])

    def test_no_time_means_no_fake_lecture(self):
        bad = PAGE.replace("●10：00～11：30\n認定講習「各種画像検査法の物理学とアーティファクト」",
                           "開始時刻は未定\n認定講習「各種画像検査法の物理学とアーティファクト」")
        rows, stats = self.extract(bad)
        self.assertEqual(len(rows), 5)
        self.assertEqual(stats["jsvdi_certification_lectures"], 4)

    def test_after_congress_no_historical_duplication(self):
        self.assertEqual(self.extract(day=datetime.date(2026, 12, 7))[0], [])

    def test_other_source_page_not_authorized(self):
        self.assertEqual(extract_free("JSVDI", "https://jsvdi.com/", "", PAGE,
                                      datetime.date(2026, 11, 14), {}), [])


if __name__ == "__main__":
    unittest.main()
