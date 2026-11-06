# -*- coding: utf-8 -*-
"""ページ本文のテキスト化と、Claudeによるセミナー情報の抽出・原文照合。"""
import datetime
import hashlib
import json
import os
import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import config

PROMPT_VERSION = "v1"

AUDIENCES = ["獣医師", "動物看護師", "トリマー", "動物病院スタッフ", "学生", "一般"]
FORMATS = ["現地", "ライブ配信", "オンデマンド", "ハイブリッド"]
TOPICS = ["内科", "外科", "麻酔・救急", "画像診断", "腫瘍", "循環器", "皮膚・耳", "眼科",
          "歯科", "神経", "内分泌", "消化器", "泌尿器", "猫", "エキゾチック", "栄養",
          "看護・技術", "院内教育・経営", "行動・しつけ", "学会・大会", "その他"]


# --------------------------------------------------------------------------
# HTML -> テキスト
# --------------------------------------------------------------------------
def html_to_text(html, base_url):
    """リンクを「ラベル <URL>」の形で残したテキストにする。"""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg", "iframe", "form", "nav", "footer", "template"]):
        t.decompose()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            a.replace_with(a.get_text(" ", strip=True) + " ")
            continue
        url = urljoin(base_url, href)
        label = a.get_text(" ", strip=True)
        if not label:
            img = a.find("img")
            label = (img.get("alt") or "").strip() if img else ""
        a.replace_with(f"{label} <{url}> " if label else f"<{url}> ")
    raw = soup.get_text("\n")
    lines, prev = [], None
    for ln in raw.splitlines():
        ln = re.sub(r"[ \t\u3000]+", " ", ln).strip()
        if not ln or ln == prev:
            continue
        lines.append(ln)
        prev = ln
    return "\n".join(lines)


def split_text(text, limit=None):
    limit = limit or config.MAX_TEXT_CHARS
    if len(text) <= limit:
        return [text]
    chunks, cur, size = [], [], 0
    for ln in text.splitlines():
        if size + len(ln) + 1 > limit and cur:
            chunks.append("\n".join(cur))
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s or ""))


# --------------------------------------------------------------------------
# プロンプト
# --------------------------------------------------------------------------
SYSTEM = """あなたは動物病院向けセミナー情報の整理担当です。与えられたWebページの本文から、
獣医師・愛玩動物看護師などが参加できるセミナー・実習・講習会・学会・大会の情報を抜き出し、JSON配列だけを返します。
前後の説明やコードフェンスは付けません。本文に書かれていないことは絶対に補わず、不明な項目は null にします。"""

USER_TMPL = """今日の日付: {today}
情報源: {source}
ページ: {page_url}
ページの種類のヒント: {hint}

# 出力する各要素のキー
- title: 催しの名称（本文の表記をそのまま。装飾の【】などは残してよい）
- start_date: 開始日 YYYY-MM-DD。年が本文や見出しから明確な場合のみ補う。不明なら null
- end_date: 終了日 YYYY-MM-DD（連日開催のとき）。単日なら null
- start_time / end_time: "HH:MM"。不明なら null
- format: {formats} のいずれか。判断できなければ null
- venue: 会場名（オンラインなら null）
- prefecture: 都道府県名（例: 東京都）。不明・オンラインなら null
- audience: {audiences} から該当するものの配列。不明なら []
- topics: {topics} から最大2つの配列
- price: 料金の表記を短くそのまま（例: "会員 385,000円／一般 440,000円"）。不明なら null
- is_free: 無料と明記されていれば true、そうでなければ null
- status: 本文にある受付状況の表記（例: "受付中" "満席" "残り3席" "受付終了"）。なければ null
- deadline: 申込締切 YYYY-MM-DD。不明なら null
- organizer: 主催者名。不明なら null
- url: その催し専用の詳細ページ。本文中に <URL> の形で出てくるものだけを使う。なければ null
- evidence: 本文からそのままコピーした連続20〜60文字（題名の一部を含む箇所）

# ルール
- 複数日に同じ催しが繰り返し載っている場合は1件にまとめ、start_date と end_date で表す。
- 「第1回」「第2回」のように日が別々の回は、別の要素にする。
- 商品、求人、書籍、会員募集など、セミナーでないものは出さない。
- 飼い主向けのしつけ教室などは出してよいが、audience は ["一般"] にする。
- 推測で埋めない。迷ったら null。

# ページ本文
{text}
"""


def build_prompt(source_name, page_url, hint, text, today):
    return USER_TMPL.format(
        today=today, source=source_name, page_url=page_url, hint=hint,
        formats="/".join(FORMATS), audiences="/".join(AUDIENCES), topics="/".join(TOPICS),
        text=text,
    )


