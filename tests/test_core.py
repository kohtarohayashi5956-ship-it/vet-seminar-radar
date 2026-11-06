# -*- coding: utf-8 -*-
import datetime, json, os, sys, tempfile, unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config, extract, merge, sources
from fetcher import Fetcher, Blocked, Disallowed

TODAY = datetime.date(2026, 11, 6)

JAHA_HTML = """<html><body><nav><a href="/x">メニュー</a></nav><main>
<a href="/seminar-calendar/page/2026/10">前月</a><h2>2026年11月</h2>
<a href="/seminar-calendar/page/2026/12">次月</a>
<table><tr><td>11/6</td><td>金</td><td>獣医師獣医学生</td><td>受付中</td>
<td><a href="/training/seminar/vet/endocrine26/">第179回国際セミナー「犬猫の内分泌疾患アップデート2026」</a></td>
<td>東京都</td><td>アーバンネット神田カンファレンス</td></tr></table></main>
<footer>フッター</footer></body></html>"""


class TextTests(unittest.TestCase):
    def test_html_to_text_keeps_links_and_drops_nav_footer(self):
        t = extract.html_to_text(JAHA_HTML, "https://www.jaha.or.jp/seminar-calendar/")
        self.assertIn("<https://www.jaha.or.jp/training/seminar/vet/endocrine26/>", t)
        self.assertIn("2026年11月", t)
        self.assertNotIn("フッター", t)
        self.assertNotIn("メニュー", t)

    def test_split_text(self):
        text = "\n".join(["あ" * 100] * 50)
        chunks = extract.split_text(text, limit=1000)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("\n".join(chunks).count("あ"), 5000)

    def test_parse_json_array_variants(self):
        self.assertEqual(len(extract.parse_json_array('```json\n[{"a":1},{"b":2}]\n```')), 2)
        # 途中で切れた出力でも、完成した要素だけ拾う
        self.assertEqual(extract.parse_json_array('[{"a":1},{"b":2},{"c":"途中')[:2], [{"a": 1}, {"b": 2}])
        self.assertEqual(extract.parse_json_array("説明だけ"), [])


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.text = extract.html_to_text(JAHA_HTML, "https://www.jaha.or.jp/seminar-calendar/")
        self.page = "https://www.jaha.or.jp/seminar-calendar/"

    def run_v(self, items):
        stats = {}
        return extract.validate(items, self.text, self.page, TODAY, stats), stats

    def test_valid_event_is_verified(self):
        out, _ = self.run_v([{
            "title": "第179回国際セミナー「犬猫の内分泌疾患アップデート2026」", "start_date": "2026-11-06",
            "format": "現地", "audience": ["獣医師", "不正な値"], "topics": ["内分泌", "存在しない分野"],
            "url": "https://www.jaha.or.jp/training/seminar/vet/endocrine26/",
            "evidence": "第179回国際セミナー「犬猫の内分泌疾患アップデート2026」"}])
        e = out[0]
        self.assertTrue(e["verified"])
        self.assertEqual(e["audience"], ["獣医師"])
        self.assertEqual(e["topics"], ["内分泌"])
        self.assertFalse(e["url_is_page"])

    def test_hallucinated_title_is_dropped(self):
        out, stats = self.run_v([{"title": "本文に存在しない架空のセミナー", "start_date": "2026-11-20",
                                  "evidence": "どこにもない文章です"}])
        self.assertEqual(out, [])
        self.assertEqual(stats["dropped_not_in_text"], 1)

    def test_unknown_url_falls_back_to_page(self):
        out, _ = self.run_v([{"title": "第179回国際セミナー「犬猫の内分泌疾患アップデート2026」",
                              "start_date": "2026-11-06", "url": "https://evil.example.com/x",
                              "evidence": "第179回国際セミナー"}])
        self.assertEqual(out[0]["url"], self.page)
        self.assertTrue(out[0]["url_is_page"])

    def test_bad_dates_and_far_dates(self):
        out, _ = self.run_v([
            {"title": "第179回国際セミナー「犬猫の内分泌疾患アップデート2026」", "start_date": "2026-13-45",
             "evidence": "第179回国際セミナー"},
        ])
        self.assertIsNone(out[0]["start_date"])
        out, _ = self.run_v([
            {"title": "第179回国際セミナー「犬猫の内分泌疾患アップデート2026」", "start_date": "2031-01-01",
             "evidence": "第179回国際セミナー"}])
        self.assertFalse(out[0]["verified"])           # 範囲外の日付は「要確認」

    def test_end_before_start_cleared_and_dupe_removed(self):
        t = "第179回国際セミナー「犬猫の内分泌疾患アップデート2026」"
        out, _ = self.run_v([
            {"title": t, "start_date": "2026-11-06", "end_date": "2026-11-01", "evidence": t},
            {"title": t, "start_date": "2026-11-06", "evidence": t}])
        self.assertEqual(len(out), 1)
        self.assertIsNone(out[0]["end_date"])

    def test_time_normalization(self):
        t = "第179回国際セミナー「犬猫の内分泌疾患アップデート2026」"
        out, _ = self.run_v([{"title": t, "start_date": "2026-11-06", "start_time": "9:30", "end_time": "25:00",
                              "evidence": t}])
        self.assertEqual(out[0]["start_time"], "09:30")
        self.assertIsNone(out[0]["end_time"])


