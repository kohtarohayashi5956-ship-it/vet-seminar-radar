# -*- coding: utf-8 -*-
"""Conservative optional enrichment from official VETS ACADEMY detail pages.

Only pages whose explicitly labelled course schedule matches the listing date
can supplement listing data. Do not infer missing dates, event format or fees.
Fetches use the shared rate-limited, robots-aware HTTP client.
"""
import datetime
import re
import unicodedata
from urllib.parse import urlsplit

from extract import html_to_text

MAX_DETAILS = 8
DETAIL_PATH = re.compile(r"/seminar/detail/\d+/?")
DATE = re.compile(
    r"(?<!\d)(20\d{2})\s*[年/.\-]\s*(1[0-2]|0?[1-9])"
    r"\s*[月/.\-]\s*(3[01]|[12]\d|0?[1-9])\s*日?"
)
RANGE = re.compile(
    r"(?<!\d)([01]?\d|2[0-3])[:：]([0-5]\d)\s*"
    r"[～〜~－―–-]\s*([01]?\d|2[0-3])[:：]([0-5]\d)"
)
FEE = re.compile(r"(?<!\d)\d[\d,，]*\s*円\s*(?:[(（]税込[)）])?")
SCHEDULE_LABEL = re.compile(r"^(?:[■●※]\s*)?開催日時\s*[：:]?")
DEADLINE_LABEL = re.compile(r"^(?:[■●※]\s*)?申込締切\s*[：:]?")
FEE_LABEL = re.compile(r"^(?:[■●※]\s*)?(?:受講料|会費)\s*[：:]?")
HEADINGS = re.compile(r"^(?:[■●]\s*)?(?:対象|形式|会場|開催場所|講師|プログラム|セミナー概要|申込締切|会費|受講料)")


def _date(text):
    matches = []
    for match in DATE.finditer(text):
        try:
            parsed = datetime.date(*map(int, match.groups())).isoformat()
        except ValueError:
            continue
        matches.append(parsed)
    return matches


def _url(event):
    try:
        parsed = urlsplit(event.get("url") or "")
    except ValueError:
        return None
    if (parsed.scheme != "https"
            or parsed.hostname != "academy.eduone.jp"
            or not DETAIL_PATH.fullmatch(parsed.path)
            or parsed.username or parsed.password):
        return None
    return parsed.scheme + "://" + parsed.netloc + parsed.path


def _course_schedule(lines, event):
    """Require a course date, not a registration or publishing date."""
    start = event.get("start_date")
    if not start:
        return None
    found = []
    for i, line in enumerate(lines):
        if not SCHEDULE_LABEL.match(line):
            continue
        snippet = SCHEDULE_LABEL.sub("", line).lstrip(" ：:")
        if not _date(snippet) and i + 1 < len(lines):
            snippet = lines[i + 1]
        dates = _date(snippet)
        if len(dates) == 1 and dates[0] == start:
            found.append(snippet)
    if len(found) != 1:
        return None
    match = RANGE.search(found[0])
    if not match:
        return {}
    sh, sm, eh, em = match.groups()
    begin, finish = f"{int(sh):02d}:{sm}", f"{int(eh):02d}:{em}"
    if event.get("start_time") and event["start_time"] != begin:
        return None
    return {"start_time": begin, "end_time": finish}


def parse_academy_detail(text, event):
    """Return only corroborated fields from one official event detail page."""
    lines = [unicodedata.normalize("NFKC", line).strip()
             for line in text.splitlines() if line.strip()]
    times = _course_schedule(lines, event)
    if times is None:
        return {}
    out = {}
    for field in ("start_time", "end_time"):
        if times.get(field) and not event.get(field):
            out[field] = times[field]

    # Distinguish registration closing from cancellation / abstract deadlines.
    # The year must be written on the same explicitly labelled line (or next).
    for i, line in enumerate(lines):
        if not DEADLINE_LABEL.match(line):
            continue
        snippet = DEADLINE_LABEL.sub("", line).lstrip(" ：:")
        if not snippet and i + 1 < len(lines):
            snippet = lines[i + 1]
        dates = _date(snippet)
        if len(dates) != 1:
            continue
        date = dates[0]
        latest_possible = event.get("end_date") or event.get("start_date")
        if latest_possible and date <= latest_possible and not event.get("deadline"):
            out["deadline"] = date
            break

    # Fee is accepted only beside an explicit 受講料 or 会費 label.
    if not event.get("price"):
        for i, line in enumerate(lines):
            if not FEE_LABEL.match(line):
                continue
            inline = FEE_LABEL.sub("", line).lstrip(" ：:")
            candidates = [inline] if inline else []
            for nxt in lines[i + 1:i + 4]:
                if HEADINGS.match(nxt) or DEADLINE_LABEL.match(nxt):
                    break
                candidates.append(nxt)
            for candidate in candidates:
                match = FEE.search(candidate)
                if match:
                    out["price"] = match.group(0).replace("，", ",")
                    break
            if "price" in out:
                break
    return out


def enrich_academy(events, fetcher, today, stats, limit=MAX_DETAILS):
    """Limit requests, preserve cards on detail failure, never bypass blocks."""
    candidates = []
    for event in events:
        url = _url(event)
        if not url or not event.get("start_date"):
            continue
        last = event.get("end_date") or event["start_date"]
        if last < today.isoformat():
            continue
        if event.get("start_time") and event.get("end_time") and event.get("price") and event.get("deadline"):
            continue
        candidates.append((event["start_date"], url, event))
    candidates.sort(key=lambda item: item[0])
    fetched = {}
    for _, url, _ in candidates:
        if url in fetched or len(fetched) >= limit:
            continue
        try:
            fetched[url] = html_to_text(fetcher.get(url), url)
        except Exception:
            fetched[url] = None
    accepted = prices = deadlines = times = 0
    for _, url, event in candidates:
        if not fetched.get(url):
            continue
        details = parse_academy_detail(fetched[url], event)
        if not details:
            continue
        previous = {field: event.get(field) for field in details}
        event.update(details)
        accepted += any(previous[field] != event.get(field) for field in details)
        prices += bool(details.get("price"))
        deadlines += bool(details.get("deadline"))
        times += bool(details.get("start_time"))
    stats.update(details_scanned=len(fetched), details_accepted=accepted,
                 prices_found=prices, deadlines_found=deadlines,
                 times_found=times,
                 detail_fetch_failed=sum(v is None for v in fetched.values()))
    return events
