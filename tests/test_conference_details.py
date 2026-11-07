# -*- coding: utf-8 -*-
"""Separate participant/abstract deadlines and validate deep-link provenance."""
import datetime
import unittest
from free_extract import extract_free, _jbvp_detail_url
from merge import update_store, dedupe_cross_source

NOW = datetime.date(2026,11,7)
JSVD = "https://www.jsvd.jp/"

class TestConferenceDetails(unittest.TestCase):
    def test_abstract_vs_registration_deadlines_are_different(self):
        text=(
            "第30回 日本獣医皮膚科学会学術大会\n"
            "日 程 | 2027 年 3 月 20 日（土）・21日（日）\n"
            "会 場 | TOC有明\n"
            "一般演題募集 | 2026 年 9 月 28 日（月）～ 2027 年 1 月 8 日（金）\n"
            "日本医真菌学会・日本獣医皮膚科学会・ISHAM WG共催シンポジウム\n"
            "日 程 | 2026 年 11 月 22 日（日）\n"
            "参加受付期間 | 2026 年 8 月 24 日（月）～ 11 月 22 日（日）15:00\n"
        )
        got=extract_free("日本獣医皮膚科学会",JSVD,"",text,NOW,{})
        self.assertEqual(len(got),2)
        by_date={g["start_date"]:g for g in got}
        congress=by_date["2027-03-20"]
        symposium=by_date["2026-11-22"]
        self.assertEqual(congress["abstract_deadline"],"2027-01-08")
        self.assertIsNone(congress["deadline"])
        self.assertEqual(congress["detail_url"],"https://www.jsvd.jp/topics/30meeting/announcement.html")
        self.assertEqual(symposium["deadline"],"2026-11-22")
        self.assertIsNone(symposium["abstract_deadline"])
        self.assertEqual(symposium["detail_url"],"https://2026.jsmm.org/")

    def test_abstract_deadline_not_stolen_from_other_meeting(self):
        text=("第30回 日本獣医皮膚科学会学術大会\n"
              "日程 | 2027年3月20日\n"
              "日本医真菌学会・日本獣医皮膚科学会・ISHAM WG共催シンポジウム\n"
              "日程 | 2026年11月22日\n"
              "一般演題募集 | 2026年9月1日～2026年10月1日\n")
        e=extract_free("日本獣医皮膚科学会",JSVD,"",text,NOW,{})
        self.assertIsNone(next(x for x in e if x["start_date"]=="2027-03-20")["abstract_deadline"])

    def test_deep_links_only_matching_current_conference(self):
        self.assertEqual(_jbvp_detail_url("第7回 名古屋地区大会","2027-02-28"),
                         "https://www.jbvp.org/regional/nagoya.html")
        self.assertIsNone(_jbvp_detail_url("第7回 名古屋地区大会","2028-03-05"))
        self.assertIsNone(_jbvp_detail_url("第29回 年次大会2027","2027-09-25"))

    def test_jbvp_region_venue_from_exact_listing_card(self):
        text = (
            "第7回 名古屋地区大会\n"
            "日程：\n2027年2月28日(日)\n"
            "会場：\nウインクあいち（愛知県産業労働センター）\n"
            "第20回 京都地区大会\n"
            "日程：2027年3月7日(日)\n"
            "会場：TKPガーデンシティ京都タワーホテル\n"
            "第23回 九州地区大会\n"
            "日程：\n2027年3月21日(日)\n"
            "会場：\n福岡国際会議場\n"
        )
        events = extract_free("JBVP", "https://www.jbvp.org/vn/", "", text, NOW, {})
        self.assertEqual(len(events), 3)
        venues = {e["start_date"]: e["venue"] for e in events}
        self.assertEqual(venues["2027-02-28"], "ウインクあいち（愛知県産業労働センター）")
        self.assertEqual(venues["2027-03-07"], "TKPガーデンシティ京都タワーホテル")
        self.assertEqual(venues["2027-03-21"], "福岡国際会議場")

    def test_jbvp_venue_not_borrowed_from_next_meeting(self):
        text = (
            "第7回 名古屋地区大会\n"
            "日程：2027年2月28日(日)\n"
            "第20回 京都地区大会\n"
            "日程：2027年3月7日(日)\n"
            "会場：TKPガーデンシティ京都タワーホテル\n"
        )
        events = extract_free("JBVP", "https://www.jbvp.org/vn/", "", text, NOW, {})
        self.assertEqual(len(events), 2)
        self.assertIsNone(events[0]["venue"])
        self.assertEqual(events[1]["venue"], "TKPガーデンシティ京都タワーホテル")

    def test_jbvp_online_delivery_is_not_a_physical_venue(self):
        text = (
            "地区大会 2027（オンラインプログラム）\n"
            "日程：2027年4月1日～2027年6月30日\n"
            "会場：オンライン配信\n"
        )
        events = extract_free("JBVP", "https://www.jbvp.org/vn/", "", text, NOW, {})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["format"], "オンデマンド")
        self.assertIsNone(events[0]["venue"])
        self.assertIsNone(events[0]["prefecture"])

    def test_jbvp_online_does_not_copy_adjacent_onsite_venue(self):
        text = (
            "地区大会 2027（オンラインプログラム）\n"
            "日程：2027年4月1日～2027年6月30日\n"
            "会場：オンライン配信\n"
            "第29回 年次大会2027\n"
            "日程：2027年9月25日～26日\n"
            "会場：ホテルニューオータニ\n"
        )
        events = extract_free("JBVP", "https://www.jbvp.org/forum/", "", text, NOW, {})
        self.assertEqual(len(events), 2)
        online = next(e for e in events if "オンライン" in e["title"])
        onsite = next(e for e in events if "年次大会" in e["title"])
        self.assertIsNone(online["venue"])
        self.assertEqual(onsite["venue"], "ホテルニューオータニ")

    def test_jbvp_venue_rejected_without_date_label(self):
        text = (
            "第7回 名古屋地区大会\n"
            "2027年2月28日(日)\n"
            "会場：ウインクあいち\n"
        )
        events = extract_free("JBVP", "https://www.jbvp.org/vn/", "", text, NOW, {})
        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0]["venue"])

    def test_jbvp_link_survives_extraction_and_store(self):
        text="第7回 名古屋地区大会\n日程：\n2027年2月28日(日)\n会場：ウインクあいち"
        e=extract_free("JBVP","https://www.jbvp.org/vn/","",text,NOW,{})
        self.assertEqual(len(e),1)
        self.assertEqual(e[0]["detail_url"],"https://www.jbvp.org/regional/nagoya.html")
        store={}
        update_store(store,e,{"id":"jbvp","name":"JBVP"},None,NOW)
        saved=next(iter(store.values()))
        self.assertEqual(saved["detail_url"],e[0]["detail_url"])

    def test_abstract_deadline_survives_store_and_dedupe(self):
        text="第30回 日本獣医皮膚科学会学術大会\n日程 | 2027年3月20日\n一般演題募集 | 2026年9月28日～2027年1月8日"
        e=extract_free("日本獣医皮膚科学会",JSVD,"",text,NOW,{})
        store={}
        update_store(store,e,{"id":"jsvd","name":"日本獣医皮膚科学会"},None,NOW)
        saved=next(iter(store.values()))
        self.assertEqual(saved["abstract_deadline"],"2027-01-08")
        self.assertEqual(dedupe_cross_source(list(store.values()))[0]["abstract_deadline"],"2027-01-08")
if __name__=="__main__":unittest.main()