class MergeTests(unittest.TestCase):
    def ev(self, **kw):
        base = dict(title="t", start_date="2026-11-10", end_date=None, audience=[], topics=[], verified=True,
                    url_is_page=False, source="A", source_id="a")
        base.update(kw); return base

    def test_cross_source_dedupe_merges_fields(self):
        a = self.ev(title="第179回JAHA国際セミナー 犬猫の内分泌疾患アップデート2026", source="JAHA",
                    status="受付中", audience=["獣医師"])
        b = self.ev(title="第179回国際セミナー「犬猫の内分泌疾患アップデート2026」", source="Life&Tail",
                    price="50,000円", organizer="JAHA")
        c = self.ev(title="全く別のセミナー", source="VETS TECH")
        out = merge.dedupe_cross_source([a, b, c])
        self.assertEqual(len(out), 2)
        m = [x for x in out if "内分泌" in x["title"]][0]
        self.assertEqual(m["price"], "50,000円")
        self.assertEqual(m["status"], "受付中")
        self.assertTrue(m["also_listed"])

    def test_different_dates_not_merged(self):
        a = self.ev(title="シニアケア講座 第1回", start_date="2026-11-12")
        b = self.ev(title="シニアケア講座 第2回", start_date="2026-12-10")
        self.assertEqual(len(merge.dedupe_cross_source([a, b])), 2)

    def test_purge(self):
        store = {
            "old": self.ev(start_date="2026-08-01", last_seen="2026-11-01"),
            "recent": self.ev(start_date="2026-10-20", last_seen="2026-11-01"),
            "future": self.ev(start_date="2027-01-10", last_seen="2026-11-01"),
            "undated_old": self.ev(start_date=None, last_seen="2026-09-01"),
            "undated_new": self.ev(start_date=None, last_seen="2026-11-01"),
        }
        merge.purge(store, TODAY)
        self.assertEqual(sorted(store), ["future", "recent", "undated_new"])

    def test_update_store_preserves_first_seen(self):
        store = {}
        src = {"id": "a", "name": "A"}
        fresh = [dict(title="X", start_date="2026-12-01", audience=[], topics=[])]
        merge.update_store(store, fresh, src, None, datetime.date(2026, 11, 1))
        merge.update_store(store, fresh, src, None, datetime.date(2026, 11, 6))
        rec = list(store.values())[0]
        self.assertEqual(rec["first_seen"], "2026-11-01")
        self.assertEqual(rec["last_seen"], "2026-11-06")

    def test_manual_csv(self):
        d = tempfile.mkdtemp()
        old = merge.MANUAL_PATH
        merge.MANUAL_PATH = os.path.join(d, "m.csv")
        with open(merge.MANUAL_PATH, "w", encoding="utf-8-sig") as f:
            f.write("title,start_date,end_date,start_time,end_time,format,venue,prefecture,audience,topics,price,status,deadline,organizer,url,note\n")
            f.write("（例）無視される行,2026-12-05,,,,現地,,,,,,,,,,\n")
            f.write("手動の講習会,2026-12-05,,10:00,12:00,ライブ配信,,,獣医師・動物看護師,内科,無料,受付中,,EDUWARD Press,https://example.com/a,\n")
        try:
            rows = merge.load_manual(TODAY)
        finally:
            merge.MANUAL_PATH = old
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["audience"], ["獣医師", "動物看護師"])
        self.assertTrue(rows[0]["is_free"])


