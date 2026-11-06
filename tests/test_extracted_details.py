# -*- coding: utf-8 -*-
import datetime
import unittest
from free_extract import _speakers_in_title, _explicit_deadline, extract_free

TODAY=datetime.date(2026,11,6)

class ExtractDetailsTest(unittest.TestCase):
    def test_lifetail_speaker(self):
        self.assertEqual(_speakers_in_title("犬猫の内視鏡実習 須藤 大輔 先生 ベーシック"),"須藤 大輔")
    def test_gakusai_speaker(self):
        self.assertEqual(_speakers_in_title("手島健次先生「犬と猫の局所麻酔」"),"手島健次")
    def test_vetstech_speaker(self):
        self.assertEqual(_speakers_in_title("【ライブ】慢性腸症治療のその先（秋吉先生）"),"秋吉")
    def test_no_speaker(self):
        self.assertIsNone(_speakers_in_title("愛玩動物看護師のための救急セミナー"))
    def test_deadline_only_explicit_full_year(self):
        self.assertEqual(_explicit_deadline("申込締切：2026年11月9日\n開催日：2026年11月11日"),"2026-11-09")
        self.assertIsNone(_explicit_deadline("開催日：2026年11月11日\n早割：11月8日"))
    def test_metadata_carried_through_validation(self):
        line=("CARD[web] 2026年11月12日 (木) 高橋 香 先生の猫の歯科講座 "
              "受付中 獣医師 <https://www.peppy.jp/seminar/901>")
        rows=extract_free("PEPPY","https://www.peppy.jp/seminar","",line,TODAY,{})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["speaker"],"高橋 香")
if __name__=="__main__":unittest.main()
