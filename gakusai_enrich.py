# -*- coding: utf-8 -*-
"""Optional, conservative Gakusai detail enrichment (no API charges)."""
import re
import unicodedata
from urllib.parse import urlsplit
from extract import html_to_text
from free_extract import _dates, _times

LIMIT = 6
TIERS = re.compile(r"(法人[・･]個人会員|一般獣医師|法人会員|個人会員)")
AMOUNT = re.compile(r"\d[\d,]*\s*円(?:\s*\(税込\s*\d[\d,]*\s*円\))?")


def detail_url(event):
    try:
        u = urlsplit(event.get("url") or "")
    except ValueError:
        return None
    if (u.scheme not in ("https", "http")
            or u.hostname not in ("www.gakusai.co.jp", "gakusai.co.jp")
            or not re.fullmatch(r"/vet/vet-seminar/\d+/?", u.path)):
        return None
    return u.scheme + "://" + u.netloc + u.path


def section(lines, name, stop, size=25):
    for i, line in enumerate(lines):
        if line == name:
            out = []
            for nxt in lines[i+1:i+size+1]:
                if any(nxt.startswith(h) for h in stop):
                    break
                out.append(nxt)
            return out
    return []


def parse_gakusai(text, event):
    """Only accept values belonging to an exact-date detail page."""
    lines = [unicodedata.normalize("NFKC", x.strip()) for x in text.splitlines() if x.strip()]
    schedule = section(lines, "開催日時・会場",
                       ["来場受講料", "ウェブ受講料", "開催にあたって"], 28)
    start = event.get("start_date")
    idx = next((i for i, ln in enumerate(schedule)
                if start and start in _dates(ln)), None)
    if idx is None:
        return {}
    date_line = schedule[idx]
    t1, t2 = _times(date_line)
    if event.get("start_time") and t1 and event["start_time"] != t1:
        return {}
    out = {}
    if t1:
        out["start_time"] = t1
    if t2:
        out["end_time"] = t2
    if event.get("format") not in ("ライブ配信", "オンデマンド"):
        out["format"] = "現地"
        for label, name in (("東京会場", "東京都"), ("大阪会場", "大阪府"),
                            ("名古屋会場", "愛知県"), ("福岡会場", "福岡県")):
            if label in date_line:
                out["prefecture"] = name
                break
        for ln in schedule[idx+1:idx+4]:
            if len(ln) < 85 and re.search(r"会館|センター|ホール|ホテル|会議室|大学|ビル", ln):
                if not event.get("venue"):
                    out["venue"] = ln
                break
        # Do not borrow generic website prices or on-demand tariffs.
        fee_lines = section(lines, "来場受講料",
                            ["ウェブ受講料", "開催にあたって"], 23)
        prices = []
        for j, line in enumerate(fee_lines):
            tier = TIERS.search(line)
            if not tier:
                continue
            rest = line[tier.end():]
            amount = AMOUNT.search(rest)
            if not amount and j+1 < len(fee_lines) and not TIERS.search(fee_lines[j+1]):
                amount = AMOUNT.search(fee_lines[j+1])
            if amount:
                value = tier.group(1) + " " + amount.group(0)
                if value not in prices:
                    prices.append(value)
        if prices:
            out["price"] = "／".join(prices[:3])
            out["is_free"] = None
    # Do not equate cancellation deadlines with registration deadlines.
    return out


def enrich_gakusai(events, fetcher, today, stats):
    candidates = [(e["start_date"], detail_url(e), e) for e in events
                  if e.get("start_date") and e["start_date"] >= today.isoformat()
                  and detail_url(e)]
    candidates.sort(key=lambda x: x[0])
    fetched = {}
    for _, url, _ in candidates:
        if url in fetched or len(fetched) >= LIMIT:
            continue
        try:
            fetched[url] = html_to_text(fetcher.get(url), url)
        except Exception:
            fetched[url] = None
    accepted = prices = times = 0
    for _, url, event in candidates:
        if not fetched.get(url):
            continue
        details = parse_gakusai(fetched[url], event)
        if not details:
            continue
        previous = (event.get("price"), event.get("start_time"), event.get("venue"))
        event.update(details)
        accepted += previous != (event.get("price"), event.get("start_time"), event.get("venue"))
        prices += bool(details.get("price"))
        times += bool(details.get("start_time"))
    stats["details_scanned"] = len(fetched)
    stats["details_accepted"] = accepted
    stats["prices_found"] = prices
    stats["times_found"] = times
    stats["detail_fetch_failed"] = sum(x is None for x in fetched.values())
    return events
