# -*- coding: utf-8 -*-
"""PEPPY official detail enrichment; never borrow values between sessions."""
import re
import unicodedata
from urllib.parse import urlsplit

from extract import html_to_text
from free_extract import _dates, _times

MAX_DETAILS = 8
HEADINGS = ("開催日時", "日程", "申込期間", "受講料", "会場",
            "受講対象", "定員", "講師紹介", "参加方法", "セミナー内容")


def _url(event):
    try:
        p = urlsplit(event.get("url") or "")
    except (ValueError, TypeError):
        return None
    if (p.scheme != "https" or p.hostname not in ("peppy.jp", "www.peppy.jp")
            or p.username or p.password or not re.fullmatch(r"/seminar/\d+/?", p.path)):
        return None
    return p.scheme + "://" + p.netloc + p.path


def _block(lines, heading, limit=20):
    for i, line in enumerate(lines):
        if line == heading or line.startswith(heading + "：") or line.startswith(heading + ":"):
            inline = line[len(heading):].strip(" ：:")
            result = [inline] if inline else []
            for nxt in lines[i+1:i+1+limit]:
                if any(nxt == h or nxt.startswith(h + "：") or nxt.startswith(h + ":") for h in HEADINGS):
                    break
                result.append(nxt)
            return result
    return []


def parse_peppy_detail(text, event):
    """Only accept detail fields when exactly one date in the explicit schedule matches."""
    if not _url(event) or not event.get("start_date"):
        return {}
    lines = [unicodedata.normalize("NFKC", x.strip())
             for x in text.splitlines() if x.strip()]
    schedule = _block(lines, "開催日時", 12)
    if not schedule:
        schedule = _block(lines, "日程", 12)
    dates = _dates("\n".join(schedule))
    if dates != [event["start_date"]]:
        return {}
    out = {}
    times = []
    for line in schedule:
        # Time-only lines immediately below the dated schedule are allowed.
        t1, t2 = _times(line)
        if t1 and t2:
            times.append((t1, t2))
    if len(times) == 1:
        t1, t2 = times[0]
        if not event.get("start_time") or event["start_time"] == t1:
            if not event.get("start_time"):
                out["start_time"] = t1
            if not event.get("end_time"):
                out["end_time"] = t2
    if not event.get("price"):
        prices = _block(lines, "受講料", 5)
        values = [x for x in prices if len(x) < 120 and (
            re.search(r"\d[\d,]*\s*円", x) or x == "無料")]
        if len(values) == 1:
            out["price"] = values[0]
            if values[0] == "無料":
                out["is_free"] = True
    if not event.get("deadline"):
        registration = _block(lines, "申込期間", 4)
        # Require a full-year start and end date; never assume a year
        # for shorthand dates, and do not infer from course dates.
        printed = _dates("\n".join(registration))
        if len(printed) == 2 and printed[0] <= printed[1] <= event["start_date"]:
            out["deadline"] = printed[1]
    if not event.get("venue") and event.get("format") not in ("ライブ配信", "オンデマンド"):
        places = _block(lines, "会場", 3)
        if (len(places) == 1 and 4 <= len(places[0]) <= 90 and
                not re.search(r"https?://|〒|TEL|FAX|\\n", places[0])):
            out["venue"] = places[0]
    return out


def enrich_peppy(events, fetcher, today, stats, limit=MAX_DETAILS):
    candidates = [(e["start_date"], _url(e), e) for e in events
                  if _url(e) and e.get("start_date")
                  and e["start_date"] >= today.isoformat()
                  and not all(e.get(k) for k in ("start_time", "end_time", "price", "deadline", "venue"))]
    candidates.sort(key=lambda row: row[0])
    fetched = {}
    for _, url, _ in candidates:
        if url in fetched or len(fetched) >= limit:
            continue
        try:
            fetched[url] = html_to_text(fetcher.get(url), url)
        except Exception:
            fetched[url] = None
    changed = times = prices = deadlines = venues = 0
    for _, url, event in candidates:
        if not fetched.get(url):
            continue
        updates = parse_peppy_detail(fetched[url], event)
        if not updates:
            continue
        changed += any(event.get(k) != v for k, v in updates.items())
        times += bool(updates.get("start_time"))
        prices += bool(updates.get("price"))
        deadlines += bool(updates.get("deadline"))
        venues += bool(updates.get("venue"))
        event.update(updates)
    stats.update(details_scanned=len(fetched), details_accepted=changed,
                 times_found=times, prices_found=prices, deadlines_found=deadlines,
                 venues_found=venues,
                 detail_fetch_failed=sum(v is None for v in fetched.values()))
    return events
