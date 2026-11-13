# -*- coding: utf-8 -*-
"""JVCS certification notes require the current meeting's own evidence."""
import unittest
from free_extract import _certification_for_meeting

CURRENT_NOTICE = [
    "第35回日本獣医がん学会は、2027年1月30日(土)、31日(日)開催",
    "日本獣医がん学会 認定資格にかかわる証明取得について",
    "本学会の認定医資格に関する受講証明・出席証明は会場でのみ押印いたします。",
    "オンラインでは録画配信を視聴できますが、証明の取得はできません。",
]


class JvcsCertificateNoticeTests(unittest.TestCase):
    def test_venue_only_policy_attached_to_current_meeting(self):
        note, url = _certification_for_meeting(
            "jvcs", "第35回日本獣医がん学会", "2027-01-30", CURRENT_NOTICE)
        self.assertIn("会場のみ", note)
        self.assertIn("オンライン", note)
        self.assertEqual(url, "https://www.jvcs.jp/society/")

    def test_no_note_if_notice_missing(self):
        note, url = _certification_for_meeting(
            "jvcs", "第35回日本獣医がん学会", "2027-01-30",
            ["録画配信を予定しています"])
        self.assertIsNone(note)
        self.assertIsNone(url)

    def test_not_carried_to_next_meeting(self):
        note, url = _certification_for_meeting(
            "jvcs", "第36回日本獣医がん学会", "2027-07-03", CURRENT_NOTICE)
        self.assertIsNone(note)
        self.assertIsNone(url)

    def test_other_societies_unaffected(self):
        note, url = _certification_for_meeting(
            "jsvd", "第35回日本獣医がん学会", "2027-01-30", CURRENT_NOTICE)
        self.assertIsNone(note)
        self.assertIsNone(url)


if __name__ == "__main__":
    unittest.main()
