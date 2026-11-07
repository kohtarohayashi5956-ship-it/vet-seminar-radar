# -*- coding: utf-8 -*-
"""Enrich JBVP regional meetings from their event-specific official pages.

Only a date-matched regional meeting page may contribute its venue. Do not
infer registration dates, fees, or programme hours from navigation/sidebar.
All HTTP requests go through the existing rate-limited robots-aware fetcher.
"""
import re
import unicodedata
from urllib.parse import urlsplit

from extract import html_to_text
from free_extract import _dates, _times

MAX_DETAILS = 5
REGIONS = {
    "nagoya": ("名古屋", "愛知県"),
    "kyoto": ("京都", "京都府"),
    "kyushu": ("九州", "福岡県"),
    "tohoku": ("東北", "宮城県"),
    "hokkaido": ("北海道", "北海道"),
}
STOP_LABELS = ("お問い合わせ", "主催", "共催", "後援", "参加費", "登録", "お申し込み", "お申込み")
VENUE_LABEL = re.compile(r"^(?:会場|開催場所)\s*[：:]?")
SCHEDULE_LABEL = re.compile(r"^(?:日時|日程)\s*[：:]?")


def detail_url(event):
    url = event.get("detail_url")
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    match = re.fullmatch(r"/regional/([a-z]+)\.html", parsed.path)
    if (parsed.scheme != "https" or parsed.hostname not in ("www.jbvp.org", "jbvp.org")
            or parsed.username or parsed.password or not match):
        return None
    region = match.group(1)
    return (parsed.scheme + "://" + parsed.netloc + parsed.path, region) if region in REGIONS else None


def parse_jbvp_region(text, event):
    """Require matching region, meeting heading and exact printed date."""
    link = detail_url(event)
    if not link or not event.get("start_date"):
        return {}
    region_name, prefecture = REGIONS[link[1]]
    if region_name not in event.get("title", "") or "地区大会" not in event.get("title", ""):
        return {}
    lines = [unicodedata.normalize("NFKC", line.strip())
             for line in text.splitlines() if line.strip()]
    meeting = next((i for i, line in enumerate(lines)
                    if region_name in line and "地区大会" in line
                    and len(line) < 65), None)
    if meeting is None:
        return {}
    scope = lines[meeting + 1:meeting + 18]
    date_ok = False
    schedule_times = []
    venue = None
    for idx, line in enumerate(scope):
        if SCHEDULE_LABEL.match(line):
            remainder = SCHEDULE_LABEL.sub("", line).strip(" ：:")
            if not remainder and idx + 1 < len(scope):
                remainder = scope[idx + 1]
            dates = _dates(remainder)
            if dates == [event["start_date"]]:
                date_ok = True
                # Only a single date-bound schedule line may supply times.
                start_time, end_time = _times(remainder)
                if start_time and end_time:
                    schedule_times.append((start_time, end_time))
        if VENUE_LABEL.match(line):
            remainder = VENUE_LABEL.sub("", line).strip(" ：:")
            if not remainder and idx + 1 < len(scope):
                remainder = scope[idx + 1]
            # Venue is a concise standalone location, not a contact address.
            if (3 <= len(remainder) <= 90
                    and not any(x in remainder for x in ("〒", "TEL", "FAX", "E-mail", "http"))
                    and not any(remainder.startswith(x) for x in STOP_LABELS)
                    and not _dates(remainder)):
                venue = remainder
    if not date_ok or not venue:
        return {}
    result = {}
    if not event.get("venue"):
        result["venue"] = venue
    if not event.get("prefecture"):
        result["prefecture"] = prefecture
    if len(schedule_times) == 1:
        start_time, end_time = schedule_times[0]
        if not event.get("start_time") or event["start_time"] == start_time:
            if not event.get("start_time"):
                result["start_time"] = start_time
            if not event.get("end_time"):
                result["end_time"] = end_time
    return result


def enrich_jbvp(events, fetcher, today, stats, limit=MAX_DETAILS):
    """No event deletion or mutation when official page fetch is denied."""
    candidates = []
    for event in events:
        url_and_region = detail_url(event)
        if not url_and_region or not event.get("start_date"):
            continue
        if event["start_date"] < today.isoformat():
            continue
        if (event.get("venue") and event.get("prefecture")
                and event.get("start_time") and event.get("end_time")):
            continue
        candidates.append((event["start_date"], url_and_region[0], event))
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
    venues_found = 0
    times_found = 0
    for _, url, event in candidates:
        if not fetched.get(url):
            continue
        values = parse_jbvp_region(fetched[url], event)
        if not values:
            continue
        event.update(values)
        accepted += 1
        venues_found += bool(values.get("venue"))
        times_found += bool(values.get("start_time"))
    stats.update(details_scanned=len(fetched), details_accepted=accepted,
                 venues_found=venues_found, times_found=times_found,
                 detail_fetch_failed=sum(value is None for value in fetched.values()))
    return events
