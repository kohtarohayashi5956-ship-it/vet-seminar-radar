# -*- coding: utf-8 -*-
"""Specialty certification finder runs without API keys or external scripts."""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

PAGE=pathlib.Path("template.html").read_text(encoding="utf-8")


def function_source(name):
    token="function "+name+"("
    i=PAGE.index(token)
    pos=PAGE.index("{",i)
    depth=0
    for k in range(pos,len(PAGE)):
        ch=PAGE[k]
        if ch=="{":
            depth+=1
        elif ch=="}":
            depth-=1
            if depth==0:
                return PAGE[i:k+1]
    raise AssertionError("Missing function ending: "+name)


class CertificationFinderTests(unittest.TestCase):
    def test_panel_controls_present_and_wired(self):
        self.assertIn('id="certField"',PAGE)
        self.assertIn('id="certKind"',PAGE)
        self.assertIn('id="certList"',PAGE)
        self.assertIn('id="certCount"',PAGE)
        self.assertIn('renderCertificationPanel();',PAGE)
        self.assertIn('$("certField").addEventListener("change", render)',PAGE)
        self.assertIn('$("certKind").addEventListener("change", render)',PAGE)
        body=function_source("renderCertificationPanel")
        self.assertIn("passes(e)",body)
        self.assertIn("endOf(e) >= todayStr",body)
        self.assertIn("e.abstract_deadline",body)
        self.assertIn("e.certification_url",body)
        self.assertIn("certCourseItems(e)",body)
        self.assertIn("e.certification_program",function_source("certCourseItems"))

    def test_certification_panel_after_main_and_collapsed_by_default(self):
        self.assertLess(PAGE.index('<div class="layout">'), PAGE.index('id="certDisclosure"'))
        self.assertIn('<details class="cert-disclosure" id="certDisclosure">', PAGE)
        self.assertIn('id="certShortcut"', PAGE)
        self.assertIn('id="certSearch"', PAGE)
        self.assertIn('$(\"certSearch\").addEventListener("input", render)', PAGE)
        self.assertIn('$(\"certDisclosure\").open = true', PAGE)
        self.assertIn('function certCourseItems(e)', PAGE)

    def test_course_search_does_not_split_titles_at_middle_dot(self):
        if shutil.which("node") is None:
            self.skipTest("Node is unavailable")
        js="\n".join([
            'const assert = require("node:assert/strict");',
            function_source("certCourseItems"),
            function_source("certSearchNorm"),
            function_source("certSearchMatch"),
            function_source("certArea"),
            function_source("norm"),
            'const e = {source_id:"jsvc",title:"第125回日本獣医循環器学会定例大会",certification_note:"認定医講習会",certification_program:"講座22 感染性心内膜炎・講座23 犬のフィラリア症・講座34 心臓腫瘍・心膜疾患／アドバンス：基礎4 心血管疾患治療の先端技術・臨床20 循環器疾患のCT検査・臨床21 猫の心臓外科・臨床22 腫瘍循環器病学"};',
            'assert.equal(certCourseItems(e).length,7);',
            'assert.ok(certCourseItems(e).includes("講座34 心臓腫瘍・心膜疾患"));',
            'assert.equal(certSearchMatch(e,"講座34"),true);',
            'assert.equal(certSearchMatch(e,"臨床21"),true);',
            'assert.equal(certSearchMatch(e,"皮膚科"),false);',
            'assert.equal(certSearchMatch(e,"循環器 講座22"),true);',
            'const kidney={source_id:"javnu_cert",title:"JAVNU認定講習会",certification_note:"認定講習会",certification_program:"腎・泌尿器の画像診断"};',
            'assert.equal(certSearchMatch(kidney,"腎泌尿器"),true);',
        ])
        p=subprocess.run(["node","-e",js],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_js_syntax(self):
        if shutil.which("node") is None:
            self.skipTest("Node is unavailable")
        scripts=re.findall(r"<script>\s*([\s\S]*?)</script>",PAGE)
        self.assertEqual(len(scripts),1)
        with tempfile.NamedTemporaryFile(mode="w",suffix=".js",encoding="utf-8") as f:
            f.write(scripts[0])
            f.flush()
            p=subprocess.run(["node","--check",f.name],
                             text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr)

    def test_specialty_and_type_classification_in_node(self):
        if shutil.which("node") is None:
            self.skipTest("Node is unavailable")
        js="\n".join([
            'var todayStr="2026-11-07";',
            'function md(x) { return x.slice(5).replace("-","/"); }',
            function_source("deadlineDays"),
            function_source("certArea"),
            function_source("certKind"),
            function_source("certMatches"),
            function_source("certRegistrationStatus"),
            'const assert=require("node:assert/strict");',
            'const heart={source_id:"jsvc",certification_note:"認定医講習会の開催予定",certification_program:"講座22 感染性心内膜炎"};',
            'const skin={source_id:"jsvd",certification_note:"認定医更新評価点 10ポイント",certification_program:null};',
            'const kidney={source_id:"javnu",certification_note:"学術集会参加単位 1単位",certification_program:null};',
            'const unknown={source_id:"jbvp",certification_note:null,certification_program:null};',
            'assert.equal(certArea(heart),"循環器");',
            'assert.equal(certArea(skin),"皮膚科");',
            'assert.equal(certArea(kidney),"腎・泌尿器");',
            'assert.equal(certKind(heart),"course");',
            'assert.equal(certKind(skin),"points");',
            'assert.equal(certKind(kidney),"activity");',
            'assert.equal(certMatches(heart,"循環器","course"),true);',
            'assert.equal(certMatches(heart,"皮膚科","all"),false);',
            'assert.equal(certMatches(skin,"皮膚科","points"),true);',
            'assert.equal(certMatches(kidney,"腎・泌尿器","activity"),true);',
            'assert.equal(certMatches(kidney,"all","course"),false);',
            'assert.equal(certMatches(unknown,"all","all"),false);',
            'assert.match(certRegistrationStatus(null,"参加申込締切"),/未取得/);',
            'assert.match(certRegistrationStatus("2026-11-22","参加申込締切"),/あと15日/);',
            'assert.match(certRegistrationStatus("2026-11-06","参加申込締切"),/期限経過/);',
            'assert.match(certRegistrationStatus("2026-11-07","演題募集締切"),/本日締切/);',
        ])
        p=subprocess.run(["node","-e",js],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)

if __name__=="__main__":
    unittest.main()
