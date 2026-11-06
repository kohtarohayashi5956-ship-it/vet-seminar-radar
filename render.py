# -*- coding: utf-8 -*-
"""events を埋め込んだ単一HTML（index.html）を書き出す。"""
import datetime
import json
import os
from zoneinfo import ZoneInfo

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")


def _json_for_html(obj):
    s = json.dumps(obj, ensure_ascii=False)
    # <script> 内に安全に埋め込む
    return s.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def write_html(events, out_path="index.html", demo=False, sources_summary="", run_status=None):
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    payload = {
        "generated": datetime.datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M JST"),
        "demo": demo,
        "sources_summary": sources_summary,
        "events": events,
        "run_status": run_status or {},
    }
    html = tpl.replace("/*__PAYLOAD__*/null", _json_for_html(payload))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
