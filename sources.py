# -*- coding: utf-8 -*-
"""巡回先ごとに「ページ本文テキスト」を作る。各関数は (url, text, hint) を返すジェネレータ。"""
import datetime
import email.utils
import re
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import config
from extract import html_to_text

NS = {"content": "http://purl.org/rss/1.0/modules/content/"}


# --------------------------------------------------------------------------
def _jaha_table_text(html, base_url):
    """Preserve date-to-event association in HTML calendar tables.

    The generic text conversion can merge/split cells in ways that hide date
    markers. The fallback remains the generic text when no table rows match.
    """
    soup = BeautifulSoup(html, "html.parser")
    heading = re.search(r"(20\d{2})\s*年\s*(1[0-2]|[1-9])\s*月", soup.get_text(" ", strip=True))
    if not heading:
        return None
    month = int(heading.group(2))
    lines = [heading.group(1) + "年" + heading.group(2) + "月"]
    found = 0
    for table in soup.find_all("table"):
        active_date = None
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"], recursive=False)
            if not cells:
                continue
            cell_texts = [x.get_text(" ", strip=True) for x in cells]
            for value in cell_texts:
                m = re.match(r"^\s*(1[0-2]|0?[1-9])\s*/\s*([12]?\d|3[01])(?=\D|$)", value)
                if m and int(m.group(1)) == month:
                    active_date = f"{int(m.group(1))}/{int(m.group(2))}"
                    break
            if not active_date:
                continue
            candidates = []
            for a in tr.find_all("a", href=True):
                title = a.get_text(" ", strip=True)
                url = urljoin(base_url, a["href"])
                if (len(title) < 6 or title in ("詳細", "MAP", "前月", "次月")
                        or "/seminar-calendar" in url):
                    continue
                candidates.append((title, url))
            if not candidates:
                continue
            for title, url in candidates:
                lines.append(active_date)
                lines.append(" ".join(cell_texts[:3])[:200])
                lines.append(title + " <" + url + ">")
                lines.append(" ".join(cell_texts[3:])[:400])
                found += 1
    return "\n".join(lines) if found else None


def jaha_pages(src, fetcher, months):
    """JAHAのセミナーカレンダー。月ごとのページを「次月」リンクでたどる。"""
    url = src["start_url"]
    hint = ("月ごとのカレンダー表。各行は 日付・曜日・対象・受付状況・名称・都道府県・会場。"
            "同じ催しが日ごとに繰り返し載る。年月は見出し（例: 2026年11月）から判断する。")
    current = datetime.datetime.now(ZoneInfo("Asia/Tokyo")).date().replace(day=1)
    collected = 0
    # The calendar landing page may begin on the previous month. Do not
    # count those archived pages toward MONTHS_AHEAD.
    for _ in range(months + 12):
        html = fetcher.get(url)
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.get_text(" ", strip=True)
        match = re.search(r"(20\d{2})\s*年\s*(1[0-2]|[1-9])\s*月", heading)
        page_month = (datetime.date(int(match.group(1)), int(match.group(2)), 1)
                      if match else None)
        if page_month is None or page_month >= current:
            yield url, (_jaha_table_text(html, url) or html_to_text(html, url)), hint
            collected += 1
        if collected >= months:
            break
        nxt = None
        for a in soup.find_all("a", href=True):
            if a.get_text(strip=True) == "次月":
                nxt = urljoin(url, a["href"])
                break
        if not nxt or nxt == url:
            break
        url = nxt



# --------------------------------------------------------------------------
def _next_page_url(html, url, seen):
    soup = BeautifulSoup(html, "html.parser")
    base = urlparse(url)
    for a in soup.find_all("a", href=True):
        label = a.get_text(strip=True)
        href = urljoin(url, a["href"])
        p = urlparse(href)
        if p.netloc != base.netloc or href in seen:
            continue
        if label in ("次へ", "次のページ", "Next", "›", "»", ">") or (
            p.path == base.path and "page=" in p.query
        ):
            return href
    return None


def list_pages(src, fetcher):
    """一覧ページ。ページ送りを最大 max_pages までたどる。"""
    hint = "セミナーの一覧ページ。各カードに 状況・題名・日時・形式（実習/ライブ/座学など）が並ぶ。"
    for start in src["urls"]:
        url, seen, n = start, set(), 0
        while url and n < src.get("max_pages", 1):
            if url in seen:
                break
            seen.add(url)
            html = fetcher.get(url)
            n += 1
            yield url, html_to_text(html, url), hint
            url = _next_page_url(html, url, seen)


