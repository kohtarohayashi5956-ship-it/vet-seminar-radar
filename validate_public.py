#!/usr/bin/env python3
"""Safety and format validation before publishing to public GitHub Pages."""
import json
import os
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

class Payload(HTMLParser):
    def __init__(self):
        super().__init__()
        self.collect = False
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "payload":
            self.collect = True
    def handle_endtag(self, tag):
        if tag == "script":
            self.collect = False
    def handle_data(self, data):
        if self.collect:
            self.text.append(data)


def validate():
    with open("index.html", encoding="utf-8") as f:
        text = f.read()
    parser = Payload(); parser.feed(text)
    payload = json.loads("".join(parser.text))
    assert isinstance(payload.get("events"), list)
    event_ids = [event.get("id") for event in payload["events"]]
    assert all(isinstance(eid, str) and eid for eid in event_ids)
    assert len(event_ids) == len(set(event_ids)), "duplicate public event IDs"
    for event in payload["events"]:
        assert isinstance(event.get("title"), str) and event["title"].strip()
        assert len(event["title"]) < 2000
        u = event.get("url")
        if u:
            p = urlparse(u)
            assert p.scheme in ("https", "http") and p.netloc
        for field in ("start_date", "end_date", "deadline"):
            d = event.get(field)
            assert d is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)
        if event.get("start_date") and event.get("deadline"):
            assert event["deadline"] <= event["start_date"], "deadline after event"
        if event.get("is_free") is True and event.get("price"):
            assert not re.search(r"[0-9０-９][0-9０-９,，]*\s*円", event["price"]), "paid fee marked free"
        assert not any(k in event for k in ("raw_html", "raw_text", "page_text", "evidence"))
    with open("data/events.json", encoding="utf-8") as f:
        db=json.load(f)
    assert isinstance(db.get("events"), dict)
    with open("data/run_status.json", encoding="utf-8") as f:
        status=json.load(f)
    assert isinstance(status.get("source_results"), list)
    assert isinstance(status.get("total_events"), int)
    assert status["total_events"] == len(payload["events"]), "status count differs from published page"
    embedded_status = payload.get("run_status")
    assert isinstance(embedded_status, dict), "missing embedded run status"
    assert embedded_status.get("checked_at_jst") == status.get("checked_at_jst"), (
        "published page contains an older collection status"
    )
    quality = status.get("data_quality") or {}
    embedded_quality = embedded_status.get("data_quality") or {}
    assert quality == embedded_quality, "published quality metrics differ from run status"
    assert quality.get("total") == len(payload["events"]), "quality total differs from published page"
    for field in ("start_date", "start_time", "venue", "price", "deadline", "topics", "audience", "url"):
        count = sum(1 for event in payload["events"] if event.get(field))
        assert quality.get("field_presence", {}).get(field) == count, (
            f"incorrect published {field} completeness"
        )
    assert "sk-ant-" not in text
    print(f"public validation OK: {len(payload['events'])} events, {len(status['source_results'])} source results")

if __name__ == "__main__":
    validate()
