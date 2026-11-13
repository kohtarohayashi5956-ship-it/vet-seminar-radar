# -*- coding: utf-8 -*-
"""Detect missing numbered Gakusai lecture cards without inventing events."""
import re
import unicodedata

from free_extract import MONTH_DAY


NUMBER = re.compile(r"^No\.\s*(\d{3,4})\b")


def _norm(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or "")).casefold()


def uncovered_gakusai_lectures(listing_text, events):
    """Return official No. identifiers with a date but no matching event.

    This is a diagnostic only. The parser's validation is deliberately
    unchanged; an unparseable listing must never become an invented event.
    Ignore MS (hands-on) cards, web-viewing date ranges, and undated cards.
    """
    lines = [unicodedata.normalize("NFKC", x.strip())
             for x in listing_text.splitlines() if x.strip()]
    heads = [(i, m.group(1)) for i, line in enumerate(lines)
             if (m := NUMBER.match(line))]
    missing = []
    for n, (idx, number) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        # An MS section ends the numbered lecture list.
        ms = next((j for j in range(idx + 1, end)
                   if re.match(r"^MS\s*\d{3,4}\b", lines[j])), end)
        segment = lines[idx:min(end, ms, idx + 9)]
        if not any(MONTH_DAY.search(row.split("ウェブ受講")[0])
                   for row in segment[1:]):
            continue
        title = NUMBER.sub("", segment[0], count=1)
        title = re.sub(r"(?:[»›>]\s*詳細はこちら).*$", "", title)
        title = re.sub(r"<https?://[^>]+>", "", title).strip()
        candidate = _norm(title)
        if not candidate:
            continue
        if not any(_norm(e.get("title")) == candidate for e in events):
            missing.append(number)
    return sorted(set(missing), key=int)
