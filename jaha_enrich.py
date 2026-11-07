# -*- coding: utf-8 -*-
"""Conservative JAHA seminar-detail deadline extraction, free of AI calls.

Only approved, event-specific official URLs are fetched through the shared
robots-respecting Fetcher. An event's exact date must occur in an explicit
schedule line, not just a registration window, before its deadline is read.
Never derive a deadline from a cancellation or payment date.
"""
import datetime
import re
import unicodedata
from urllib.parse import urlsplit
from extract import html_to_text
from free_extract import _dates, _times

MAX_DETAILS = 10
REGISTRATION = re.compile(
    r"^(?:受付期間|申込期間|申込み期間|申し込み期間|お申込み締切|お申し込み締切|"
    r"申込締切|申し込み締切|申込期限|受付締切)\s*[：:]?"
)
EXCLUDE = re.compile(
    r"キャンセル|取り消し|返金|振込|支払|入金|資料|掲載日|投稿日|公開日|発行日"
)
YMD = re.compile(r"(20\d{2})\s*年\s*(1[0-2]|0?[1-9])\s*月\s*(3[01]|[12]\d|0?[1-9])\s*日")
SHORT = re.compile(r"(?<!\d)(1[0-2]|0?[1-9])\s*月\s*(3[01]|[12]\d|0?[1-9])\s*日")
DATE_RANGE = re.compile(r"[～〜~－–―-]")


def _url(event):
    try:
        u = urlsplit(event.get("url") or "")
    except ValueError:
        return None
    if u.scheme not in ("http", "https") or u.hostname not in (
        "jaha.or.jp", "www.jaha.or.jp"
    ):
        return None
    if not (
        u.path.startswith("/training/seminar/")
        or u.path.startswith("/owners/dog-training/")
    ):
        return None
    if u.path.endswith(("/top/", "/vet/", "/seminar/")):
        return None
    return u.scheme + "://" + u.netloc + u.path


def _registration_deadline(lines, start_date):
    for line in lines:
        if EXCLUDE.search(line) or not REGISTRATION.match(line):
            continue
        main = REGISTRATION.sub("", line).strip(" ：:")
        full = list(YMD.finditer(main))
        if not full:
            continue  # Never infer year from a neighboring event/page footer.
        if DATE_RANGE.search(main):
            # e.g. 受付期間：2026年9月7日～11月4日17時締切
            last = full[-1]
            year = int(last.group(1))
            tail = main[last.end():]
            short = list(SHORT.finditer(tail))
            if short:
                m, d = map(int, short[-1].groups())
                # Range can run over the new year. Use explicit start year,
                # not the year from the event calendar.
                if m < int(last.group(2)):
                    year += 1
                try:
                    result = datetime.date(year, m, d).isoformat()
                except ValueError:
                    continue
            else:
                result = _dates(main)[-1]
        else:
            result = _dates(main)[-1]
        if result and result <= start_date:
            return result
    return None


def parse_jaha_detail(text, event):
    start_date = event.get("start_date")
    if not start_date:
        return {}
    lines = [unicodedata.normalize("NFKC", v.strip())
             for v in text.splitlines() if v.strip()]
    # Exact printed seminar date must occur OUTSIDE registration, footer,
    # application, payment and cancellation information.
    schedule_matches = [
        line for line in lines
        if not REGISTRATION.match(line)
        and not EXCLUDE.search(line)
        and start_date in _dates(line)
    ]
    if not schedule_matches:
        return {}
    out = {}
    deadline = _registration_deadline(lines, start_date)
    if deadline:
        out["deadline"] = deadline
    # A timestamp is only trusted when the same schedule line explicitly
    # contains exactly one fully specified date and one time range.
    # In particular, do not associate a timetable for another session.
    matches = []
    for line in schedule_matches:
        if _dates(line) != [start_date] or len(SHORT.findall(line)) != 1:
            continue
        t1, t2 = _times(line)
        if t1 and t2:
            matches.append((t1, t2))
    if len(matches) == 1:
        t1, t2 = matches[0]
        if not event.get("start_time") or event["start_time"] == t1:
            if not event.get("start_time"):
                out["start_time"] = t1
            if not event.get("end_time"):
                out["end_time"] = t2
    return out


def enrich_jaha(events, fetcher, today, stats, limit=MAX_DETAILS):
    candidates = []
    for e in events:
        u = _url(e)
        start = e.get("start_date")
        if u and start and start >= today.isoformat():
            candidates.append((start, u, e))
    candidates.sort(key=lambda x: x[0])
    fetched = {}
    for _, url, _ in candidates:
        if url in fetched or len(fetched) >= limit:
            continue
        try:
            fetched[url] = html_to_text(fetcher.get(url), url)
        except Exception:
            fetched[url] = None
    accepted = 0
    times_found = 0
    for _, url, e in candidates:
        if not fetched.get(url):
            continue
        detail = parse_jaha_detail(fetched[url], e)
        if detail:
            before = (e.get("deadline"), e.get("start_time"), e.get("end_time"))
            missing_start = not e.get("start_time")
            e.update(detail)
            after = (e.get("deadline"), e.get("start_time"), e.get("end_time"))
            accepted += before != after
            times_found += bool(missing_start and e.get("start_time"))
    stats["details_scanned"] = len(fetched)
    stats["details_accepted"] = accepted
    stats["deadlines_found"] = sum(bool(e.get("deadline")) for _, _, e in candidates)
    stats["times_found"] = times_found
    stats["detail_fetch_failed"] = sum(v is None for v in fetched.values())
    return events
