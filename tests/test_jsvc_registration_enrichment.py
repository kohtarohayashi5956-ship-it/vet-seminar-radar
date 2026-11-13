# -*- coding: utf-8 -*-
"""125th JSVC attendee and abstract dates must never be mixed up."""
import datetime
import unittest
from society_enrich import (JSVC_COURSES_URL, JSVC_REGISTRATION_URL,
                            parse_jsvc_registration, enrich_jsvc)

EVENT = {
    "source_id": "jsvc", "start_date": "2026-12-19",
    "title": "第125回日本獣医循環器学会定例大会",
    "url": "https://www.jsvc.jp/meeting/regular/conf125/",
}
PAGE = """参加申込/演題申込
開催概要
１．参加申込概要
◆参加費
会場参加　一般：10,000円、学生：3,000円、研修医（フルタイム）：5,000円
オンデマンド配信の視聴費＋10,000円
◆各種締切日
演題登録：10月18日（日）
参加申込：
◆懇親会
締切：11月29日（日）
費用：一般・その他　10,000円、学生　2,000円
２．発表要領
"""
COURSES = """2026年度 認定医講習会
第125回　定例大会
日時：2026年12月19、20日
会場：パピヨン24ガスホール（福岡）
22
感染性心内膜炎
23
犬のフィラリア症
34
心臓腫瘍・心膜疾患
日本獣医循環器学会事務局
"""


class FakeFetcher:
    def __init__(self, missing=False):
        self.calls = []
        self.missing = missing

    def get(self, url):
        self.calls.append(url)
        if url == JSVC_REGISTRATION_URL and self.missing:
            raise RuntimeError("robots blocked")
        data = COURSES if url == JSVC_COURSES_URL else PAGE
        return "<main><p>" + data.replace("\n", "</p><p>") + "</p></main>"


class JSVCRegistrationTests(unittest.TestCase):
    def test_exact_price_and_abstract_date(self):
        data = parse_jsvc_registration(PAGE, EVENT)
        self.assertIn("10,000円", data["price"])
        self.assertIn("3,000円", data["price"])
        self.assertEqual(data["abstract_deadline"], "2026-10-18")
        self.assertEqual(data["detail_url"], JSVC_REGISTRATION_URL)
        self.assertNotIn("deadline", data)

    def test_no_dinner_fee_or_dinner_deadline(self):
        out = parse_jsvc_registration(PAGE, EVENT)
        self.assertNotIn("11-29", repr(out))
        self.assertNotIn("懇親会", repr(out))

    def test_wrong_meeting_rejected(self):
        for ev in (dict(EVENT, start_date="2027-12-19"),
                   dict(EVENT, title="第124回定例大会"),
                   dict(EVENT, source_id="gakusai")):
            with self.subTest(event=ev):
                self.assertEqual(parse_jsvc_registration(PAGE, ev), {})

    def test_ambiguous_fee_not_invented(self):
        bad = PAGE.replace("オンデマンド配信の視聴費＋10,000円", "視聴費未定")
        self.assertNotIn("price", parse_jsvc_registration(bad, EVENT))

    def test_abstract_deadline_not_borrowed_from_dinner(self):
        bad = PAGE.replace("演題登録：10月18日（日）", "演題登録：")
        self.assertNotIn("abstract_deadline", parse_jsvc_registration(bad, EVENT))

    def test_existing_data_not_overwritten(self):
        ev = dict(EVENT, price="独立に確認した受講料",
                  abstract_deadline="2026-10-15", detail_url="https://www.jsvc.jp/other")
        self.assertEqual(parse_jsvc_registration(PAGE, ev), {})

    def test_enrichment_fetches_registration_once(self):
        fetcher = FakeFetcher()
        ev = dict(EVENT)
        rows = enrich_jsvc([ev], fetcher, datetime.date(2026, 11, 13), {})
        self.assertEqual(fetcher.calls, [JSVC_COURSES_URL, JSVC_REGISTRATION_URL])
        self.assertEqual(rows[0]["abstract_deadline"], "2026-10-18")
        self.assertIn("会場参加", rows[0]["price"])

    def test_blocked_registration_retains_course_program(self):
        fetcher = FakeFetcher(missing=True)
        stats = {}
        ev = dict(EVENT)
        enrich_jsvc([ev], fetcher, datetime.date(2026, 11, 13), stats)
        self.assertIn("講座22", ev["certification_program"])
        self.assertNotIn("price", ev)
        self.assertEqual(stats["registration_detail_failed"], 1)


if __name__ == "__main__":
    unittest.main()
