# -*- coding: utf-8 -*-
"""JSVAS district course enrichment from the *same* official detail page.

Does not interpret the post-event video period, cancellation cutoffs or
programme/session timetable as the seminar's start time.
"""
import datetime
import re
import unicodedata
from urllib.parse import urlsplit

from extract import html_to_text
from free_extract import _dates, _times

MAX_DETAILS = 6
SCHEDULE = re.compile(r"^日時\s*[：:]?")
DEADLINE = re.compile(r"^(?:事前申込締切|会場参加のお申込み締切|参加申込締切)\s*[：:]?")
TOP_LEVEL = re.compile(r"^(?:日時|会場|講師|主催|参加対象|参加費|定員|"
                       r"開催後配信|プログラム|参加登録|事前申込締切|"
                       r"会場参加のお申込み締切|お問い合わせ)\s*[：:]?")


def _url(event):
    try:
        p = urlsplit(event.get("url") or "")
    except ValueError:
        return None
    if (p.scheme != "https" or p.hostname not in ("www.jsvas.net", "jsvas.net")
            or p.username or p.password
            or not re.fullmatch(r"/lectures/[a-zA-Z0-9_-]+\.php", p.path)):
        return None
    return p.scheme + "://" + p.netloc + p.path


def parse_jsvas_detail(text, event):
    """Require exactly one matching dated course schedule before any enrichment."""
    start = event.get("start_date")
    if not start:
        return {}
    lines = [unicodedata.normalize("NFKC", line).strip()
             for line in text.splitlines() if line.strip()]
    candidates = []
    for i, line in enumerate(lines):
        if not SCHEDULE.match(line):
            continue
        remainder = SCHEDULE.sub("", line).strip(" ：:")
        # Official pages use a standalone 日時 label followed by a date.
        if not remainder and i + 1 < len(lines):
            remainder = lines[i + 1]
        dates = _dates(remainder)
        if dates:
            candidates.append((dates, remainder))
    if len(candidates) != 1 or candidates[0][0] != [start]:
        return {}

    out = {}
    t1, t2 = _times(candidates[0][1])
    if t1 and t2 and (not event.get("start_time") or event["start_time"] == t1):
        if not event.get("start_time"):
            out["start_time"] = t1
        if not event.get("end_time"):
            out["end_time"] = t2

    if not event.get("deadline"):
        for i, line in enumerate(lines):
            if not DEADLINE.match(line):
                continue
            remainder = DEADLINE.sub("", line).strip(" ：:")
            if not remainder and i + 1 < len(lines):
                remainder = lines[i + 1]
            dates = _dates(remainder)
            if len(dates) == 1 and dates[0] <= start:
                out["deadline"] = dates[0]
                break

    if not event.get("price"):
        # Retain tier names. A free tier does NOT make the entire event free.
        for i, line in enumerate(lines):
            if line != "参加費":
                continue
            values = []
            for nxt in lines[i + 1:i + 7]:
                if TOP_LEVEL.match(nxt) or nxt in ("パンフレット", "フライヤー"):
                    break
                if ("無料" in nxt or re.search(r"\d[\d,]*\s*円", nxt)) and len(nxt) <= 110:
                    values.append(nxt)
            if values:
                out["price"] = "／".join(values[:4])[:300]
                if all("無料" in x and not re.search(r"\d[\d,]*\s*円", x) for x in values):
                    out["is_free"] = True
            break
    return out



