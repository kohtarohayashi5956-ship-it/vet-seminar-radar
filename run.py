#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""セミナーレーダー（個人用・非公開）。

  python run.py --demo         画面の確認（サンプルデータ。通信しません）
  python run.py                巡回 → AIで抽出 → index.html を生成
  python run.py --offline      通信せず、蓄積済みのデータから index.html を作り直す
  python run.py --only jaha,vetstech   指定した巡回先だけ
  python run.py --months 2     何か月分（JAHAのカレンダー）を見るか
  python run.py --debug        取得した本文を cache/ に保存（うまく抽出できないときの調査用）
  python run.py --open         終わったら index.html をブラウザで開く
"""
import argparse
import datetime
import os
import json
from zoneinfo import ZoneInfo
import sys
import webbrowser

import config
import demo
import merge
import render

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def log(msg=""):
    print(msg, flush=True)


STATUS_PATH = os.path.join("data", "run_status.json")


def read_status():
    try:
        with open(STATUS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_status(status):
    os.makedirs("data", exist_ok=True)
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def local_today():
    return datetime.datetime.now(ZoneInfo("Asia/Tokyo")).date()


def build_events(today):

    store = merge.load_store()
    manual = merge.load_manual(today)
    events = merge.dedupe_cross_source(list(store.values()) + manual)
    return store, events


def summarize(events):
    counts = {}
    for e in events:
        counts[e.get("source", "?")] = counts.get(e.get("source", "?"), 0) + 1
    return " / ".join(f"{k} {v}件" for k, v in sorted(counts.items()))


def main(argv):
    ap = argparse.ArgumentParser(description="セミナーレーダー（個人用）")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--months", type=int, default=config.MONTHS_AHEAD)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--out", default="index.html")
    args = ap.parse_args(argv)
    today = local_today()

    if args.demo:
        render.write_html(demo.sample_events(today), args.out, demo=True)
        log(f"サンプル画面を {args.out} に作りました。")
        if args.open:
            webbrowser.open("file://" + os.path.abspath(args.out))
        return 0

    if args.offline:
        store, events = build_events(today)
        render.write_html(events, args.out, sources_summary=summarize(events), run_status=read_status())
        log(f"{len(events)}件から {args.out} を作り直しました。")
        if args.open:
            webbrowser.open("file://" + os.path.abspath(args.out))
        return 0

    # ---- 通常実行 ----
    from fetcher import Blocked, Disallowed, Fetcher
    from extract import Extractor
    from sources import pages_for

    client = None
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        from anthropic import Anthropic
        client = Anthropic(api_key=key)
    else:
        log("注意: ANTHROPIC_API_KEY が未設定です。前回までに解析済みのページ以外は読み取れません。")
    if not config.CONTACT:
        log("注意: 連絡先が未設定です（環境変数 SEMINAR_RADAR_CONTACT）。相手サイトに分かるよう設定を推奨します。")

    fetcher, extractor = Fetcher(), Extractor(client)
    store = merge.load_store()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    cache_dir = os.path.join("cache", today.isoformat())
    summary = []
    health = []
    warnings = []
    if not key:
        warnings.append("ANTHROPIC_API_KEY が未設定です。未解析ページからの自動抽出は行われません。")
    if not config.CONTACT:
        warnings.append("SEMINAR_RADAR_CONTACT が未設定です。")

    for src in config.SOURCES:
        if not src.get("enabled", True) or (only and src["id"] not in only):
            continue
        log(f"\n== {src['name']} ==")
        stats, fresh, pages, note = {}, [], 0, ""
        try:
            for n, (url, text, hint) in enumerate(pages_for(src, fetcher, args.months), start=1):
                pages += 1
                log(f"  [{n}] {url}  (本文 {len(text):,}字)")
                if args.debug:
                    os.makedirs(cache_dir, exist_ok=True)
                    with open(os.path.join(cache_dir, f"{src['id']}-{n}.txt"), "w", encoding="utf-8") as f:
                        f.write(text)
                got = extractor.extract(src["name"], url, hint, text, today, stats)
                log(f"      → {len(got)}件を抽出")
                fresh.extend(got)
        except Disallowed as ex:
            note = f"取得しませんでした（robots.txt）: {ex}"
        except Blocked as ex:
            note = f"取得できませんでした（サイト側が拒否。回避はしません）: {ex}"
        except Exception as ex:  # noqa: BLE001
            note = f"エラー: {ex}"
        if note:
            log(f"  ! {note}")
        added, updated = merge.update_store(store, fresh, src, None, today)
        extra = "".join(f" {k}={v}" for k, v in stats.items())
        summary.append((src["name"], pages, len(fresh), added, updated, note or ("OK" + extra)))
        health.append({"id": src["id"], "name": src["name"], "pages": pages,
                       "extracted": len(fresh), "added": added, "updated": updated,
                       "status": "error" if note else ("empty" if not pages else "ok"),
                       "note": note[:250] if note else ("対象ページなし" if not pages else "")})
        if note:
            warnings.append(src["name"] + ": " + note[:120])

    dropped = merge.purge(store, today)
    merge.save_store(store, datetime.datetime.now(ZoneInfo("Asia/Tokyo")))
    manual = merge.load_manual(today)
    events = merge.dedupe_cross_source(list(store.values()) + manual)
    status = {
        "checked_at_jst": datetime.datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds"),
        "mode": "AI" if key else "cached_only",
        "total_events": len(events),
        "source_results": health,
        "warnings": warnings,
    }
    save_status(status)
    render.write_html(events, args.out, sources_summary=summarize(events), run_status=status)

    log("\n===== 結果 =====")
    log(f"{'巡回先':<12}{'ページ':>6}{'抽出':>6}{'新規':>6}{'更新':>6}  状況")
    for name, pages, got, added, updated, st in summary:
        log(f"{name:<12}{pages:>6}{got:>6}{added:>6}{updated:>6}  {st}")
    log(f"AI呼び出し {extractor.calls}回 / キャッシュ利用 {extractor.cache_hits}回 / 古いデータの削除 {dropped}件")
    log(f"手動登録 {len(manual)}件 / 画面に出る合計 {len(events)}件 → {args.out}")
    if args.open:
        webbrowser.open("file://" + os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
