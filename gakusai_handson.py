# -*- coding: utf-8 -*-
"""JAHA-independent Gakusai official hands-on listing fee enrichment.

Match one scheduled course by course title, day AND city before taking its
member/general price and material fee. Never copy a general tariff or the
next training course's price. Do not query external booking providers.
"""
import datetime
import difflib
import re
import unicodedata
from urllib.parse import urlsplit

from extract import html_to_text
from free_extract import _dates

URL = "https://www.gakusai.co.jp/doubutu/handson-comingup/"
COURSE = re.compile(r"(?:^|\s)MS\s*(1\d{2})\b")
FEE = re.compile(r"^(?:会員獣医師|一般獣医師)\s*(?:\||：|:)?\s*(.*)$")
MONEY = re.compile(r"\d[\d,]*\s*円")
CITY = {"東京": "東京", "大阪": "大阪", "宮崎": "宮崎", "福岡": "福岡"}
MONTHDAY = re.compile(r"(?<!\d)(1[0-2]|0?[1-9])月(3[01]|[12]\d|0?[1-9])日")
STOP = re.compile(r"^(?:受講料|ご入会はこちら|※|お申し込み|一般獣医師|会員獣医師)")


def _normalize(text):
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"20\d{2}|(?:dr\.)|[「」『』（）()【】、!！?？　\s・:：,，\-/]", "", text)
    return text


def _courses(text):
    lines = [unicodedata.normalize("NFKC", x).strip()
             for x in text.splitlines() if x.strip()]
    if not any("2027年" in x and "学際小動物" in x for x in lines[:25]):
        return []
    starts = [i for i, line in enumerate(lines)
              if COURSE.search(line) and ("MS1" in line or "MS 1" in line)]
    blocks = []
    for pos, i in enumerate(starts):
        j = starts[pos + 1] if pos + 1 < len(starts) else len(lines)
        segment = lines[i:j]
        # Top-of-page navigation cards have no seminar-specific 受講料.
        if "受講料" not in segment:
            continue
        match = COURSE.search(segment[0])
        if not match:
            continue
        title = segment[0][match.end():].strip(" |　")
        marker = segment.index("受講料")
        fees = {}
        fee_rows = segment[marker + 1:marker + 22]
        for k, line in enumerate(fee_rows):
            m = FEE.match(line)
            if not m:
                continue
            tier = ("会員" if line.startswith("会員獣医師") else "一般")
            rest = m.group(1)
            if not MONEY.search(rest):
                # HTML tables commonly split <td>会員獣医師</td> and
                # <td>48,000円＋実習材料費... into distinct text lines.
                # Only the immediately following cell in this course card
                # may complete that tier; never cross another tier/heading.
                nxt = fee_rows[k + 1] if k + 1 < len(fee_rows) else ""
                if not (MONEY.search(nxt) and not FEE.match(nxt)
                        and not nxt.startswith(("申込", "ご入会", "※", "受講料"))):
                    continue
                rest = nxt
            rest = re.split(r"<https?://|ご入会はこちら", rest, maxsplit=1)[0]
            if MONEY.search(rest):
                fees[tier] = rest.strip(" |")
        if set(fees) != {"会員", "一般"}:
            continue
        dates = []
        applications = {}
        for line in segment[marker + 1:]:
            if "会場申込" not in line:
                continue
            m = MONTHDAY.search(line)
            if not m:
                continue
            month, day = map(int, m.groups())
            try:
                date = datetime.date(2027, month, day).isoformat()
            except ValueError:
                continue
            city = next((name for name in CITY if name in line), None)
            if city:
                dates.append((date, city))
                # The actual booking URL must occur in THIS dated venue row.
                # Never invent one or accept unrelated/external domains.
                link = re.search(r"<(https://[^<>\s]+)>", line)
                if link:
                    try:
                        parsed = urlsplit(link.group(1))
                    except ValueError:
                        parsed = None
                    if (parsed and parsed.hostname == "seminar.gakusai.co.jp"
                            and parsed.username is None and parsed.password is None
                            and parsed.path.startswith("/")):
                        applications[(date, city)] = link.group(1)
        if not dates:
            continue
        blocks.append(dict(id=match.group(1), title=title,
                           dates=dates, applications=applications, fees=fees))
    # A course may have several nav anchors or repeated markup fragments.
    return list({x["id"]: x for x in blocks}.values())


def enrich_handson(events, fetcher, today, stats):
    candidates = [e for e in events
                  if e.get("source_id") in (None, "gakusai")
                  and e.get("start_date", "").startswith("2027-")
                  and e.get("url", "").startswith("https://www.gakusai.co.jp/doubutu/")
                  and e.get("format") not in ("オンデマンド", "ライブ配信")
                  and not e.get("price")]
    if not candidates:
        stats["handson_pages"] = 0
        stats["handson_fees_found"] = 0
        return events
    try:
        text = html_to_text(fetcher.get(URL), URL)
    except Exception:
        stats["handson_pages"] = 0
        stats["handson_fees_found"] = 0
        stats["handson_fetch_failed"] = 1
        return events

    courses = _courses(text)
    added = 0
    for event in candidates:
        # Exact date plus a matching city shown in the listing. A listing
        # without an explicit city is not enough to match split sessions.
        context = (event.get("title") or "") + " " + (event.get("venue") or "")
        city = next((c for c in CITY if c in context), None)
        # The annual card may not print Tokyo/Osaka in its title; use its
        # explicit event date only when exactly one matching course exists.
        possible = []
        for course in courses:
            matches = [(d, c) for d, c in course["dates"] if d == event["start_date"]]
            if not matches or (city and not any(c == city for _, c in matches)):
                continue
            a, b = _normalize(event.get("title")), _normalize(course["title"])
            if not a or not b:
                continue
            similarity = difflib.SequenceMatcher(None, a, b).ratio()
            overlap = difflib.SequenceMatcher(None, a, b).find_longest_match(
                0, len(a), 0, len(b)).size
            if similarity >= .56 and overlap >= 8:
                possible.append((similarity, course, matches))
        possible.sort(key=lambda x: x[0], reverse=True)
        if not possible or (len(possible) > 1 and
                            possible[0][0] - possible[1][0] < .13):
            continue
        similarity, course, matches = possible[0]
        # If multiple venues on the same day exist for this one programme,
        # do not pick a location unless an actual city was present.
        if not city and len({x[1] for x in matches}) != 1:
            continue
        values = course["fees"]
        price = ("会員 " + values["会員"] + "／一般 " + values["一般"])
        if len(price) > 340:
            continue
        event["price"] = price
        event["is_free"] = None
        if not event.get("format"):
            event["format"] = "現地"
        selected_city = city or matches[0][1]
        if not event.get("prefecture"):
            event["prefecture"] = {"東京":"東京都","大阪":"大阪府",
                                   "宮崎":"宮崎県","福岡":"福岡県"}[selected_city]
        application = course["applications"].get((event["start_date"], selected_city))
        if application and not event.get("detail_url"):
            event["detail_url"] = application
            stats["handson_applications_found"] = (
                stats.get("handson_applications_found", 0) + 1)
        added += 1
    stats["handson_pages"] = 1
    stats["handson_course_cards"] = len(courses)
    stats["handson_fees_found"] = added
    return events