def parse_jsvas_conference(text, event):
    """Only the *advance* registration cutoff; later registration remains open."""
    if (event.get("early_registration_deadline") or not event.get("start_date")
            or not event.get("end_date")):
        return {}
    lines = [unicodedata.normalize("NFKC", line).strip()
             for line in text.splitlines() if line.strip()]
    # Require the actual conference, rather than a link or unrelated meeting.
    match = re.search(r"第(\\d+)回", event.get("title") or "")
    if not match or not any("第" + match.group(1) + "回" in line
                            and "日本獣医麻酔外科学会" in "".join(lines[max(0, i-2):i+3])
                            for i, line in enumerate(lines)):
        return {}
    if not any("開催期間" in line and
               event["start_date"][:4] in " ".join(lines[i:i+3]) and
               str(int(event["start_date"][5:7])) + "月" in " ".join(lines[i:i+3])
               for i, line in enumerate(lines)):
        return {}
    for i, line in enumerate(lines):
        if "参加登録期間" not in line:
            continue
        block = " ".join(lines[i:i+5])
        # Exactly one advance registration window with a year on its start.
        candidates = re.findall(
            r"事前登録\\s*[：:]\\s*(20\\d{2})\\s*年\\s*(\\d{1,2})\\s*月\\s*\\d{1,2}\\s*日"
            r"[^。\\n]{0,55}?[〜~～-]\\s*(?:(20\\d{2})\\s*年\\s*)?(\\d{1,2})\\s*月\\s*(\\d{1,2})\\s*日",
            block)
        if len(candidates) != 1:
            return {}
        year, _, end_year, month, day = candidates[0]
        try:
            date = datetime.date(int(end_year or year), int(month), int(day))
        except ValueError:
            return {}
        if date.isoformat() <= event["start_date"]:
            return {"early_registration_deadline": date.isoformat()}
        return {}
    return {}

def _conference_url(event):
    try:
        p = urlsplit(event.get("url") or "")
    except ValueError:
        return None
    if (p.scheme != "https" or p.hostname not in ("www.jsvas.net", "jsvas.net")
            or p.username or p.password
            or not re.fullmatch(r"/conference/20\\d{2}-\\d+\\.php", p.path)):
        return None
    return p.scheme + "://" + p.netloc + p.path

def enrich_jsvas(events, fetcher, today, stats, limit=MAX_DETAILS):
    candidates = []
    conferences = []
    for e in events:
        conference_url = _conference_url(e)
        if (conference_url and e.get("start_date") and e["start_date"] >= today.isoformat()
                and not e.get("early_registration_deadline")):
            conferences.append((conference_url, e))
        url = _url(e)
        if not url or not e.get("start_date") or e["start_date"] < today.isoformat():
            continue
        if all(e.get(key) for key in ("start_time", "end_time", "price", "deadline")):
            continue
        candidates.append((e["start_date"], url, e))
    candidates.sort(key=lambda x: x[0])
    fetched = {}
    for _, url, _ in candidates:
        if url in fetched or len(fetched) >= limit:
            continue
        try:
            fetched[url] = html_to_text(fetcher.get(url), url)
        except Exception:
            fetched[url] = None
    accepted = deadlines = prices = times = 0
    for _, url, e in candidates:
        if not fetched.get(url):
            continue
        data = parse_jsvas_detail(fetched[url], e)
        if not data:
            continue
        old = {key: e.get(key) for key in data}
        e.update(data)
        accepted += any(old[key] != e.get(key) for key in data)
        deadlines += bool(data.get("deadline"))
        prices += bool(data.get("price"))
        times += bool(data.get("start_time"))
    # Conference registration is multi-phase. Never use the advance-registration
    # cutoff as the final application deadline.
    for url, e in conferences[:2]:
        if url not in fetched:
            try:
                fetched[url] = html_to_text(fetcher.get(url), url)
            except Exception:
                fetched[url] = None
        if not fetched[url]:
            continue
        data = parse_jsvas_conference(fetched[url], e)
        if data:
            e.update(data)
            accepted += 1
    stats["early_registration_deadlines_found"] = sum(
        bool(e.get("early_registration_deadline")) for _, e in conferences)
    stats.update(details_scanned=len(fetched), details_accepted=accepted,
                 deadlines_found=deadlines, prices_found=prices,
                 times_found=times, detail_fetch_failed=sum(v is None for v in fetched.values()))
    return events
