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


# Only actual section headings or inline fee labels, never a TOC link such
# as "受講料・お申込 <#section>".
FEE_HEADING = re.compile(
    r"^(?:受講料|参加費|受講料金)(?:\s*[（(]税込[）)])?\s*(?:[：:](.*))?$"
)
FEE_AMOUNT = re.compile(r"\d[\d,，]*\s*円")
FEE_STOP = re.compile(
    r"^(?:申込|お申込み|お申し込み|申込み|受付|キャンセル|"
    r"日時|日程|開催日|講師|会場|対象|定員|注意事項|"
    r"お問合せ|お問い合わせ|主催|共催|支払|お支払|"
    r"プログラム|講義内容|備考|参加方法)"
)


def _explicit_course_fee(lines):
    """Accept only values under a short explicitly labelled fee section."""
    for index, line in enumerate(lines):
        heading = FEE_HEADING.match(line)
        if not heading:
            continue
        values = []
        rest = (heading.group(1) or "").strip(" ：:")
        if rest:
            values.append(rest)
        # Real JAHA price tables can have multiple separate header/cell
        # lines between the section heading and the first amount.
        for next_line in lines[index + 1:index + 35]:
            if FEE_STOP.match(next_line) or FEE_HEADING.match(next_line):
                break
            # An unrelated navigation link is not a reason to read fees
            # from another section. Skip links, but keep labelled prices.
            if re.search(r"<https?://", next_line):
                if FEE_AMOUNT.search(next_line):
                    values.append(re.split(r"<https?://", next_line, maxsplit=1)[0])
                continue
            values.append(next_line)
        eligible = [
            value for value in values
            if (FEE_AMOUNT.search(value) or re.fullmatch(r"無料|無料[（(][^）)]{1,35}[）)]", value))
            and len(value) <= 150
        ]
        if not eligible:
            continue
        price = "／".join(eligible[:3])[:300]
        explicitly_free = bool(
            len(eligible) == 1
            and re.fullmatch(r"無料|無料[（(][^）)]{1,35}[）)]", eligible[0])
        )
        return price, True if explicitly_free else None
    return None, None


def _short_date_session_time(lines, start_date):
    """Match a uniquely dated session time to a year-anchored course schedule.

    Only supports same-year, short month/day session lines (e.g. パート2
    11月14日 14:00-17:00) when the SAME page explicitly prints a dated
    multi-session announcement including that short date. Other years,
    registration rows, and non-session timetables are never inferred.
    """
    try:
        target = datetime.date.fromisoformat(start_date)
    except (TypeError, ValueError):
        return None
    anchored = False
    for line in lines:
        if EXCLUDE.search(line) or REGISTRATION.match(line):
            continue
        full = _dates(line)
        if not full or not re.search(r"配信|開催|講義|日程|日時", line):
            continue
        if any(datetime.date.fromisoformat(day).year != target.year for day in full):
            continue
        if not any(abs((datetime.date.fromisoformat(day) - target).days) <= 45 for day in full):
            continue
        short = {(int(m), int(d)) for m, d in SHORT.findall(line)}
        if (target.month, target.day) in short and len(short) >= 2:
            anchored = True
            break
    if not anchored:
        return None
    candidates = set()
    for line in lines:
        if REGISTRATION.match(line) or EXCLUDE.search(line):
            continue
        if not re.search(r"^(?:パート\s*\d+|第\s*\d+\s*回|講義|開催日時|日程|日時)", line):
            continue
        short = SHORT.findall(line)
        if len(short) != 1 or tuple(map(int, short[0])) != (target.month, target.day):
            continue
        if len(_dates(line)) > 1:
            continue
        t1, t2 = _times(line)
        if t1 and t2:
            candidates.add((t1, t2))
    return next(iter(candidates)) if len(candidates) == 1 else None


def _date_from_numbered_course(lines, event):
    """Corroborate a session using an explicit academic year and round/date.

    This applies only to JAHA's published numbered schedule table; it does
    not extrapolate dates from registration or cancellation prose.
    """
    title = event.get("title") or ""
    date_str = event.get("start_date")
    round_match = re.search(r"第\s*([1-9])\s*回", unicodedata.normalize("NFKC", title))
    if not round_match or not date_str:
        return False
    try:
        target = datetime.date.fromisoformat(date_str)
    except ValueError:
        return False
    round_num = round_match.group(1)
    year_heading = next((int(m.group(1)) for line in lines
                         if (m := re.search(r"(20\d{2})年度\s*(?:開催スケジュール|講座内容)", line))), None)
    if year_heading is None:
        return False
    if not (target.year == year_heading or target.year == year_heading + 1):
        return False
    occurrences = []
    for i, line in enumerate(lines):
        if not re.match(rf"^第\s*{round_num}\s*回(?:\s|\||$)", line):
            continue
        # Include short, split table-cell date; stop at another numbered round.
        scope = " ".join(lines[i:min(len(lines), i+4)])
        if re.search(r"受付|キャンセル|申込締切", scope):
            continue
        matched = re.search(
            r"(?<!\d)(1[0-2]|0?[1-9])\s*月\s*(3[01]|[12]\d|0?[1-9])"
            r"\s*(?:[～〜~-]\s*(?:3[01]|[12]\d|0?[1-9]))?\s*日", scope
        )
        if not matched:
            continue
        month, day = map(int, matched.groups())
        year = year_heading + (month < 4)
        if (year, month, day) == (target.year, target.month, target.day):
            occurrences.append(scope)
    return len(occurrences) == 1


