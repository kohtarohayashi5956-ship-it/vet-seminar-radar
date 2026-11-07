# -*- coding: utf-8 -*-
"""VETS ACADEMY detail page must match the exact listed course date."""
import datetime
import unittest

from academy_enrich import enrich_academy, parse_academy_detail

URL = "https://academy.eduone.jp/seminar/detail/10284"
TODAY = datetime.date(2026, 11, 7)
PAGE = """術後を見据えた外科　大腿骨頭壊死症に対するアプローチ
開催日時：2026/11/27 20:00～
セミナー概要
■開催日時
2026年11月27日（金）20:00～22:00（受付開始19:30）
※申込締切：2026年11月26日（木）18:00まで
■対象
獣医師
■形式
Zoomウェビナー
受講料
申込締切：11月26日（木）18時まで
会費
5,000円(税込)
申し込み
"""


def event(**kwargs):
    item = {"url": URL, "title": "術後を見据えた外科",
            "start_date": "2026-11-27", "end_date": None,
            "start_time": "20:00", "end_time": None,
            "deadline": None, "price": None}
    item.update(kwargs)
    return item


class Fake:
    def __init__(self, text=PAGE):
        self.text = text
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        return "<main>" + "".join(f"<p>{line}</p>" for line in self.text.splitlines()) + "</main>"


class AcademyDetailTests(unittest.TestCase):
    def test_exact_schedule_allows_explicit_deadline_and_fee(self):
        result = parse_academy_detail(PAGE, event())
        self.assertEqual(result, {"end_time": "22:00",
                                  "deadline": "2026-11-26",
                                  "price": "5,000円(税込)"})

    def test_different_date_fails_closed(self):
        self.assertEqual(parse_academy_detail(PAGE, event(start_date="2026-11-28")), {})

    def test_conflicting_schedule_times_fails_closed(self):
        conflicting = PAGE + "\n■開催日時\n2026年11月27日 21:00～23:00\n"
        self.assertEqual(parse_academy_detail(conflicting, event()), {})

    def test_registration_not_a_course_date(self):
        text = ("※申込締切：2026年11月26日18:00まで\n"
                "会費\n5,000円(税込)\n")
        self.assertEqual(parse_academy_detail(text, event()), {})

    def test_no_year_in_deadline_not_assumed(self):
        text = ("■開催日時\n2026年11月27日 20:00～22:00\n"
                "申込締切：11月26日\n会費\n5,000円(税込)")
        out = parse_academy_detail(text, event())
        self.assertNotIn("deadline", out)
        self.assertEqual(out["price"], "5,000円(税込)")

    def test_no_unlabelled_price(self):
        text = ("■開催日時\n2026年11月27日 20:00～22:00\n"
                "他の講習案内 50,000円")
        out = parse_academy_detail(text, event())
        self.assertNotIn("price", out)

    def test_existing_fee_and_deadline_are_preserved(self):
        out = parse_academy_detail(PAGE, event(price="会員 3,000円", deadline="2026-11-20"))
        self.assertNotIn("price", out)
        self.assertNotIn("deadline", out)

    def test_fetch_once_for_duplicate_course_and_skip_external(self):
        f = Fake()
        rows = [event(), event(), event(url="https://evil.example/seminar/detail/10284")]
        stats = {}
        enriched = enrich_academy(rows, f, TODAY, stats)
        self.assertEqual(f.calls, [URL])
        self.assertEqual([x["deadline"] for x in enriched],
                         ["2026-11-26", "2026-11-26", None])
        self.assertEqual(stats["details_scanned"], 1)
        self.assertEqual(stats["detail_fetch_failed"], 0)

    def test_blocked_request_preserves_existing_course(self):
        class Denied:
            def get(self, url):
                raise RuntimeError("robots blocked")
        row = event()
        stats = {}
        result = enrich_academy([row], Denied(), TODAY, stats)
        self.assertIsNone(result[0]["price"])
        self.assertEqual(stats["detail_fetch_failed"], 1)


if __name__ == "__main__":
    unittest.main()
