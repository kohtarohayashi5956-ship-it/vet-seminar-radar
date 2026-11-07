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


def enrich_jsvas(events, fetcher, today, stats, limit=MAX_DETAILS):
    candidates = []
    for e in events:
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
    stats.update(details_scanned=len(fetched), details_accepted=accepted,
                 deadlines_found=deadlines, prices_found=prices,
                 times_found=times, detail_fetch_failed=sum(v is None for v in fetched.values()))
    return events
