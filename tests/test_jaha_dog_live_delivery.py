# -*- coding: utf-8 -*-
"""Official JAHA dog-training seminars: live webinar even with replay."""
import unittest

from jaha_enrich import parse_jaha_detail, _dog_lecture_delivery

URL_2 = "https://www.jaha.or.jp/owners/dog-training/kougi2_ol/"
URL_3 = "https://www.jaha.or.jp/owners/dog-training/kougi3ol/"


def item(number, url, date):
    return {"title": "家庭犬のしつけ方講座インストラクター養成コース講義" + str(number),
            "url": url, "start_date": date, "format": None,
            "price": None, "deadline": None, "start_time": None, "end_time": None}


PAGE_2 = """講義２【オンライン】
講義２はZoom（ウェビナー形式）によるオンライン開催です
リアルタイム配信後、１週間の見直し配信があります
２０２６年１２月５日（土曜日）１２月１２日（土曜日）の２回に分けて配信
パート１ １２月５日（土曜日）14:00-17:00
パート２ １２月１２日（土曜日）14:00-17:00
"""
PAGE_3 = """講義３【オンライン】
講義３はZoom（ウェビナー形式）によるオンライン開催です
リアルタイム配信後、１週間の見直し配信があります
２０２６年１１月７日（土曜日）１１月１４日（土曜日）の２回に分けて配信
パート２ １１月１４日（土曜日）14:00-17:00
"""


class JahaLiveWebinarTests(unittest.TestCase):
    def test_course_2_is_live_not_on_demand(self):
        for day in ("2026-12-05", "2026-12-12"):
            with self.subTest(day=day):
                out = parse_jaha_detail(PAGE_2, item(2, URL_2, day))
                self.assertEqual(out.get("format"), "ライブ配信")

    def test_course_3_is_live_not_on_demand(self):
        out = parse_jaha_detail(PAGE_3, item(3, URL_3, "2026-11-14"))
        self.assertEqual(out.get("format"), "ライブ配信")

    def test_wrong_course_number_does_not_borrow(self):
        self.assertIsNone(_dog_lecture_delivery(
            PAGE_2.splitlines(), item(3, URL_2, "2026-12-05")))

    def test_wrong_url_does_not_borrow(self):
        x = item(2, "https://www.jaha.or.jp/owners/dog-training/other/", "2026-12-05")
        self.assertIsNone(_dog_lecture_delivery(PAGE_2.splitlines(), x))

    def test_missing_realtime_statement_is_not_enough(self):
        page = PAGE_2.replace("リアルタイム配信後、１週間の見直し配信があります", "")
        self.assertNotIn("format", parse_jaha_detail(
            page, item(2, URL_2, "2026-12-05")))

    def test_replay_only_not_labelled_live(self):
        page = PAGE_2.replace("講義２はZoom（ウェビナー形式）によるオンライン開催です",
                              "講義２は録画配信です")
        self.assertNotIn("format", parse_jaha_detail(
            page, item(2, URL_2, "2026-12-05")))

    def test_existing_correct_format_not_overwritten(self):
        x = item(2, URL_2, "2026-12-05")
        x["format"] = "ライブ配信"
        self.assertNotIn("format", parse_jaha_detail(PAGE_2, x))


if __name__ == "__main__":
    unittest.main()
