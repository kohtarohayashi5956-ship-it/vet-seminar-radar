# -*- coding: utf-8 -*-
"""Optional, conservative Gakusai detail enrichment (no API charges)."""
import re
import unicodedata
from urllib.parse import urlsplit
from extract import html_to_text
from free_extract import _dates, _times

LIMIT = 12
TIERS = re.compile(r"(法人[・･]個人会員|一般獣医師|法人会員|個人会員)")
AMOUNT = re.compile(r"\d[\d,]*\s*円(?:\s*\(税込\s*\d[\d,]*\s*円\))?")


def detail_url(event):
    """Use a known first-party course detail even when the listing URL is primary."""
    for candidate in (event.get("detail_url"), event.get("url")):
        try:
            u = urlsplit(candidate or "")
        except ValueError:
            continue
        if (u.scheme == "https"
                and not u.username and not u.password
                and u.hostname in ("www.gakusai.co.jp", "gakusai.co.jp")
                and re.fullmatch(r"/vet/vet-seminar/\d+/?", u.path)):
            return u.scheme + "://" + u.netloc + u.path
    return None


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



def _no297_material_fee(lines, event):
    """Add mandatory dry-lab materials only to the exact Jan 24 on-site event."""
    url = detail_url(event)
    if (not url or url.rstrip("/") != "https://www.gakusai.co.jp/vet/vet-seminar/35591"
            or event.get("start_date") != "2027-01-24"
            or event.get("title") != "失敗しない腸管吻合 ミニドライラボ&セミナー"
            or event.get("format") in ("ライブ配信", "オンデマンド")):
        return None
    fees = section(lines, "来場受講料", ["ウェブ受講料", "開催にあたって"], 24)
    member = "法人・個人会員 9,000円(税込9,900円)+ミニドライラボ材料費 4,500円(税込4,950円)"
    general = "一般獣医師 27,000円(税込29,700円)+ミニドライラボ材料費 4,500円(税込4,950円)"
    norm = lambda x: re.sub(r"\s+", "", unicodedata.normalize("NFKC", x))
    def has_fee(tier, amount, taxed):
        return sum(
            tier in row and amount in norm(row) and taxed in norm(row)
            and "材料費4,500円" in norm(row) and "4,950円" in norm(row)
            for row in fees
        ) == 1
    # Each official attendee tier explicitly carries the material fee.
    # The separate explanatory footnote may be split across HTML elements
    # and is not necessary corroboration when both full tier rows agree.
    if not (has_fee("法人・個人会員", "9,000円", "9,900円")
            and has_fee("一般獣医師", "27,000円", "29,700円")):
        return None
    existing = event.get("price")
    base = "法人・個人会員 9,000円(税込9,900円)／一般獣医師 27,000円(税込29,700円)"
    complete = member + "／" + general
    if existing and norm(existing) not in (norm(base), norm(complete)):
        return None
    if existing and norm(existing) == norm(complete):
        return None
    return complete



def parse_gakusai(text, event):
    """Only accept values belonging to an exact-date detail page."""
    lines = [unicodedata.normalize("NFKC", x.strip()) for x in text.splitlines() if x.strip()]
    schedule = section(lines, "開催日時・会場",
                       ["来場受講料", "ウェブ受講料", "開催にあたって"], 28)
    start = event.get("start_date")
    idx = next((i for i, ln in enumerate(schedule)
                if start and _dates(ln) == [start]
                and len(re.findall(r"\d{1,2}月\d{1,2}日", ln)) == 1), None)
    if idx is None:
        return {}
    date_line = schedule[idx]
    t1, t2 = _times(date_line)
    # A single detail-card schedule sometimes wraps its clock range to
    # the immediately following line. Accept ONLY a standalone range,
    # never a second date, location, registration/cancellation time, or
    # another field. The preceding line must uniquely match this event.
    if not t1 and idx + 1 < len(schedule):
        next_line = schedule[idx + 1]
        bare_range = re.fullmatch(
            r"\s*([01]?\d|2[0-3])[：:]([0-5]\d)\s*[〜~～－―–-]"
            r"\s*([01]?\d|2[0-3])[：:]([0-5]\d)\s*",
            next_line,
        )
        if bare_range:
            t1, t2 = _times(next_line)
    if event.get("start_time") and t1 and event["start_time"] != t1:
        return {}
    out = {}
    if t1 and not event.get("start_time"):
        out["start_time"] = t1
    if t2 and not event.get("end_time"):
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
            if not event.get("price"):
                out["price"] = "／".join(prices[:3])
                out["is_free"] = None
            # The course's own priced registration tiers explicitly
            # identify veterinarians, regardless of whether price is filled.
            if any("一般獣医師" in price for price in prices):
                audience = event.get("audience") or []
                if "獣医師" not in audience:
                    out["audience"] = audience + ["獣医師"]
    # No.297 requires a separate material fee for on-site participation.
    # This may correct an incomplete previously collected base tariff.
    full_price = _no297_material_fee(lines, event)
    if full_price:
        out["price"] = full_price
    # Do not equate cancellation deadlines with registration deadlines.
    return out


def enrich_gakusai(events, fetcher, today, stats):
    candidates = [(e["start_date"], detail_url(e), e) for e in events
                  if e.get("start_date") and e["start_date"] >= today.isoformat()
                  and detail_url(e)]
    candidates.sort(key=lambda x: (x[0], x[1]))
    # Rotate a bounded crawl across unique official detail URLs. Otherwise
    # an annual programme with >LIMIT pages repeatedly checks its earliest
    # events and may never visit later ones.
    unique_urls = list(dict.fromkeys(url for _, url, _ in candidates))
    if len(unique_urls) > LIMIT:
        start_at = (today.toordinal() * LIMIT) % len(unique_urls)
        selected = (unique_urls[start_at:] + unique_urls[:start_at])[:LIMIT]
    else:
        selected = unique_urls
    fetched = {}
    for url in selected:
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
        previous = (event.get("price"), event.get("start_time"), event.get("end_time"),
                    event.get("venue"), event.get("prefecture"), event.get("format"),
                    event.get("audience"))
        event.update(details)
        current = (event.get("price"), event.get("start_time"), event.get("end_time"),
                   event.get("venue"), event.get("prefecture"), event.get("format"),
                   event.get("audience"))
        accepted += previous != current
        prices += bool(details.get("price"))
        times += bool(details.get("start_time"))
    stats["detail_candidates"] = len(unique_urls)
    stats["detail_deferred"] = len(unique_urls) - len(fetched)
    stats["details_scanned"] = len(fetched)
    stats["details_accepted"] = accepted
    stats["prices_found"] = prices
    stats["times_found"] = times
    stats["detail_fetch_failed"] = sum(x is None for x in fetched.values())
    return events
