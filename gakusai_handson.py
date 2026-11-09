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
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

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
        # Retain exact-date booking links even when both fee tiers are pending.
        dates = []
        applications = {}
        application_lines = segment[marker + 1:]
        for position, line in enumerate(application_lines):
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
                if not link and position + 1 < len(application_lines):
                    following = application_lines[position + 1]
                    # html_to_text may put an anchor label + URL on the
                    # immediately next line. Only a booking label is eligible.
                    if ("会場申込" in following or following.startswith("申込先")):
                        link = re.search(r"<(https://[^<>\s]+)>", following)
                if link:
                    try:
                        parsed = urlsplit(link.group(1))
                    except ValueError:
                        parsed = None
                    if (parsed and parsed.hostname == "seminar.gakusai.co.jp"
                            and parsed.username is None and parsed.password is None
                            and parsed.path.startswith("/")):
                        # Preserve required booking parameters; remove only
                        # analytics tags that can be user/session-specific.
                        query = [(k, v) for k, v in parse_qsl(
                            parsed.query, keep_blank_values=True)
                            if not (k.lower().startswith(("utm_", "_ga", "_gcl"))
                                    or k.lower() in ("_gl", "fbclid", "gclid"))]
                        applications[(date, city)] = urlunsplit((
                            parsed.scheme, parsed.netloc, parsed.path,
                            urlencode(query), ""))
        if not dates:
            continue
        blocks.append(dict(id=match.group(1), title=title,
                           dates=dates, applications=applications, fees=fees))
    # A course may have several nav anchors or repeated markup fragments.
    return list({x["id"]: x for x in blocks}.values())


def _booking_start_time(url, expected_day):
    """Only a fully dated, event-matched official booking timestamp is usable."""
    if not url:
        return None
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if (parsed.scheme != "https" or parsed.hostname != "seminar.gakusai.co.jp"
            or parsed.username or parsed.password
            or parsed.path != "/reservations/add"):
        return None
    params = parse_qsl(parsed.query, keep_blank_values=True)
    stamp = [v for k, v in params if k == "usage_timestamp_from"]
    booking_ids = [v for k, v in params if k == "event_id"]
    if (len(stamp) != 1 or len(booking_ids) != 1
            or not re.fullmatch(r"\d{1,10}", booking_ids[0])):
        return None
    match = re.fullmatch(
        r"(20\d{2})/(\d{2})/(\d{2})[ T](\d{2}):(\d{2})(?::00)?",
        stamp[0]
    )
    if not match:
        return None
    year, month, day, hour, minute = map(int, match.groups()[:5])
    try:
        date = datetime.date(year, month, day).isoformat()
    except ValueError:
        return None
    if date != expected_day or hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def enrich_handson(events, fetcher, today, stats):
    candidates = [e for e in events
                  if e.get("source_id") in (None, "gakusai")
                  and e.get("start_date", "").startswith("2027-")
                  and e.get("url", "").startswith("https://www.gakusai.co.jp/doubutu/")
                  and e.get("format") not in ("オンデマンド", "ライブ配信")
                  and (not e.get("price") or not e.get("detail_url") or not e.get("start_time"))]
    # The Gakusai annual listing itself explicitly names the venue for
    # these two 2027 wet labs. It remains valid even if course detail links
    # are not yet published; never infer a venue from prefecture alone.
    for event in candidates:
        title = unicodedata.normalize("NFKC", event.get("title") or "")
        if (not event.get("venue")
                and event.get("start_date") == "2027-10-10"
                and "ウェットラボ in 宮崎大学" in title
                and ("軟部外科実習2027" in title
                     or "麻酔管理実習2027" in title)):
            event["venue"] = "宮崎大学"
            stats["handson_venues_found"] = (
                stats.get("handson_venues_found", 0) + 1)
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
        # Fee headings come directly from this same matched official course:
        # 会員獣医師 / 一般獣医師. Do not classify unmatched annual cards.
        if set(values) == {"会員", "一般"}:
            audience = event.get("audience") or []
            if "獣医師" not in audience:
                event["audience"] = audience + ["獣医師"]
        if not event.get("price") and set(values) == {"会員", "一般"}:
            price = ("会員 " + values["会員"] + "／一般 " + values["一般"])
            if len(price) <= 340:
                event["price"] = price
                event["is_free"] = None
                added += 1
        if not event.get("format"):
            event["format"] = "現地"
        selected_city = city or matches[0][1]
        if not event.get("prefecture"):
            event["prefecture"] = {"東京":"東京都","大阪":"大阪府",
                                   "宮崎":"宮崎県","福岡":"福岡県"}[selected_city]
        # For two 2027 Miyazaki wet labs, the official course title itself
        # explicitly names the university. Do not infer Tokyo/Osaka venues
        # from a city label or transfer this venue to another course.
        if (not event.get("venue") and selected_city == "宮崎"
                and "宮崎大学" in course["title"]
                and "宮崎大学" in (event.get("title") or "")):
            event["venue"] = "宮崎大学"
            stats["handson_venues_found"] = (
                stats.get("handson_venues_found", 0) + 1)
        application = course["applications"].get((event["start_date"], selected_city))
        if application:
            # Read the official booking start timestamp only after the
            # independently matched title/date/city/course decision above.
            # End times, application deadlines and venue names are not inferred.
            booking_time = _booking_start_time(application, event["start_date"])
            if booking_time and not event.get("start_time"):
                event["start_time"] = booking_time
                stats["handson_start_times_found"] = (
                    stats.get("handson_start_times_found", 0) + 1)
            if not event.get("detail_url"):
                event["detail_url"] = application
                stats["handson_applications_found"] = (
                    stats.get("handson_applications_found", 0) + 1)
    stats["handson_pages"] = 1
    stats["handson_course_cards"] = len(courses)
    stats["handson_fees_found"] = added
    return events
