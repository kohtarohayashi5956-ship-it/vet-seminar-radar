# -*- coding: utf-8 -*-
"""Validate one official certification-course schedule against its meeting.

Never infer registration deadlines, examination credits or award points.
Only publish course titles after the event date AND meeting number match.
Fetches through the shared robots-respecting / rate-limited Fetcher.
"""
import re
import unicodedata
from extract import html_to_text

JSVC_COURSES_URL = "https://www.jsvc.jp/certification/session/records/session2026/"
EXPLICIT_COURSES = {
    "22": "感染性心内膜炎",
    "23": "犬のフィラリア症",
    "34": "心臓腫瘍・心膜疾患",
}
ADVANCED_COURSES = {
    "基礎4": "心血管疾患治療の先端技術",
    "臨床20": "循環器疾患のCT検査",
    "臨床21": "猫の心臓外科",
    "臨床22": "腫瘍循環器病学",
}


def _course_exists(lines, label, title):
    """Match a course identifier immediately adjacent to its subject title."""
    normalized = [unicodedata.normalize("NFKC", x).strip() for x in lines]
    for i, line in enumerate(normalized):
        if line == label:
            if any(title in nxt for nxt in normalized[i+1:i+3]):
                return True
        if re.search(r"(^|\|)\s*" + re.escape(label) +
                     r"\s*\|\s*" + re.escape(title), line):
            return True
    return False


def parse_jsvc_certification_program(page_text, event):
    if (event.get("source_id") not in (None, "jsvc")
            or event.get("start_date") != "2026-12-19"
            or "第125回" not in event.get("title", "")):
        return None
    text = unicodedata.normalize("NFKC", page_text)
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    start = next((i for i,x in enumerate(lines)
                 if re.match(r"^第125回\s*定例大会$", x)), None)
    if start is None:
        return None
    section = []
    for line in lines[start + 1:]:
        if re.match(r"^第\d+回\s*定例大会$", line):
            break
        if line.startswith(("日本獣医循環器学会事務局", "お問い合わせ")):
            break
        section.append(line)
    # This is the actual scheduled meeting, not the preceding 124th meeting.
    joined = "\n".join(section)
    if not re.search(r"2026年12月19[、,・〜~～\-]\s*20日", re.sub(r"\s+", "",joined)):
        return None
    if not all(_course_exists(section, course, title)
               for course, title in EXPLICIT_COURSES.items()):
        return None
    ordinary = [f"講座{k} {v}" for k,v in EXPLICIT_COURSES.items()]
    advanced = [f"{k} {v}" for k,v in ADVANCED_COURSES.items()
                if _course_exists(section,k,v)]
    return "・".join(ordinary) + ("／アドバンス：" + "・".join(advanced) if advanced else "")


def enrich_jsvc(events, fetcher, today, stats):
    candidates = [
        e for e in events if e.get("start_date") == "2026-12-19"
        and "第125回" in e.get("title", "")
        and e.get("url", "").startswith("https://www.jsvc.jp/")
    ]
    if not candidates:
        return events
    try:
        html = fetcher.get(JSVC_COURSES_URL)
        text = html_to_text(html, JSVC_COURSES_URL)
    except Exception:
        stats["certification_detail_failed"] = 1
        return events
    stats["certification_details_scanned"] = 1
    updated = 0
    for ev in candidates:
        program = parse_jsvc_certification_program(text, ev)
        if program:
            ev["certification_program"] = program
            ev["certification_url"] = JSVC_COURSES_URL
            updated += 1
    stats["certification_programs_found"] = updated
    return events