def _numbered_course_time(lines, event):
    """Use only a uniquely dated row of an explicitly year-anchored course."""
    if not _date_from_numbered_course(lines, event):
        return None
    target = datetime.date.fromisoformat(event["start_date"])
    title = unicodedata.normalize("NFKC", event.get("title") or "")
    match = re.search(r"第\s*([1-9])\s*回", title)
    if not match:
        return None
    n = match.group(1)
    schedules = set()
    for i, line in enumerate(lines):
        if not re.match(rf"^第\s*{n}\s*回(?:\s|\||$)", line):
            continue
        for nxt in lines[i:min(len(lines), i+4)]:
            if nxt != line and re.match(r"^第\s*[1-9]\s*回(?:\s|\||$)", nxt):
                break
            if REGISTRATION.match(nxt) or EXCLUDE.search(nxt):
                continue
            dates = _dates(nxt)
            short = SHORT.findall(nxt)
            # Exactly one same-day date must appear WITH its time range.
            if len(short) != 1:
                continue
            mon, day = map(int, short[0])
            if (mon, day) != (target.month, target.day):
                continue
            if dates and dates != [target.isoformat()]:
                continue
            first, last = _times(nxt)
            if first and last:
                schedules.add((first, last))
    return next(iter(schedules)) if len(schedules) == 1 else None


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
    if (not schedule_matches
            and not _short_date_session_time(lines, start_date)
            and not _date_from_numbered_course(lines, event)):
        return {}
    out = {}
    deadline = _registration_deadline(lines, start_date)
    if deadline and not event.get("deadline"):
        out["deadline"] = deadline
    if not event.get("price"):
        price, is_free = _explicit_course_fee(lines)
        if price:
            out["price"] = price
            if is_free and event.get("is_free") is None:
                out["is_free"] = True
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
    session_time = _short_date_session_time(lines, start_date)
    numbered_time = _numbered_course_time(lines, event)
    # Independent corroborations must agree; never prefer one conflicting row.
    distinct = set(matches)
    if session_time:
        distinct.add(session_time)
    if numbered_time:
        distinct.add(numbered_time)
    if len(distinct) == 1:
        t1, t2 = next(iter(distinct))
        if not event.get("start_time") or event["start_time"] == t1:
            if not event.get("end_time") or event["end_time"] == t2:
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
    # Aggregate diagnostics only: no page contents or personal data in logs.
    detail_pages_with_fee_label = sum(
        any(FEE_HEADING.match(v.strip()) for v in (page or "").splitlines())
        for page in fetched.values()
    )
    detail_pages_with_amount = sum(
        any(FEE_AMOUNT.search(v) for v in (page or "").splitlines())
        for page in fetched.values()
    )
    detail_pages_with_parsed_fee = sum(
        bool(_explicit_course_fee([unicodedata.normalize("NFKC", v.strip())
                                   for v in (page or "").splitlines() if v.strip()])[0])
        for page in fetched.values()
    )
    # Official detail paths + boolean flags only. No copied page body.
    fee_checks = []
    for url, page in fetched.items():
        lines = ([unicodedata.normalize("NFKC", value.strip())
                  for value in page.splitlines() if value.strip()] if page else [])
        parsed_price = _explicit_course_fee(lines)[0] if lines else None
        same_page = [(day, e) for day, course_url, e in candidates if course_url == url]
        eligible_dates = sorted({
            day for day, event in same_page
            if page and parse_jaha_detail(page, event)
        })
        fee_checks.append({
            "path": urlsplit(url).path,
            "fee_label": any(FEE_HEADING.match(value) for value in lines),
            "yen_amount": any(FEE_AMOUNT.search(value) for value in lines),
            "fee_section": bool(parsed_price),
            "corroborated_dates": eligible_dates,
        })
    accepted = 0
    times_found = 0
    prices_found = 0
    for _, url, e in candidates:
        if not fetched.get(url):
            continue
        detail = parse_jaha_detail(fetched[url], e)
        if detail:
            before = (e.get("deadline"), e.get("start_time"), e.get("end_time"),
                      e.get("price"))
            missing_start = not e.get("start_time")
            missing_price = not e.get("price")
            e.update(detail)
            updated = (e.get("deadline"), e.get("start_time"), e.get("end_time"),
                       e.get("price"))
            accepted += before != updated
            times_found += bool(missing_start and e.get("start_time"))
            prices_found += bool(missing_price and e.get("price"))
    stats["details_scanned"] = len(fetched)
    stats["details_accepted"] = accepted
    stats["deadlines_found"] = sum(bool(e.get("deadline")) for _, _, e in candidates)
    stats["times_found"] = times_found
    stats["prices_found"] = prices_found
    stats["fee_label_pages"] = detail_pages_with_fee_label
    stats["fee_amount_pages"] = detail_pages_with_amount
    stats["fee_parsed_pages"] = detail_pages_with_parsed_fee
    stats["fee_detail_checks"] = fee_checks
    stats["detail_fetch_failed"] = sum(v is None for v in fetched.values())
    return events
