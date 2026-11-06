# -*- coding: utf-8 -*-
"""run.py を通しで動かす。通信とAIは疑似。"""
import json, os, sys, tempfile, types, unittest, shutil
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import config, fetcher as fetchmod, run, sources, merge, extract

PAGE_TEXT = ("2026年11月\n獣医師獣医学生 受付中\n第179回国際セミナー「犬猫の内分泌疾患アップデート2026」 "
             "<https://www.jaha.or.jp/training/seminar/vet/endocrine26/>\n東京都 アーバンネット神田カンファレンス\n")
MODEL_OUT = json.dumps([{
    "title": "第179回国際セミナー「犬猫の内分泌疾患アップデート2026」", "start_date": "2026-11-06", "end_date": "2026-11-08",
    "format": "現地", "venue": "アーバンネット神田カンファレンス", "prefecture": "東京都", "audience": ["獣医師"],
    "topics": ["内分泌"], "status": "受付中", "organizer": "JAHA",
    "url": "https://www.jaha.or.jp/training/seminar/vet/endocrine26/",
    "evidence": "第179回国際セミナー「犬猫の内分泌疾患アップデート2026」"}], ensure_ascii=False)


def fake_pages(src, f, months):
    if src["id"] == "jaha":
        yield "https://www.jaha.or.jp/seminar-calendar/", PAGE_TEXT, "hint"
    elif src["id"] == "lifetail":
        raise fetchmod.Blocked("HTTP 403 テスト")
    elif src["id"] == "gakusai":
        raise fetchmod.Disallowed("robots テスト")
    else:
        return iter(())


class E2E(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd(); self.tmp = tempfile.mkdtemp(); os.chdir(self.tmp)
        shutil.copy(os.path.join(ROOT, "template.html"), self.tmp)
        os.makedirs("data")
        shutil.copy(os.path.join(ROOT, "data", "manual_events.csv"), "data")
        config.REQUEST_INTERVAL_SEC = 0
        render_tpl = os.path.join(ROOT, "template.html")
        self.p = [
            mock.patch.object(sources, "pages_for", fake_pages),
            mock.patch.object(run.render, "TEMPLATE", render_tpl),
        ]
        for p in self.p: p.start()
        client = mock.Mock()
        client.messages.create.return_value = mock.Mock(content=[mock.Mock(type="text", text=MODEL_OUT)], stop_reason="end_turn")
        self.client = client
        fake = types.ModuleType("anthropic"); fake.Anthropic = lambda api_key=None: client
        self.mods = mock.patch.dict(sys.modules, {"anthropic": fake}); self.mods.start()
        self.env = mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x", "SEMINAR_RADAR_CONTACT": "a@b.c"}); self.env.start()

    def tearDown(self):
        for p in self.p: p.stop()
        self.mods.stop(); self.env.stop(); os.chdir(self.cwd)

    def test_full_flow(self):
        import datetime
        with mock.patch.object(run, "local_today", return_value=datetime.date(2026, 11, 6)):
            rc = run.main(["--out", "index.html"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists("index.html"))
        store = json.load(open("data/events.json", encoding="utf-8"))["events"]
        self.assertEqual(len(store), 1)
        ev = list(store.values())[0]
        self.assertEqual(ev["source"], "JAHA")
        self.assertEqual(ev["end_date"], "2026-11-08")
        html = open("index.html", encoding="utf-8").read()
        self.assertIn("犬猫の内分泌疾患アップデート2026", html)
        self.assertNotIn("無視される行", html)          # 手動CSVのサンプル行は載らない
        # 2回目はキャッシュで、AIを呼ばない
        calls = self.client.messages.create.call_count
        with mock.patch.object(run, "local_today", return_value=datetime.date(2026, 11, 7)):
            run.main(["--out", "index.html"])
        self.assertEqual(self.client.messages.create.call_count, calls)
        store = json.load(open("data/events.json", encoding="utf-8"))["events"]
        ev = list(store.values())[0]
        self.assertEqual(ev["first_seen"], "2026-11-06"); self.assertEqual(ev["last_seen"], "2026-11-07")
        # --offline は通信なしで作り直せる
        os.remove("index.html")
        run.main(["--offline", "--out", "index.html"])
        self.assertTrue(os.path.exists("index.html"))

    def test_html_payload_is_valid_json(self):
        run.main(["--out", "index.html"])
        html = open("index.html", encoding="utf-8").read()
        s = html.index('id="payload" type="application/json">') + len('id="payload" type="application/json">')
        e = html.index("</script>", s)
        payload = json.loads(html[s:e].replace("<\\/", "</"))
        self.assertIn("events", payload)


if __name__ == "__main__":
    unittest.main(verbosity=1)
