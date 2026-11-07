"""Non-identifying completeness indicators for the published seminar listing.

These are field-presence metrics, not confirmation of factual accuracy.
"""
FIELDS = ("start_date", "start_time", "price", "deadline", "topics", "audience", "url")


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