# --------------------------------------------------------------------------
# JSONの頑健な読み取り（途中で切れていても、完成した要素だけ拾う）
# --------------------------------------------------------------------------
def parse_json_array(text):
    s = text.strip()
    s = re.sub(r"^```(?:json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    start = s.find("[")
    if start < 0:
        return []
    dec = json.JSONDecoder()
    i = start + 1
    items = []
    while i < len(s):
        while i < len(s) and s[i] in " \r\n\t,":
            i += 1
        if i >= len(s) or s[i] == "]":
            break
        try:
            obj, end = dec.raw_decode(s, i)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict):
            items.append(obj)
        i = end
    return items


# --------------------------------------------------------------------------
# 検証・正規化
# --------------------------------------------------------------------------
def _date(v):
    if not isinstance(v, str):
        return None
    try:
        return datetime.date.fromisoformat(v.strip()).isoformat()
    except ValueError:
        return None


def _time(v):
    if isinstance(v, str) and re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", v.strip()):
        h, m = v.strip().split(":")
        return f"{int(h):02d}:{m}"
    return None


def _str(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return None


def url_set(text):
    return {u.rstrip(".,)") for u in re.findall(r"<(https?://[^>\s]+)>", text)}


def validate(raw_items, text, page_url, today, stats):
    """モデルの出力を検証して、取り込める形にする。"""
    ntext = norm(text)
    urls = url_set(text)
    out, seen = [], set()
    for it in raw_items:
        title = _str(it.get("title"))
        if not title:
            continue
        title_ok = norm(title) in ntext
        ev = _str(it.get("evidence"))
        ev_ok = bool(ev) and norm(ev) in ntext
        if not title_ok and not ev_ok:
            stats["dropped_not_in_text"] = stats.get("dropped_not_in_text", 0) + 1
            continue

        start = _date(it.get("start_date"))
        end = _date(it.get("end_date"))
        if end and start and end < start:
            end = None
        date_ok = True
        if start:
            d = datetime.date.fromisoformat(start)
            if not (today - datetime.timedelta(days=400) <= d <= today + datetime.timedelta(days=500)):
                date_ok = False

        fmt = it.get("format") if it.get("format") in FORMATS else None
        aud = [a for a in (it.get("audience") or []) if a in AUDIENCES] if isinstance(it.get("audience"), list) else []
        top = [t for t in (it.get("topics") or []) if t in TOPICS][:2] if isinstance(it.get("topics"), list) else []

        url = _str(it.get("url"))
        url_is_page = False
        if url:
            url = url.rstrip(".,)")
            if url not in urls:
                url = None
        if not url:
            url, url_is_page = page_url, True

        key = (norm(title), start)
        if key in seen:
            continue
        seen.add(key)

        out.append({
            "title": title,
            "start_date": start,
            "end_date": end,
            "start_time": _time(it.get("start_time")),
            "end_time": _time(it.get("end_time")),
            "format": fmt,
            "venue": _str(it.get("venue")),
            "prefecture": _str(it.get("prefecture")),
            "audience": aud,
            "topics": top,
            "price": _str(it.get("price")),
            "is_free": True if it.get("is_free") is True else None,
            "status": _str(it.get("status")),
            "deadline": _date(it.get("deadline")),
            "abstract_deadline": _date(it.get("abstract_deadline")),
            "detail_url": _str(it.get("detail_url")),
            "certification_note": _str(it.get("certification_note")),
            "certification_url": _str(it.get("certification_url")),
            "organizer": _str(it.get("organizer")),
            "speaker": _str(it.get("speaker")),
            "url": url,
            "url_is_page": url_is_page,
            "verified": bool(title_ok and ev_ok and date_ok),
        })
    return out


# --------------------------------------------------------------------------
# 抽出（キャッシュつき）
# --------------------------------------------------------------------------
CACHE_PATH = os.path.join("data", "extract_cache.json")


def _load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _save_cache(cache):
    os.makedirs("data", exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


class Extractor:
    def __init__(self, client):
        self.client = client
        self.cache = _load_cache()
        self.calls = 0
        self.cache_hits = 0

    def extract(self, source_name, page_url, hint, text, today, stats):
        results = []
        for chunk in split_text(text):
            key = hashlib.sha1(
                f"{PROMPT_VERSION}|{config.MODEL}|{page_url}|{chunk}".encode("utf-8")
            ).hexdigest()
            if key in self.cache:
                raw_items = self.cache[key]
                self.cache_hits += 1
            else:
                if self.client is None:
                    stats["skipped_no_ai"] = stats.get("skipped_no_ai", 0) + 1
                    continue
                prompt = build_prompt(source_name, page_url, hint, chunk, today.isoformat())
                msg = self.client.messages.create(
                    model=config.MODEL, max_tokens=config.MAX_OUTPUT_TOKENS,
                    system=SYSTEM, messages=[{"role": "user", "content": prompt}],
                )
                self.calls += 1
                body = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
                raw_items = parse_json_array(body)
                if getattr(msg, "stop_reason", "") == "max_tokens":
                    stats["truncated"] = stats.get("truncated", 0) + 1
                self.cache[key] = raw_items
                _save_cache(self.cache)
            results.extend(validate(raw_items, chunk, page_url, today, stats))
        return results
