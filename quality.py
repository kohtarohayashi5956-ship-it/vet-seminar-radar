"""Non-identifying completeness indicators for the published seminar listing.

These are field-presence metrics, not confirmation of factual accuracy.
"""
FIELDS = ("start_date", "start_time", "venue", "price", "deadline", "topics", "audience", "url")


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