def single_pages(src, fetcher):
    hint = ("年間スケジュールのページ。月ごとの見出しの下に、No.・講師・題名・日付・会場・"
            "ウェブ受講の開始日が並ぶ。年は「2027 セミナー 開催スケジュール」のような見出しから判断する。")
    for url in src["urls"]:
        html = fetcher.get(url)
        yield url, html_to_text(html, url), hint


# --------------------------------------------------------------------------
def feed_pages(src, fetcher):
    """WordPressのRSS。セミナー関連の記事を集め、まとめてAIに渡す。"""
    xml = fetcher.get(src["feed"])
    root = ET.fromstring(xml.encode("utf-8"))
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=src.get("max_age_days", 120))
    keyword = src.get("category_contains", "")
    items = []
    for it in root.iter("item"):
        cats = [(c.text or "") for c in it.findall("category")]
        if keyword and not any(keyword in c for c in cats):
            continue
        try:
            pub = email.utils.parsedate_to_datetime(it.findtext("pubDate") or "")
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=datetime.timezone.utc)
        except (TypeError, ValueError):
            continue
        if pub < cutoff:
            continue
        link = (it.findtext("link") or "").strip()
        body_html = it.findtext("content:encoded", namespaces=NS) or it.findtext("description") or ""
        items.append({"title": (it.findtext("title") or "").strip(), "link": link, "pub": pub, "html": body_html})
    items.sort(key=lambda x: x["pub"], reverse=True)
    items = items[: src.get("max_items", 40)]

    hint = ("WordPressの記事を「=====」で区切って並べたもの。記事の公開日は告知日で、開催日とは限らない。"
            "録画・オンデマンドで開催日が書かれていない記事は start_date を null にする。"
            "配信開始日が明記されていれば start_date にし、format を オンデマンド にする。")
    batch, size = [], 0
    for it in items:
        body = html_to_text(it["html"], it["link"] or src["feed"])
        # RSS bodies can be abstracts even when >300 characters.  When a
        # seminar's actual schedule is missing, fetch its public detail page
        # under the same robots.txt / rate-limit policy.  Never treat an
        # article's URL date or its publication date as a seminar date.
        has_schedule = re.search(
            r"(?:開催日時|開催日|開催期間|開催予定日|配信日時|配信期間|日時[：:]|日程[：:]).{0,120}"
            r"(?:20\d{2}|[1-9]|1[0-2])", body, re.S
        )
        if it["link"] and (len(body) < 300 or not has_schedule):
            try:
                detail_html = fetcher.get(it["link"])
                if not re.search(r"<rss\b|<feed\b", detail_html[:1500], re.I):
                    detailed = html_to_text(detail_html, it["link"])
                    if detailed.strip():
                        body = detailed[:16000]
            except Exception:  # noqa: BLE001 - fail closed, retain the feed text
                pass
        block = (f"=====\n記事タイトル: {it['title']}\n記事URL: <{it['link']}>\n"
                 f"公開日: {it['pub'].date().isoformat()}\n{body[:6000]}\n")
        if batch and size + len(block) > 20000:
            yield src["feed"], "\n".join(batch), hint
            batch, size = [], 0
        batch.append(block)
        size += len(block)
    if batch:
        yield src["feed"], "\n".join(batch), hint


# --------------------------------------------------------------------------
def jaha_top_pages(src, fetcher):
    """JAHA's dated upcoming list is more stable than calendar table markup."""
    url = src["start_url"]
    html = fetcher.get(url)
    hint = ("セミナーごとのリンク、開催開始日～終了日、対象者・受付状態の一覧。"
            "開催日を公開日や申し込み期限と混同しない。")
    yield url, html_to_text(html, url), hint


# --------------------------------------------------------------------------
def pages_for(src, fetcher, months):
    kind = src["kind"]
    if kind == "jaha_top":
        return jaha_top_pages(src, fetcher)
    if kind == "jaha_calendar":
        return jaha_pages(src, fetcher, months)
    if kind == "html_list":
        return list_pages(src, fetcher)
    if kind == "html_page":
        return single_pages(src, fetcher)
    if kind == "wp_feed":
        return feed_pages(src, fetcher)
    raise ValueError(f"未対応のkindです: {kind}")
