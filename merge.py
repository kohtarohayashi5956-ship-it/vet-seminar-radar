# -*- coding: utf-8 -*-
"""イベントの統合・重複除去・保存。"""
import csv
import datetime
import difflib
import hashlib
import json
import os
from urllib.parse import urlsplit, parse_qsl

import config
from extract import AUDIENCES, FORMATS, TOPICS, norm

STORE_PATH = os.path.join("data", "events.json")
MANUAL_PATH = os.path.join("data", "manual_events.csv")

FIELDS = ["title", "start_date", "end_date", "start_time", "end_time", "format", "venue",
          "prefecture", "audience", "topics", "price", "is_free", "status", "deadline",
          "organizer", "speaker", "url", "detail_url", "abstract_deadline",
          "certification_note", "certification_url", "certification_program",
          "url_is_page", "verified"]


def event_id(source_id, title, start_date):
    return hashlib.sha1(f"{source_id}|{norm(title)}|{start_date}".encode("utf-8")).hexdigest()[:12]


def _score(e):
    keys = ["start_date", "start_time", "format", "venue", "prefecture", "price", "status",
            "deadline", "abstract_deadline", "certification_note", "certification_program", "organizer", "end_date"]
    s = sum(1 for k in keys if e.get(k))
    s += len(e.get("audience") or []) + len(e.get("topics") or [])
    if e.get("verified"):
        s += 2
    if not e.get("url_is_page"):
        s += 1
    return s


