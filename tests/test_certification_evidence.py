# -*- coding: utf-8 -*-
"""Certifications are informational, source-specific and never implied credits."""
import datetime
import pathlib
import unittest

from free_extract import extract_free, _certification_for_meeting
from merge import update_store, dedupe_cross_source

NOW=datetime.date(2026,11,7)
JSVD="https://www.jsvd.jp/"

class CertificationEvidenceTests(unittest.TestCase):
    def test_jsvd_2026_symposium_points_and_registration(self):
        text=(
            "第30回 日本獣医皮膚科学会学術大会\n"
            "日程 | 2027年3月20日（土）・21日（日）\n"
            "一般演題募集 | 2026年9月28日（月）～2027年1月8日（金）\n"
            "日本医真菌学会・日本獣医皮膚科学会・ISHAM WG共催シンポジウム\n"
            "犬と猫の皮膚真菌症\n"
            "日程 | 2026年11月22日（日）\n"
            "参加受付期間 | 2026年8月24日（月）～11月22日（日）15:00\n"
            "参加者には日本獣医皮膚科学会認定医更新評価点10ポイントが付与されます。\n")
        ev=extract_free("日本獣医皮膚科学会",JSVD,"",text,NOW,{})
        by_date={e["start_date"]:e for e in ev}
        self.assertEqual(len(ev),2)
        self.assertEqual(by_date["2026-11-22"]["deadline"],"2026-11-22")
        self.assertIn("10ポイント",by_date["2026-11-22"]["certification_note"])
        self.assertNotIn("10ポイント",by_date["2027-03-20"]["certification_note"])
        self.assertEqual(by_date["2027-03-20"]["abstract_deadline"],"2027-01-08")
        self.assertIsNone(by_date["2027-03-20"]["deadline"])

    def test_point_claim_requires_its_own_evidence(self):
        note,url=_certification_for_meeting(
            "jsvd","日本医真菌学会・日本獣医皮膚科学会・ISHAM WG共催シンポジウム",
            "2026-11-22",["参加受付期間 2026年8月24日～11月22日"])
        self.assertIsNone(note)
        self.assertIsNone(url)

    def test_points_not_carried_to_next_event(self):
        text=("日本医真菌学会・日本獣医皮膚科学会・ISHAM WG共催シンポジウム\n"
              "日程 | 2026年11月22日\n"
              "AiANZ 獣医皮膚科シンポジウム with ひふゼミ\n"
              "認定医更新評価点10ポイント\n")
        ev=extract_free("日本獣医皮膚科学会",JSVD,"",text,NOW,{})
        self.assertEqual(len(ev),1)
        self.assertIsNone(ev[0]["certification_note"])

    def test_jsvc_course_info_is_not_claim_of_earned_points(self):
        note,link=_certification_for_meeting(
           "jsvc","第125回日本獣医循環器学会定例大会","2026-12-19",[])
        self.assertIn("認定医講習会",note)
        self.assertNotIn("取得できる",note)
        self.assertIn("session2026",link)

    def test_javnu_conditions_not_personal_credit_claim(self):
        note,url=_certification_for_meeting(
          "javnu","第19回学術集会・総会","2027-08-21",[])
        self.assertIn("出席",note)
        self.assertIn("条件",note)

    def test_notes_survive_storage_and_dedupe(self):
        text=("第125回日本獣医循環器学会定例大会\n"
              "会期\n2026年12月19日（土）・20日（日）\n"
              "会場\nパピヨン24")
        result=extract_free("日本獣医循環器学会",
            "https://www.jsvc.jp/meeting/regular/conf125/","",text,NOW,{})
        self.assertEqual(len(result),1)
        self.assertTrue(result[0]["certification_note"])
        stored={}
        update_store(stored,result,{"id":"jsvc","name":"日本獣医循環器学会"},None,NOW)
        self.assertEqual(next(iter(stored.values()))["certification_url"],
                         result[0]["certification_url"])
        self.assertEqual(dedupe_cross_source(list(stored.values()))[0]["certification_note"],
                         result[0]["certification_note"])

    def test_ui_includes_provenance_and_lark_option(self):
        ui=pathlib.Path("template.html").read_text(encoding="utf-8")
        self.assertIn("制度の公式情報",ui)
        self.assertIn('id="oCert"',ui)
        self.assertIn("認定医関連",ui)

if __name__=="__main__":
    unittest.main()
