# -*- coding: utf-8 -*-
"""JAHA's ISO-date upcoming card list (separate from calendar table)."""
import datetime
import unittest
from extract import html_to_text
from free_extract import extract_free

class JahaUpcomingTests(unittest.TestCase):
    def test_two_cities_same_title_preserve_separate_dates(self):
        base = "https://www.jaha.or.jp/seminar-calendar/top/"
        html = """
        <article><p>受付中</p>
        <a href="/training/seminar/vet/endocrine26/">第179回国際セミナー 犬猫の内分泌疾患アップデート2026</a>
        <p>2026-11-06～2026-11-08【東京都】</p><p>対象：獣医師・獣医学生</p></article>
        <article><p>受付中</p>
        <a href="/training/seminar/vet/endocrine26/">第179回国際セミナー 犬猫の内分泌疾患アップデート2026</a>
        <p>2026-11-11～2026-11-13【大阪府】</p><p>対象：獣医師・獣医学生</p></article>
        <article><p>受付中</p><a href="/training/seminar/vnseries/">動物病院スタッフのためのシニアケア講座</a>
        <p>2026-11-12～2026-11-12【東京都】</p><p>対象：獣医師・動物看護師</p></article>
        """
        stats={}
        events=extract_free("JAHA",base,"",html_to_text(html,base),datetime.date(2026,11,6),stats)
        self.assertEqual(len(events),3)
        self.assertEqual([e["start_date"] for e in events],
                         ["2026-11-06","2026-11-11","2026-11-12"])
        self.assertEqual(events[0]["end_date"],"2026-11-08")
        self.assertEqual(events[1]["end_date"],"2026-11-13")
        self.assertEqual(events[0]["prefecture"],"東京都")
        self.assertTrue(all(e["verified"] for e in events))
        self.assertIn("獣医師", events[0]["audience"])
        self.assertNotIn("一般", events[0]["audience"])
        self.assertEqual(events[2]["audience"], ["獣医師", "動物看護師"])

    def test_general_audience_not_leaked_from_next_card(self):
        base = "https://www.jaha.or.jp/seminar-calendar/top/"
        html = """<section><p>受付中</p>
          <a href="/owners/lecture/">家庭犬のしつけ方講座インストラクター養成コース講義３</a>
          <p>2026-11-07～2026-11-07【東京都】</p>
          <p>対象：一般・すべて</p></section>
          <section><p>受付中</p>
          <a href="/training/vet/">獣医師向け内分泌セミナー</a>
          <p>2026-11-08～2026-11-08【東京都】</p>
          <p>対象：獣医師・獣医学生</p></section>"""
        events = extract_free("JAHA", base, "", html_to_text(html, base),
                              datetime.date(2026,11,6), {})
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["audience"], ["一般"])
        self.assertEqual(events[1]["audience"], ["獣医師", "学生"])

if __name__ == "__main__":
    unittest.main()
