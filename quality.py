"""Non-identifying completeness indicators for the published seminar listing.

These are field-presence metrics, not confirmation of factual accuracy.
"""
FIELDS = ("start_date", "start_time", "venue", "price", "deadline", "topics", "audience", "url", "format")


def summarize_quality(events):
    """Count filled event fields after cross-source deduplication."""
    items = list(events)
    total = len(items)
    present = {
        field: sum(
            bool(event.get(field)) for event in items
        )
        for field in FIELDS
    }
    return {
        "total": total,
        "field_presence": present,
        "field_presence_pct": {
            field: round(count * 100 / total, 1) if total else 0.0
            for field, count in present.items()
        },
        "note": "Field presence only; dates, prices and details are not independently verified.",
    }


def summarize_quality_by_source(events):
    """Per-source field completeness for prioritizing real source repairs.

    Derived only from the already deduplicated published events. An event is
    attributed to its retained primary source, never double-counted.
    These figures show filled fields, not independently verified correctness.
    """
    groups = {}
    for event in events:
        source = event.get("source_id") or "unknown"
        groups.setdefault(source, []).append(event)
    return {
        source: summarize_quality(rows)
        for source, rows in sorted(groups.items())
    }


REVIEW_FIELDS = ("start_date", "start_time", "price", "deadline", "format")


def _review_link_type(event):
    """Recognize known detail URL patterns without asserting field availability."""
    import re
    from urllib.parse import urlsplit

    # An event can retain a listing URL while holding a separate official
    # detail page. Only accept recognized first-party detail URL patterns;
    # reservation URLs and arbitrary external links are not evidence.
    source = event.get("source_id")
    urls = [event.get("detail_url"), event.get("url")]
    for candidate in urls:
        try:
            parts = urlsplit(candidate or "")
        except ValueError:
            continue
        if parts.scheme != "https":
            continue
        if (source == "gakusai" and parts.hostname in
                ("gakusai.co.jp", "www.gakusai.co.jp") and
                re.fullmatch(r"/vet/vet-seminar/\\d+/?", parts.path)):
            return "individual_detail"
        if (source == "jaha" and parts.hostname in
                ("jaha.or.jp", "www.jaha.or.jp") and
                parts.path.startswith(("/training/seminar/", "/owners/dog-training/"))):
            return "individual_detail"
    return "listing_or_other" if source in ("jaha", "gakusai") else "unclassified"


def summarize_review_candidates(events, limit=20):
    """Count missing fields and prioritize IDs; do not infer reasons for blanks."""
    by_source = {}
    candidates = []
    for event in events:
        source = event.get("source_id") or "unknown"
        row = by_source.setdefault(source, {
            "total": 0,
            "not_applicable": {"start_time": 0},
            "missing": {field: 0 for field in REVIEW_FIELDS},
            "missing_with_detail_link": {field: 0 for field in REVIEW_FIELDS},
            "missing_without_confirmed_detail_link": {
                field: 0 for field in REVIEW_FIELDS
            },
        })
        row["total"] += 1
        # Recorded/on-demand seminars typically have a viewing period,
        # not one clock-time start. Their blank clock is not a repair target.
        is_on_demand = event.get("format") == "オンデマンド"
        if is_on_demand:
            row["not_applicable"]["start_time"] += 1
        missing = [field for field in REVIEW_FIELDS
                   if not event.get(field)
                   and not (field == "start_time" and is_on_demand)]
        link_type = _review_link_type(event)
        for field in missing:
            row["missing"][field] += 1
            key = ("missing_with_detail_link" if link_type == "individual_detail"
                   else "missing_without_confirmed_detail_link")
            row[key][field] += 1
        if missing and event.get("id"):
            score = (100 if "start_date" in missing else 0)
            score += 20 if link_type == "individual_detail" else 0
            score += len(missing)
            candidates.append((
                -score,
                event.get("start_date") or "9999-99-99",
                str(event["id"]),
                {
                    "id": str(event["id"]),
                    "source_id": source,
                    "start_date": event.get("start_date"),
                    "link_type": link_type,
                    "missing": missing,
                },
            ))
    candidates.sort(key=lambda item: item[:3])
    return {
        "source_summary": dict(sorted(by_source.items())),
        "priority_review": [item[3] for item in candidates[:max(0, limit)]],
        "review_candidate_total": len(candidates),
        "note": (
            "Missing means only that the published field is blank, not that "
            "the official source lacks the information. For on-demand events "
            "a blank start_time is considered not applicable. A detail link "
            "is recognized by URL pattern, not verified page content."
        ),
    }