# --------------------------------------------------------------------------
def load_store():
    if os.path.exists(STORE_PATH):
        try:
            with open(STORE_PATH, encoding="utf-8") as f:
                return json.load(f).get("events", {})
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def save_store(events, now):
    os.makedirs("data", exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump({"updated": now.isoformat(timespec="seconds"), "events": events},
                  f, ensure_ascii=False, indent=1)


def update_store(store, fresh, source, _unused, today):
    """今回取得した分を蓄積に反映する。"""
    t = today.isoformat()
    added = updated = 0
    for e in fresh:
        eid = event_id(source["id"], e["title"], e.get("start_date"))
        rec = {k: e.get(k) for k in FIELDS}
        rec.update({"id": eid, "source": source["name"], "source_id": source["id"], "last_seen": t})
        if eid in store:
            rec["first_seen"] = store[eid].get("first_seen", t)
            updated += 1
        else:
            rec["first_seen"] = t
            added += 1
        store[eid] = rec
    return added, updated


def reconcile_source(store, fresh, source, today):
    """Replace stale records after a *complete, nonempty* source scan.

    This removes previously misassigned dates, without deleting records when
    the source is blocked, empty, or failed part way through collection.
    """
    if not fresh:
        return 0, 0, 0
    fresh_ids = {event_id(source["id"], e["title"], e.get("start_date")) for e in fresh}
    old_ids = {k for k, e in store.items() if e.get("source_id") == source["id"]}
    added, updated = update_store(store, fresh, source, None, today)
    obsolete = old_ids - fresh_ids
    for k in obsolete:
        store.pop(k, None)
    return added, updated, len(obsolete)


def purge(store, today):
    drop = []
    for eid, e in store.items():
        ref = e.get("end_date") or e.get("start_date")
        if ref:
            if datetime.date.fromisoformat(ref) < today - datetime.timedelta(days=config.KEEP_PAST_DAYS):
                drop.append(eid)
        else:
            ls = datetime.date.fromisoformat(e.get("last_seen", today.isoformat()))
            if ls < today - datetime.timedelta(days=config.KEEP_UNDATED_DAYS):
                drop.append(eid)
    for eid in drop:
        del store[eid]
    return len(drop)


# --------------------------------------------------------------------------
def _range(e):
    s = e.get("start_date")
    if not s:
        return None
    return s, (e.get("end_date") or s)


def _same_event(a, b):
    """Conservatively merge *cross-source* copies, never separate sessions.

    Previously a common title fragment + same calendar day collapsed different
    sessions in a provider's course (e.g. Life&Tail morning/afternoon).
    """
    # Real providers must retain their distinct sessions. A legacy test
    # fixture shares a source_id across two distinct provider names, so check
    # both fields instead of source_id alone.
    if a.get("source_id") == b.get("source_id") and a.get("source") == b.get("source"):
        return False
    ra, rb = _range(a), _range(b)
    if not ra or not rb:
        return False
    if ra[0] > rb[1] or rb[0] > ra[1]:
        return False
    if a.get("start_time") and b.get("start_time") and a["start_time"] != b["start_time"]:
        return False
    na, nb = norm(a.get("title", "")), norm(b.get("title", ""))
    if not na or not nb:
        return False
    # No substring matching; a common promotional series name is insufficient.
    return na == nb or difflib.SequenceMatcher(None, na, nb).ratio() >= 0.80



def _canonical_event_url(url):
    """Compare the actual event link, ignoring only marketing query parameters."""
    try:
        p = urlsplit(url or "")
        if p.scheme not in ("http", "https") or not p.netloc:
            return None
        query = tuple(sorted((k, v) for k, v in parse_qsl(p.query)
                             if not k.lower().startswith("utm_")))
        return (p.netloc.lower().removeprefix("www."), p.path.rstrip("/"), query)
    except ValueError:
        return None


def _same_source_copy(a, b):
    """A repeated listing of one event, NOT two dates or two sessions."""
    if not a.get("source_id") or a.get("source_id") != b.get("source_id"):
        return False
    if a.get("url_is_page") or b.get("url_is_page"):
        return False
    if not a.get("start_date") or a.get("start_date") != b.get("start_date"):
        return False
    # In particular, keep afternoon/evening sessions if one starts later.
    if a.get("start_time") != b.get("start_time"):
        return False
    ua, ub = _canonical_event_url(a.get("url")), _canonical_event_url(b.get("url"))
    if not ua or ua != ub:
        return False
    ta, tb = norm(a.get("title", "")), norm(b.get("title", ""))
    return bool(ta and tb and difflib.SequenceMatcher(None, ta, tb).ratio() >= 0.92)


def dedupe_cross_source(events):
    """別サイトに同じ催しが載っている場合に1件へまとめる。"""
    events = sorted(events, key=lambda e: (e.get("start_date") or "9999", -_score(e)))
    out = []
    for e in events:
        e = dict(e)
        e.setdefault("also_listed", [])
        hit = None
        for o in out:
            if _same_source_copy(o, e) or _same_event(o, e):
                hit = o
                break
        if hit is None:
            out.append(e)
            continue
        base, other = (hit, e) if _score(hit) >= _score(e) else (e, hit)
        merged = dict(base)
        for k in FIELDS:
            if not merged.get(k) and other.get(k):
                merged[k] = other[k]
        merged["audience"] = sorted(set((base.get("audience") or []) + (other.get("audience") or [])))
        merged["verified"] = bool(base.get("verified") or other.get("verified"))
        lst = set(base.get("also_listed") or []) | set(other.get("also_listed") or [])
        for x in (hit, e):
            lst.add(x.get("source"))
        lst.discard(merged.get("source"))
        merged["also_listed"] = sorted(s for s in lst if s)
        out[out.index(hit)] = merged
    return out


# --------------------------------------------------------------------------
def _split_list(v, allowed):
    items = [x.strip() for x in (v or "").replace("、", "・").replace(",", "・").split("・") if x.strip()]
    return [x for x in items if x in allowed]


def load_manual(today):
    """data/manual_events.csv から手動登録の分を読む。"""
    if not os.path.exists(MANUAL_PATH):
        return []
    out = []
    with open(MANUAL_PATH, encoding="utf-8-sig", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            title = (row.get("title") or "").strip()
            if not title or title.startswith(("(例)", "（例）")):
                continue
            g = lambda k: (row.get(k) or "").strip() or None  # noqa: E731
            fmt = g("format")
            out.append({
                "id": "manual-" + hashlib.sha1(f"{title}|{g('start_date')}".encode("utf-8")).hexdigest()[:8],
                "title": title, "start_date": g("start_date"), "end_date": g("end_date"),
                "start_time": g("start_time"), "end_time": g("end_time"),
                "format": fmt if fmt in FORMATS else None,
                "venue": g("venue"), "prefecture": g("prefecture"),
                "audience": _split_list(row.get("audience"), AUDIENCES),
                "topics": _split_list(row.get("topics"), TOPICS),
                "price": g("price"), "is_free": True if (g("price") or "").startswith("無料") else None,
                "status": g("status"), "deadline": g("deadline"), "organizer": g("organizer"),
                "speaker": g("speaker"), "url": g("url"), "detail_url": g("detail_url"),
                "abstract_deadline": g("abstract_deadline"),
                "certification_note": g("certification_note"), "certification_url": g("certification_url"),
                "url_is_page": False, "verified": True,
                "source": "手動", "source_id": "manual", "manual": True,
                "first_seen": today.isoformat(), "last_seen": today.isoformat(),
            })
    return out
