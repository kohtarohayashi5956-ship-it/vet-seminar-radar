# -*- coding: utf-8 -*-
"""Conservative overrides for source-verified corrections.

Only fill a missing deadline for the exact same event, date and official URL.
Never overwrite a different extracted value; mismatches require human review.
"""
import datetime
import json
import os
import re
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
        proposed = {field: rule[field] for field in
                    ("deadline", "start_time", "end_time") if field in rule}
        if not proposed:
            conflicts.append(rule["id"])
            continue
        try:
            start = datetime.date.fromisoformat(event["start_date"])
            if "deadline" in proposed:
                deadline = datetime.date.fromisoformat(proposed["deadline"])
                if deadline > start:
                    raise ValueError("deadline after event")
            for field in ("start_time", "end_time"):
                if field in proposed:
                    value = proposed[field]
                    if not isinstance(value, str) or not re.fullmatch(
                            r"(?:[01]\d|2[0-3]):[0-5]\d", value):
                        raise ValueError("invalid time")
                    h, m = map(int, value.split(":"))
                    if h > 23 or m > 59:
                        raise ValueError("invalid time")
            start_time = proposed.get("start_time", event.get("start_time"))
            end_time = proposed.get("end_time", event.get("end_time"))
            if start_time and end_time and end_time <= start_time:
                raise ValueError("invalid time order")
        except (ValueError, TypeError):
            conflicts.append(rule["id"])
            continue
        if any(event.get(field) and event[field] != value
               for field, value in proposed.items()):
            conflicts.append(rule["id"])
            continue
        changed = False
        for field, value in proposed.items():
            if not event.get(field):
                event[field] = value
                changed = True
        if changed:
            filled.append(rule["id"])
    return filled, conflicts
