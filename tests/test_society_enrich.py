# -*- coding: utf-8 -*-
"""Site-specific JSV Cardiology courses, and multiline JSVD registration dates."""
import datetime
import unittest
from free_extract import extract_free
from society_enrich import enrich_jsvc, parse_jsvc_certification_program, parse_jsvc_meeting_venue, JSVC_COURSES_URL
from merge import update_store, dedupe_cross_source

NOW=datetime.date(2026,11,7)
SCHEDULE="""2026年度 認定医講習会
第124回 定例大会
日時：2026年7月4、5日
講座番号
講座名
講師名
12
正常心電図
福島
第125回　定例大会
日時：2026年12月19、20日
会場：パピヨン24ガスホール（福岡）
講座番号
講座名
講師名
22
感染性心内膜炎：
町田
23
犬のフィラリア症：
青木
34
心臓腫瘍・心膜疾患：
杉本
アドバンスコース
分野/番号
講座名
講師名
基礎4
心血管疾患治療の先端技術：人工臓器／再生医療
中尾 周
臨床20
循環器疾患のCT検査
合屋 征二郎
臨床21
猫の心臓外科
菅野 信之
臨床22
腫瘍循環器病学～心疾患と担癌動物～
佐藤 恵一
日本獣医循環器学会事務局
"""
def e(date="2026-12-19",name="第125回日本獣医循環器学会定例大会"):
    return {"title":name,"start_date":date,
            "url":"https://www.jsvc.jp/meeting/regular/conf125/",
            "source_id":"jsvc","certification_program":None,
            "certification_note":None}
class Fake:
    def __init__(self,value):self.value=value;self.calls=[]
    def get(self,url):
        self.calls.append(url)
        return "<article><p>" + self.value.replace("\n","</p><p>") + "</p></article>"

class CertificationProgramTests(unittest.TestCase):
    def test_2026_meeting_courses_only(self):
        program=parse_jsvc_certification_program(SCHEDULE,e())
        self.assertIn("講座22 感染性心内膜炎",program)
        self.assertIn("講座23 犬のフィラリア症",program)
        self.assertIn("講座34 心臓腫瘍・心膜疾患",program)
        self.assertIn("臨床20 循環器疾患のCT検査",program)
        self.assertNotIn("正常心電図",program)
    def test_other_meeting_does_not_receive_schedule(self):
        self.assertIsNone(parse_jsvc_certification_program(SCHEDULE,e("2027-12-19")))
        self.assertIsNone(parse_jsvc_certification_program(SCHEDULE,e(name="第126回定例大会")))
    def test_course_number_without_title_not_enough(self):
        bad=SCHEDULE.replace("犬のフィラリア症","小動物皮膚科学")
        self.assertIsNone(parse_jsvc_certification_program(bad,e()))
    def test_enrich_and_store(self):
        f=Fake(SCHEDULE)
        rows=[e()]
        stat={}
        enrich_jsvc(rows,f,NOW,stat)
        self.assertEqual(f.calls,[JSVC_COURSES_URL,
                                  "https://www.jsvc.jp/meeting/regular/conf125/entry125/"])
        self.assertEqual(stat["certification_programs_found"],1)
        self.assertEqual(stat["venues_found"],1)
        self.assertEqual(rows[0]["venue"],"パピヨン24ガスホール(福岡)")
        store={}
        update_store(store,rows,{"id":"jsvc","name":"日本獣医循環器学会"},None,NOW)
        value=next(iter(store.values()))
        self.assertIn("講座22",value["certification_program"])
        self.assertIn("アドバンス",dedupe_cross_source(list(store.values()))[0]["certification_program"])
    def test_venue_from_confirmed_meeting_only(self):
        self.assertEqual(
            parse_jsvc_meeting_venue(SCHEDULE,e()),
            {"venue":"パピヨン24ガスホール(福岡)","prefecture":"福岡県"}
        )
        self.assertEqual(parse_jsvc_meeting_venue(SCHEDULE,e("2027-12-19")),{})

    def test_does_not_borrow_prior_meeting_venue(self):
        text=SCHEDULE.replace("会場：パピヨン24ガスホール（福岡）", "")
        text=text.replace("第124回 定例大会",
                          "第124回 定例大会\\n会場：前大会の会場")
        self.assertEqual(parse_jsvc_meeting_venue(text,e()),{})

    def test_ambiguous_venue_is_ignored_and_existing_preserved(self):
        text=SCHEDULE.replace("会場：パピヨン24ガスホール（福岡）",
                              "会場：パピヨン24ガスホール（福岡）\\n会場：別会場")
        self.assertEqual(parse_jsvc_meeting_venue(text,e()),{})
        existing=e()
        existing["venue"]="既存の正式会場"
        got=parse_jsvc_meeting_venue(SCHEDULE,existing)
        self.assertNotIn("venue",got)

    def test_blocked_page_preserves_meeting(self):
        class Denied:
            def get(self,url):raise RuntimeError("robots")
        row=e();stat={}
        enrich_jsvc([row],Denied(),NOW,stat)
        self.assertIsNone(row["certification_program"])
        self.assertEqual(stat["certification_detail_failed"],1)

class RegistrationDateTests(unittest.TestCase):
    def test_split_table_cells(self):
        text=("日本医真菌学会・日本獣医皮膚科学会・ISHAM WG共催シンポジウム\n"
              "犬と猫の皮膚真菌症\n"
              "日 程\n2026 年 11 月 22 日（日）\n"
              "会 場\n東京たま未来メッセ\n"
              "参加受付期間\n2026 年 8 月 24 日（月）～\n"
              "11 月 22 日（日）15:00\n"
              "参加ご希望の方は申込ください\n")
        events=extract_free("日本獣医皮膚科学会","https://www.jsvd.jp/","",text,NOW,{})
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]["deadline"],"2026-11-22")
    def test_abstract_or_membership_deadline_not_participation(self):
        text=("日本医真菌学会・日本獣医皮膚科学会・ISHAM WG共催シンポジウム\n"
              "日程\n2026年11月22日\n"
              "一般演題募集\n2026年8月1日～2026年11月1日\n")
        events=extract_free("日本獣医皮膚科学会","https://www.jsvd.jp/","",text,NOW,{})
        self.assertEqual(len(events),1)
        self.assertIsNone(events[0]["deadline"])
if __name__=="__main__":unittest.main()