class SourcesTests(unittest.TestCase):
    def test_jaha_follows_next_month(self):
        pages = {"https://www.jaha.or.jp/seminar-calendar/": JAHA_HTML,
                 "https://www.jaha.or.jp/seminar-calendar/page/2026/12": "<html><body><h2>2026年12月</h2><a>次月</a></body></html>"}
        f = mock.Mock(); f.get.side_effect = lambda u: pages[u]
        got = list(sources.jaha_pages({"start_url": "https://www.jaha.or.jp/seminar-calendar/"}, f, 3))
        self.assertEqual(len(got), 2)       # 次月リンクがなくなったら止まる
        self.assertIn("2026年12月", got[1][1])

    def test_jaha_skips_prior_month_without_consuming_horizon(self):
        urls = ["https://www.jaha.or.jp/seminar-calendar/",
                "https://www.jaha.or.jp/seminar-calendar/11",
                "https://www.jaha.or.jp/seminar-calendar/12"]
        pages = {
            urls[0]: '<h2>2026年10月</h2><a href="/seminar-calendar/11">次月</a>',
            urls[1]: '<h2>2026年11月</h2><a href="/seminar-calendar/12">次月</a>',
            urls[2]: '<h2>2026年12月</h2>'
        }
        f = mock.Mock(); f.get.side_effect = lambda u: pages[u]
        with mock.patch.object(sources.datetime, "datetime", wraps=datetime.datetime) as dt:
            dt.now.return_value = datetime.datetime(2026, 11, 6, tzinfo=datetime.timezone.utc)
            got = list(sources.jaha_pages({"start_url": urls[0]}, f, 2))
        self.assertEqual(len(got), 2)
        self.assertIn("2026年11月", got[0][1]); self.assertIn("2026年12月", got[1][1])

    def test_feed_filters_by_category_and_age(self):
        rss = """<?xml version="1.0" encoding="UTF-8"?><rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>【ライブ】腫瘍科医からみた慢性腸症</title><link>https://vets-tech.jp/a/</link><pubDate>Tue, 27 Oct 2026 03:00:00 +0000</pubDate>
<category>セミナー</category><content:encoded><![CDATA[<p>2026年11月20日(金) 20:00〜21:30 ライブ配信。申込はこちら。この記事の本文はある程度の長さが必要なので、ここに補足説明を書きます。"""+"あ"*300+"""</p>]]></content:encoded></item>
<item><title>文献ニュース</title><link>https://vets-tech.jp/b/</link><pubDate>Tue, 27 Oct 2026 03:00:00 +0000</pubDate><category>文献ニュース</category></item>
<item><title>古いセミナー</title><link>https://vets-tech.jp/c/</link><pubDate>Mon, 01 Jan 2024 03:00:00 +0000</pubDate><category>セミナー</category></item>
</channel></rss>"""
        f = mock.Mock(); f.get.return_value = rss
        src = {"feed": "https://vets-tech.jp/feed/", "category_contains": "セミナー", "max_items": 10, "max_age_days": 100000}
        # 古い記事は max_age_days で落ちる設定を別途確認
        got = list(sources.feed_pages(dict(src, max_age_days=120), f))
        self.assertEqual(len(got), 1)
        text = got[0][1]
        self.assertIn("腫瘍科医からみた慢性腸症", text)
        self.assertIn("<https://vets-tech.jp/a/>", text)
        self.assertNotIn("文献ニュース", text)
        self.assertNotIn("古いセミナー", text)


class FetcherTests(unittest.TestCase):
    def resp(self, code, text=""):
        r = mock.Mock(); r.status_code = code; r.text = text; r.encoding = "utf-8"; r.apparent_encoding = "utf-8"
        return r

    def make(self, responses):
        config.REQUEST_INTERVAL_SEC = 0
        f = Fetcher()
        f.session = mock.Mock(); f.session.get.side_effect = responses
        return f

    def test_robots_disallow_blocks_fetch(self):
        f = self.make([self.resp(200, "User-agent: *\nDisallow: /private/")])
        with self.assertRaises(Disallowed):
            f.get("https://example.com/private/page")

    def test_robots_403_is_treated_as_deny(self):
        f = self.make([self.resp(403)])
        with self.assertRaises(Disallowed):
            f.get("https://example.com/x")

    def test_no_robots_allows_and_403_page_is_blocked_without_retry(self):
        f = self.make([self.resp(404), self.resp(403)])
        with self.assertRaises(Blocked):
            f.get("https://example.com/x")
        self.assertEqual(f.session.get.call_count, 2)    # robots.txt と本体の1回ずつだけ（再試行しない）

    def test_ok_page(self):
        f = self.make([self.resp(404), self.resp(200, "<html>" + "a" * 2000 + "</html>")])
        self.assertIn("aaaa", f.get("https://example.com/x"))


class ExtractorFlowTests(unittest.TestCase):
    def test_cache_prevents_second_api_call(self):
        d = tempfile.mkdtemp(); cwd = os.getcwd(); os.chdir(d)
        try:
            client = mock.Mock()
            body = '[{"title":"第179回国際セミナー","start_date":"2026-11-06","evidence":"第179回国際セミナー"}]'
            client.messages.create.return_value = mock.Mock(
                content=[mock.Mock(type="text", text=body)], stop_reason="end_turn")
            ex = extract.Extractor(client)
            text = "第179回国際セミナー 東京都 11/6"
            r1 = ex.extract("JAHA", "https://x/", "h", text, TODAY, {})
            r2 = ex.extract("JAHA", "https://x/", "h", text, TODAY, {})
            self.assertEqual(client.messages.create.call_count, 1)
            self.assertEqual(len(r1), 1); self.assertEqual(len(r2), 1)
            # 本文が変わると再度呼ぶ
            ex.extract("JAHA", "https://x/", "h", text + " 追記", TODAY, {})
            self.assertEqual(client.messages.create.call_count, 2)
        finally:
            os.chdir(cwd)

    def test_no_client_skips_uncached(self):
        d = tempfile.mkdtemp(); cwd = os.getcwd(); os.chdir(d)
        try:
            stats = {}
            out = extract.Extractor(None).extract("JAHA", "https://x/", "h", "本文", TODAY, stats)
            self.assertEqual(out, []); self.assertEqual(stats["skipped_no_ai"], 1)
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main(verbosity=1)
