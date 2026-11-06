# -*- coding: utf-8 -*-
"""Regression examples based on the formats seen in the 2026-11-06 run."""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extract import html_to_text
from free_extract import extract_free
from sources import _jaha_table_text
from merge import reconcile_source

TODAY = datetime.date(2026, 11, 6)


class Dates(unittest.TestCase):
    def test_lifetail_card_owned_dates_and_times(self):
        page = "https://life-tail.com/seminars/?status=open"
        cards = [
            ("無料 無料ライブ｜成犬のストレスサインと、動物病院でできるサポート 第1回｜無料ライブ 2026.12.01 20:00〜21:30 ライブ", "https://bah.life-tail.com/20261201/", "2026-12-01", "20:00"),
            ("残り3席 猫の心エコー実習セミナー 第1回｜ついに実現！猫の心エコー実習セミナー 2027.01.17 13:00〜16:00 実習", "https://life-tail.com/seminars/1775/", "2027-01-17", "13:00"),
            ("＜博多開催＞内視鏡の基本操作を身に着ける操作技能アップ実習セミナー 第1回｜午前 2027.01.21 10:00〜13:00 実習", "https://life-tail.com/seminars/1772/", "2027-01-21", "10:00"),
            ("＜博多開催＞内視鏡の基本操作を身に着ける操作技能アップ実習セミナー 第1回｜午後 2027.01.21 14:30〜17:30 実習", "https://life-tail.com/seminars/1773/", "2027-01-21", "14:30"),
        ]
        html = "<main>" + "".join('<a href="{}">{}</a>'.format(u, t) for t,u,_,_ in cards) + "</main>"
        stats = {}
        rows = extract_free("Life&Tail", page, "", html_to_text(html, page), TODAY, stats)
        by_url = {e["url"]: e for e in rows}
        self.assertEqual(len(by_url), 4)
        for _, url, d, start_time in cards:
            with self.subTest(url=url):
                self.assertEqual(by_url[url]["start_date"], d)
                self.assertEqual(by_url[url]["start_time"], start_time)
                self.assertTrue(by_url[url]["verified"])
        self.assertEqual(by_url["https://bah.life-tail.com/20261201/"]["format"], "ライブ配信")

    def test_lifetail_does_not_borrow_neighbor_date(self):
        p="https://life-tail.com/seminars/"
        html='<a href="/seminars/1">犬猫の内科セミナー</a><a href="/seminars/2">獣医の外科実習 2027.02.16 14:30〜17:30 実習</a>'
        rows=extract_free("Life&Tail",p,"",html_to_text(html,p),TODAY,{})
        self.assertEqual(len(rows),2)
        self.assertIsNone(next(e for e in rows if e["url"].endswith("/1"))["start_date"])
        self.assertEqual(next(e for e in rows if e["url"].endswith("/2"))["start_date"],"2027-02-16")

    def test_vetstech_url_post_date_does_not_become_event_date(self):
        p="https://vets-tech.jp/feed/"
        url="https://vets-tech.jp/2026/10/27/vets-tech-web-seminar-vol83/116565/"
        article=f"=====\n記事タイトル: 【ライブ】腫瘍科医からみた慢性腸症治療のその先\n記事URL: <{url}>\n公開日: 2026-10-27\n参加登録はこちら <{url}>\n申込締切: 2026年11月2日\n開催日は後日発表\n"
        rows=extract_free("VETS TECH",p,"",article,TODAY,{})
        self.assertEqual(len(rows),1)
        self.assertIsNone(rows[0]["start_date"])
        self.assertFalse(rows[0]["verified"])

    def test_vetstech_prefers_labeled_date_over_deadline(self):
        p="https://vets-tech.jp/feed/"
        article="=====\n記事タイトル: 眼科検査の手技を学ぶ実習セミナー\n記事URL: <https://vets-tech.jp/2026/11/04/eye/123/>\n公開日: 2026-11-04\n申込締切：2026年11月25日\n開催日時\n2027年1月17日（日）13:00〜16:00 東京\n"
        rows=extract_free("VETS TECH",p,"",article,TODAY,{})
        self.assertEqual(rows[0]["start_date"],"2027-01-17")
        self.assertEqual(rows[0]["start_time"],"13:00")

    def test_calendar_table_row_association(self):
        p="https://www.jaha.or.jp/seminar-calendar/page/2026/11"
        html='''<h2>2026年11月</h2><table><tr><th>日付</th><th>対象</th><th>セミナー名</th><th>場所</th></tr>
        <tr><td>11/18 水</td><td>獣医師 受付中</td><td><a href="/course/endo">犬と猫の内分泌アップデート講座</a></td><td>東京都</td></tr>
        <tr><td>11/22 日</td><td>看護師 受付中</td><td><a href="/course/nurse">愛玩動物看護師の救急対応実習</a></td><td>大阪府</td></tr></table>'''
        text=_jaha_table_text(html,p)
        self.assertIsNotNone(text)
        rows=extract_free("JAHA",p,"",text,TODAY,{})
        self.assertEqual(len(rows),2)
        self.assertEqual({e["start_date"] for e in rows},{"2026-11-18","2026-11-22"})

    def test_reconcile_removes_wrong_old_date(self):
        src={"id":"lifetail","name":"Life&Tail"}
        old={"stale": {"source_id":"lifetail","source":"Life&Tail","start_date":"2027-01-17","title":"内視鏡実習","id":"stale"},
             "other": {"source_id":"gakusai","source":"学際企画","start_date":"2027-02-18","title":"別イベント"}}
        fresh=[{"title":"内視鏡実習","start_date":"2027-01-21","url":"https://life-tail.com/seminars/1772/","verified":True}]
        add,update,replaced=reconcile_source(old,fresh,src,TODAY)
        self.assertEqual((add,update,replaced),(1,0,1))
        self.assertNotIn("stale",old)
        self.assertIn("other",old)
        self.assertTrue(any(v.get("source_id")=="lifetail" and v.get("start_date")=="2027-01-21" for v in old.values()))

if __name__ == "__main__": unittest.main()
