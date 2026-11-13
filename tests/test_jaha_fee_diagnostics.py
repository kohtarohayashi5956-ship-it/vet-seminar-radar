# -*- coding: utf-8 -*-
"""JAHA detail scan records parsed dog-lecture fees independently of generic fees."""
import datetime
import unittest

from jaha_enrich import enrich_jaha

URL = "https://www.jaha.or.jp/owners/dog-training/kougi2_ol/"
PAGE = """<article><h1>講義２【オンライン】</h1>
<p>講義２はZoom（ウェビナー形式）によるオンライン開催です</p>
<p>２０２６年１２月５日（土曜日）１２月１２日（土曜日）の２回に分けて配信</p>
<p>パート１ １２月５日（土曜日）14:00-17:00</p>
<h2>受講料</h2>
<p>通常受講：</p><p>一般料金19,800円、JAHA会員16,500円、学生料金9,900円</p>
<p>単発受講：</p><p>一般料金22,000円、JAHA会員18,700円</p>
<h2>お申し込み</h2></article>"""


class Fetch:
    def get(self, url):
        if url != URL:
            raise ValueError("unexpected URL")
        return PAGE


class JahaFeeDiagnosticsTests(unittest.TestCase):
    def test_dog_fee_diagnostic_is_true_when_parsed(self):
        row = {"title": "家庭犬のしつけ方講座インストラクター養成コース講義２",
               "url": URL, "start_date": "2026-12-05",
               "price": None, "format": None, "start_time": None,
               "end_time": None, "deadline": None}
        stats = {}
        enrich_jaha([row], Fetch(), datetime.date(2026, 11, 13), stats)
        self.assertEqual(len(stats["fee_detail_checks"]), 1)
        self.assertTrue(stats["fee_detail_checks"][0]["dog_lecture_fee_parsed"])
        self.assertIsNotNone(row["price"])

    def test_other_seminars_not_marked_as_dog_fee_parsed(self):
        row = {"title": "まったく別の講座",
               "url": URL, "start_date": "2026-12-05",
               "price": None, "format": None, "start_time": None,
               "end_time": None, "deadline": None}
        stats = {}
        enrich_jaha([row], Fetch(), datetime.date(2026, 11, 13), stats)
        self.assertFalse(stats["fee_detail_checks"][0]["dog_lecture_fee_parsed"])


if __name__ == "__main__":
    unittest.main()
