# -*- coding: utf-8 -*-
"""Optional, bounded, free detailed-page enrichment.

Respect the shared Fetcher's robots.txt and 3-second delay. The detail page
must explicitly state the SAME start date (and time, if applicable) as the
event card. Never infer an admission price or deadline from another listing,
page navigation, or an unrelated side bar.
"""
import datetime
import re
from urllib.parse import urlsplit

from extract import html_to_text
from free_extract import _dates, _times

MAX_LIFETAIL_DETAILS = 12

# Block labels occurring on Life&Tail public seminar detail pages.
SECTION_HEADS = {
    "開催日時", "受講料", "申込期間", "会場", "備考", "定員",
    "シリーズ", "主催", "講師", "協力",
}


def _rows(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def _section(lines, name, max_rows):
    """Take only text *under* a matching field label, not a neighboring field."""
    for i, line in enumerate(lines):
        if line == name or line.startswith(name + "：") or line.startswith(name + ":"):
            content = []
            inline = line[len(name):].lstrip(" ：:")
            if inline:
                content.append(inline)
            for nxt in lines[i + 1:i + 1 + max_rows]:
                if nxt in SECTION_HEADS or any(nxt.startswith(s + "：") for s in SECTION_HEADS):
                    break
                content.append(nxt)
            return content
    return []


def _course_date_matches(lines, event):
    block = _section(lines, "開催日時", 3)
    dates = _dates(" ".join(block))
    if not dates or dates[0] != event.get("start_date"):
        return False
    expected_time = event.get("start_time")
    parsed_times = _times(" ".join(block))
    if expected_time and parsed_times[0] and expected_time != parsed_times[0]:
        return False
    return True


def _life_price(lines):
    block = _section(lines, "受講料", 7)
    prices = []
    for line in block:
        m = re.match(
            r"^(無料会員|プライム会員|一般会員|一般|会員)[：:\s]+"
            r"([\d０-９,，]+\s*円)(?:/人)?", line
        )
        if m:
            tier, amount = m.groups()
            amount = amount.replace("，", ",")
            record = tier + " " + amount
            if record not in prices:
                prices.append(record)
    if prices:
        return "／".join(prices[:4]), None
    # Only a standalone free value under the '受講料' field is proof.
    if any(re.fullmatch(r"(?:参加費\s*)?無料(?:\s*[（(]税込[)）])?", x) for x in block[:3]):
        return "無料", True
    return None, None


def _life_deadline(lines, event):
    block = _section(lines, "申込期間", 15)
    if not block:
        return None
    all_dates = _dates(" ".join(block))
    if not all_dates:
        return None
    max_end = event.get("end_date") or event.get("start_date")
    candidates = [x for x in all_dates if max_end and x <= max_end]
    # Several dates can be printed for priority/regular registration.
    # Last date is the latest *explicitly printed* date, never fabricated.
    return max(candidates) if candidates else None


def _life_venue(lines, event):
    if event.get("format") in ("ライブ配信", "オンデマンド"):
        return None
    block = _section(lines, "会場", 3)
    for line in block:
        if (4 <= len(line) <= 95
                and "Google map" not in line
                and not line.startswith(("http", "<", "map"))
                and "オンライン" not in line):
            return line
    return None


def parse_lifetail_detail(detail_text, event):
    """Return only verified supplemental fields; no date changes, ever."""
    lines = _rows(detail_text)
    if not _course_date_matches(lines, event):
        return {}
    out = {}
    price, is_free = _life_price(lines)
    if price is not None:
        out["price"] = price
        out["is_free"] = is_free
    deadline = _life_deadline(lines, event)
    if deadline:
        out["deadline"] = deadline
    venue = _life_venue(lines, event)
    if venue and not event.get("venue"):
        out["venue"] = venue
    return out


def _detail_link(event):
    try:
        u = urlsplit(event.get("url") or "")
    except ValueError:
        return None
    if u.scheme not in ("https", "http"):
        return None
    if u.hostname not in ("life-tail.com", "www.life-tail.com"):
        return None
    if not re.fullmatch(r"/seminars/\d+/?", u.path):
        return None
    return u.scheme + "://" + u.netloc + u.path


def enrich_lifetail(events, fetcher, today, stats, limit=MAX_LIFETAIL_DETAILS):
    """Do not fail a whole source scan when an optional detail fetch fails."""
    if not events:
        return events
    candidates = []
    for event in events:
        url = _detail_link(event)
        start = event.get("start_date")
        if not url or not start or start < today.isoformat():
            continue
        if event.get("deadline") and event.get("price") and event.get("venue"):
            continue
        candidates.append((start, url, event))
    candidates.sort(key=lambda t: t[0])
    # Cache within the run: the same detail page can appear twice on the list.
    # Data remain event-specific by checking the expected date/time.
    fetched = {}
    for _, url, event in candidates:
        if url in fetched or len(fetched) >= limit:
            continue
        try:
            fetched[url] = html_to_text(fetcher.get(url), url)
        except Exception:
            fetched[url] = None
    changed = 0
    dated = 0
    priced = 0
    for _, url, event in candidates:
        text = fetched.get(url)
        if not text:
            continue
        details = parse_lifetail_detail(text, event)
        if not details:
            continue
        old = (event.get("deadline"), event.get("price"), event.get("venue"))
        event.update(details)
        new = (event.get("deadline"), event.get("price"), event.get("venue"))
        changed += old != new
        dated += bool(details.get("deadline"))
        priced += bool(details.get("price"))
    stats["details_scanned"] = len(fetched)
    stats["details_accepted"] = changed
    stats["deadlines_found"] = dated
    stats["prices_found"] = priced
    stats["detail_fetch_failed"] = sum(v is None for v in fetched.values())
    return events
