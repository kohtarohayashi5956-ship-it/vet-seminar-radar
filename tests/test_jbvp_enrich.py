# -*- coding: utf-8 -*-
"""JBVP region-specific official venue confirmation, never infer deadlines."""
import datetime
import unittest
from jbvp_enrich import parse_jbvp_region, enrich_jbvp

TODAY = datetime.date(2026, 11, 7)
URL = "https://www.jbvp.org/regional/nagoya.html"
PAGE = """Regional Meetings地区大会
第7回 名古屋地区大会
日時
2027年2月28日（日）
会場
ウインクあいち（愛知県産業労働センター）
お問い合わせ
〒483-8228 愛知県江南市
TEL：0587-53-5755
"""

def event(**kwargs):
    value = {"title":"第7回 名古屋地区大会", "start_date":"2027-02-28",
             "detail_url":URL, "url":"https://www.jbvp.org/vn/",
             "venue":None, "prefecture":None, "deadline":None}
    value.update(kwargs)
    return value


class DummyFetcher:
    def __init__(self, html=PAGE):
        self.html = html
        self.calls = []
    def get(self, url):
        self.calls.append(url)
        return "<main>" + "".join("<p>" + line + "</p>" for line in self.html.splitlines()) + "</main>"


class JBVPDetailTests(unittest.TestCase):
    def test_matching_meeting_venue(self):
        got = parse_jbvp_region(PAGE, event())
        self.assertEqual(got, {"venue":"ウインクあいち(愛知県産業労働センター)",
                               "prefecture":"愛知県"})

    def test_date_bound_meeting_times(self):
        page = PAGE.replace("2027年2月28日（日）", "2027年2月28日（日）10:00〜17:00")
        got = parse_jbvp_region(page, event())
        self.assertEqual(got["start_time"], "10:00")
        self.assertEqual(got["end_time"], "17:00")

    def test_time_on_unrelated_line_is_not_borrowed(self):
        page = PAGE.replace("会場\\n", "別イベント 10:00〜17:00\\n会場\\n")
        got = parse_jbvp_region(page, event())
        self.assertNotIn("start_time", got)

    def test_existing_times_remain_unchanged(self):
        page = PAGE.replace("2027年2月28日（日）", "2027年2月28日（日）10:00〜17:00")
        got = parse_jbvp_region(page, event(start_time="10:00", end_time="18:00"))
        self.assertNotIn("start_time", got)
        self.assertNotIn("end_time", got)

    def test_conflicting_time_not_used(self):
        page = PAGE.replace("2027年2月28日（日）", "2027年2月28日（日）10:00〜17:00")
        got = parse_jbvp_region(page, event(start_time="09:00"))
        self.assertNotIn("start_time", got)
        self.assertNotIn("end_time", got)

    def test_fetch_for_time_even_if_venue_known(self):
        page = PAGE.replace("2027年2月28日（日）", "2027年2月28日（日）10:00〜17:00")
        e = event(venue="既存公式会場", prefecture="愛知県")
        f = DummyFetcher(page)
        enrich_jbvp([e], f, TODAY, {})
        self.assertEqual(f.calls, [URL])
        self.assertEqual(e["start_time"], "10:00")
        self.assertEqual(e["venue"], "既存公式会場")

    def test_unrelated_meeting_date_is_not_accepted(self):
        self.assertEqual(parse_jbvp_region(PAGE,event(start_date="2027-03-01")),{})

    def test_wrong_region_page_does_not_enrich(self):
        self.assertEqual(parse_jbvp_region(PAGE,event(detail_url="https://www.jbvp.org/regional/kyoto.html")),{})

    def test_existing_venue_not_overwritten(self):
        got = parse_jbvp_region(PAGE,event(venue="既存公式会場",prefecture="愛知県"))
        self.assertEqual(got,{})

    def test_only_event_specific_official_links(self):
        self.assertEqual(parse_jbvp_region(PAGE,event(detail_url="https://evil.example/regional/nagoya.html")),{})
        self.assertEqual(parse_jbvp_region(PAGE,event(detail_url="https://www.jbvp.org/regional/archive.html")),{})
        self.assertEqual(parse_jbvp_region(PAGE,event(detail_url="https://www.jbvp.org/regional/nagoya.html",title="第25回北海道地区大会")),{})
        
    def test_no_dated_heading_no_venue(self):
        page = "第7回 名古屋地区大会\n会場\nウインクあいち\nお申し込み締切:2027年2月20日"
        self.assertEqual(parse_jbvp_region(page,event()),{})

    def test_duplicate_url_is_fetched_once(self):
        f=DummyFetcher()
        rows=[event(),event()]
        stats={}
        enrich_jbvp(rows,f,TODAY,stats)
        self.assertEqual(f.calls,[URL])
        self.assertEqual(stats["details_scanned"],1)
        self.assertEqual(stats["venues_found"],2)
        self.assertTrue(all(e["venue"] for e in rows))
        self.assertTrue(all(e["deadline"] is None for e in rows))

    def test_robots_failure_preserves_listing(self):
        class Blocked:
            def get(self,url):raise RuntimeError("robots disallowed")
        rows=[event()]
        stats={}
        enrich_jbvp(rows,Blocked(),TODAY,stats)
        self.assertIsNone(rows[0]["venue"])
        self.assertEqual(stats["detail_fetch_failed"],1)


if __name__=="__main__":
    unittest.main()
