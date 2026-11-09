# -*- coding: utf-8 -*-
"""Conservative overrides for source-verified corrections.

Only fill a missing deadline for the exact same event, date and official URL.
Never overwrite a different extracted value; mismatches require human review.
"""
import datetime
import json
import os
from urllib.parse import urlsplit

PATH = os.path.join(os.path.dirname(__file__), "data", "verified_corrections.json")


def _identity_url(url):
    try:
        part = urlsplit(url)
        return (part.hostname or "").removeprefix("www.").lower(), part.path.rstrip("/")
    except (TypeError, ValueError):
        return None


def apply_verified_corrections(store, path=PATH):
    """Return (filled, conflicts); mutate only matching records in place."""
    if not os.path.exists(path):
        return [], []
    with open(path, encoding="utf-8") as f:
        rules = json.load(f).get("corrections", [])
    filled, conflicts = [], []
    for rule in rules:
        event = store.get(rule.get("id"))
        if not event:
            continue
        if (event.get("source_id") != rule.get("source_id")
                or event.get("start_date") != rule.get("start_date")
                or _identity_url(event.get("url")) != _identity_url(rule.get("url"))):
            conflicts.append(rule.get("id"))
            continue
        new_value = rule.get("deadline")
        if not isinstance(new_value, str):
            conflicts.append(rule.get("id"))
            continue
        try:
            deadline = datetime.date.fromisoformat(new_value)
            start = datetime.date.fromisoformat(event["start_date"])
        except (ValueError, TypeError):
            conflicts.append(rule.get("id"))
            continue
        if deadline > start:
            conflicts.append(rule.get("id"))
            continue
        existing = event.get("deadline")
        if not existing:
            event["deadline"] = new_value
            filled.append(rule["id"])
        elif existing != new_value:
            conflicts.append(rule["id"])
    return filled, conflicts
