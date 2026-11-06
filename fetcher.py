# -*- coding: utf-8 -*-
"""作法を守るHTTP取得。robots.txtに従い、間隔を空け、ブロックされたら回避せずに止まる。"""
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

import config


class Disallowed(Exception):
    """robots.txt で取得が許可されていない。"""


class Blocked(Exception):
    """サイト側が自動アクセスを拒否している（回避はしない）。"""


class Fetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept-Language": "ja,en;q=0.5",
        })
        self._last = 0.0
        self._robots = {}   # host -> RobotFileParser | "deny"

    # ---- robots.txt --------------------------------------------------
    def _robots_for(self, url):
        p = urlparse(url)
        host = f"{p.scheme}://{p.netloc}"
        if host in self._robots:
            return self._robots[host]
        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"{host}/robots.txt"
        try:
            self._wait()
            r = self.session.get(robots_url, timeout=config.TIMEOUT_SEC)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
                result = rp
            elif r.status_code in (401, 403):
                result = "deny"          # 取得を拒否されている → 保守的に不許可
            elif 400 <= r.status_code < 500:
                rp.parse([])             # robots.txt なし → 制限なし
                result = rp
            else:
                result = "deny"          # 5xx など → 保守的に不許可
        except requests.RequestException:
            result = "deny"
        self._robots[host] = result
        return result

    def allowed(self, url):
        rp = self._robots_for(url)
        if rp == "deny":
            return False
        return rp.can_fetch(config.ROBOTS_TOKEN, url)

    # ---- 取得 ---------------------------------------------------------
    def _wait(self):
        gap = time.time() - self._last
        if gap < config.REQUEST_INTERVAL_SEC:
            time.sleep(config.REQUEST_INTERVAL_SEC - gap)
        self._last = time.time()

    def get(self, url):
        if not self.allowed(url):
            raise Disallowed(f"robots.txt で許可されていません: {url}")
        self._wait()
        try:
            r = self.session.get(url, timeout=config.TIMEOUT_SEC)
        except requests.RequestException as ex:
            raise RuntimeError(f"接続に失敗しました: {url} ({ex})") from ex
        if r.status_code in (401, 403, 429, 503):
            raise Blocked(f"サイトが自動アクセスを受け付けませんでした(HTTP {r.status_code}): {url}")
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}: {url}")
        if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii"):
            r.encoding = r.apparent_encoding
        text = r.text
        low = text[:3000].lower()
        if len(text) < 1500 and any(k in low for k in ("captcha", "bot detection", "access denied", "unusual traffic")):
            raise Blocked(f"ボット検知のページが返りました: {url}")
        return text
