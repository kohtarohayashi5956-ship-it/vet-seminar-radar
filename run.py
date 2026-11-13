#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""セミナーレーダー（個人用・非公開）。

  python run.py --demo         画面の確認（サンプルデータ。通信しません）
  python run.py                巡回 → 無料ルール抽出（必要なら明示AI）→ index.html を生成
  python run.py --ai           無料抽出0件のページでAIを使う（キーと料金が必要）
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
from verified_corrections import apply_verified_corrections
from quality import summarize_quality, summarize_quality_by_source, summarize_review_candidates

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
    apply_verified_corrections(store)
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
    ap.add_argument("--ai", action="store_true", help="無料抽出0件のページだけClaude APIを使う（有料）")
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
        # Verified corrections can fill fields after the last network crawl.
        # Preserve the crawl timestamp but refresh all derived diagnostics
        # so public status and the regenerated HTML describe the same events.
        status = read_status()
        if status:
            status["total_events"] = len(events)
            status["data_quality"] = summarize_quality(events)
            status["quality_by_source"] = summarize_quality_by_source(events)
            status["review_diagnostics"] = summarize_review_candidates(events)
            if os.path.abspath(args.out) == os.path.abspath("index.html"):
                save_status(status)
        render.write_html(events, args.out, sources_summary=summarize(events), run_status=status)
        log(f"{len(events)}件から {args.out} を作り直しました。")
        if args.open:
            webbrowser.open("file://" + os.path.abspath(args.out))
        return 0

    # ---- 通常実行 ----
    from fetcher import Blocked, Disallowed, Fetcher
    from extract import Extractor
    from free_extract import extract_free
    from sources import pages_for
    from detail_enrich import enrich_lifetail
    from gakusai_enrich import enrich_gakusai
    from gakusai_handson import enrich_handson
    from jaha_enrich import enrich_jaha
    from society_enrich import enrich_jsvc
    from jsvas_enrich import enrich_jsvas
    from peppy_enrich import enrich_peppy
    from jbvp_enrich import enrich_jbvp

    client = None
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    # AI must remain opt-in; a secret alone never enables paid API calls.
    use_ai = args.ai or os.environ.get("SEMINAR_RADAR_USE_AI", "").strip().lower() in ("1", "true", "yes")
    if use_ai and key:
        from anthropic import Anthropic
        client = Anthropic(api_key=key)
    elif use_ai:
        log("注意: AIモードを指定しましたがANTHROPIC_API_KEYがありません。無料抽出のみ実行します。")
    else:
        log("モード: 無料ルール抽出（Claude APIは呼びません）")
    if not config.CONTACT:
        log("注意: 連絡先が未設定です（環境変数 SEMINAR_RADAR_CONTACT）。相手サイトに分かるよう設定を推奨します。")

    fetcher, extractor = Fetcher(), Extractor(client)
    store = merge.load_store()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    cache_dir = os.path.join("cache", today.isoformat())
    summary = []
    health = []
    warnings = []
    if use_ai and not key:
        warnings.append("AIモード指定ですがAPIキーがないため無料抽出のみです。")
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
                got = extract_free(src["name"], url, hint, text, today, stats)
                # AI is costly and strictly opt-in. It is only a fallback for
                # pages where source-specific free parsing found no seminars.
                if not got and client is not None:
                    got = extractor.extract(src["name"], url, hint, text, today, stats)
                    stats["ai_fallback_pages"] = stats.get("ai_fallback_pages", 0) + 1
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
        # Optional, bounded enrichment after the successful source listing.
        # A detail-page failure never removes or invalidates a valid card.
        if src["id"] == "peppy" and not note and fresh:
            fresh = enrich_peppy(fresh, fetcher, today, stats)
            log("  PEPPY詳細補完: " + str(stats.get("details_scanned", 0)) +
                "ページ / 時刻 " + str(stats.get("times_found", 0)) +
                "件 / 料金 " + str(stats.get("prices_found", 0)) +
                "件 / 締切 " + str(stats.get("deadlines_found", 0)) + "件")
        if src["id"] == "jaha" and not note and fresh:
            fresh = enrich_jaha(fresh, fetcher, today, stats)
            log("  JAHA個別ページ: " + str(stats.get("details_scanned", 0)) +
                "ページ / 締切確認 " + str(stats.get("deadlines_found", 0)) +
                "件 / 料金 " + str(stats.get("prices_found", 0)) +
                "件 / 詳細料金表示 " + str(stats.get("fee_label_pages", 0)) +
                "件 / 料金解析 " + str(stats.get("fee_parsed_pages", 0)) + "件")
        if src["id"] == "lifetail" and not note and fresh:
            fresh = enrich_lifetail(fresh, fetcher, today, stats)
            log("  詳細補完: " + str(stats.get("details_scanned", 0)) +
                "ページ / 締切 " + str(stats.get("deadlines_found", 0)) +
                "件 / 料金 " + str(stats.get("prices_found", 0)) + "件")
        elif src["id"] == "gakusai" and not note and fresh:
            fresh = enrich_gakusai(fresh, fetcher, today, stats)
            fresh = enrich_handson(fresh, fetcher, today, stats)
            log("  詳細補完: " + str(stats.get("details_scanned", 0)) +
                "ページ / 開催時刻 " + str(stats.get("times_found", 0)) +
                "件 / 料金 " + str(stats.get("prices_found", 0)) +
                "件 / 実習料金 " + str(stats.get("handson_fees_found", 0)) +
                "件 / 申込リンク " + str(stats.get("handson_applications_found", 0)) + "件")
        elif src["id"] == "jbvp" and not note and fresh:
            fresh = enrich_jbvp(fresh, fetcher, today, stats)
            log("  JBVP地区大会会場補完: " + str(stats.get("details_scanned", 0)) +
                "ページ / 会場 " + str(stats.get("venues_found", 0)) + "件")
        elif src["id"] == "jsvas" and not note and fresh:
            fresh = enrich_jsvas(fresh, fetcher, today, stats)
            log("  JSVAS講習会詳細: " + str(stats.get("details_scanned", 0)) +
                "ページ / 料金 " + str(stats.get("prices_found", 0)) +
                "件 / 申込締切 " + str(stats.get("deadlines_found", 0)) + "件")
        elif src["id"] == "jsvc" and not note and fresh:
            fresh = enrich_jsvc(fresh, fetcher, today, stats)
            log("  認定医講習科目補完: " + str(stats.get("certification_programs_found", 0)) + "件")
        if not note and pages and fresh:
            added, updated, replaced = merge.reconcile_source(store, fresh, src, today)
        else:
            added, updated = merge.update_store(store, fresh, src, None, today)
            replaced = 0
        if not note and pages and not fresh:
            note = "ページ取得成功・イベント抽出0件（構造または対象日を要確認）"
            warnings.append(src["name"] + ": " + note)
        extra = "".join(f" {k}={v}" for k, v in stats.items())
        summary.append((src["name"], pages, len(fresh), added, updated, note or ("OK" + extra)))
        health.append({"id": src["id"], "name": src["name"], "pages": pages,
                       "extracted": len(fresh), "added": added, "updated": updated,
                       "replaced_stale": replaced,
                       "details_scanned": stats.get("details_scanned", 0),
                       "details_accepted": stats.get("details_accepted", 0),
                       "deadlines_found": stats.get("deadlines_found", 0),
                       "prices_found": stats.get("prices_found", 0),
                       "handson_fees_found": stats.get("handson_fees_found", 0),
                       "handson_applications_found": stats.get("handson_applications_found", 0),
                       "handson_course_cards": stats.get("handson_course_cards", 0),
                       "handson_fetch_failed": stats.get("handson_fetch_failed", 0),
                       "fee_label_pages": stats.get("fee_label_pages", 0),
                       "fee_amount_pages": stats.get("fee_amount_pages", 0),
                       "fee_parsed_pages": stats.get("fee_parsed_pages", 0),
                       "fee_detail_checks": stats.get("fee_detail_checks", []),
                       "times_found": stats.get("times_found", 0),
                       "venues_found": stats.get("venues_found", 0),
                       "detail_fetch_failed": stats.get("detail_fetch_failed", 0),
                       "status": ("error" if note.startswith(("取得", "エラー")) else "empty") if note else ("empty" if not pages else "ok"),
                       "note": note[:250] if note else ("対象ページなし" if not pages else "")})
        if note:
            warnings.append(src["name"] + ": " + note[:120])

    dropped = merge.purge(store, today)
    corrected, correction_conflicts = apply_verified_corrections(store)
    if corrected:
        log("公式確認済み訂正を補完: " + ", ".join(corrected))
    if correction_conflicts:
        warnings.append("公式確認済み訂正と新規抽出値が不一致（上書きしません）: " +
                        ", ".join(correction_conflicts))
    merge.save_store(store, datetime.datetime.now(ZoneInfo("Asia/Tokyo")))
    manual = merge.load_manual(today)
    events = merge.dedupe_cross_source(list(store.values()) + manual)
    status = {
        "checked_at_jst": datetime.datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds"),
        "mode": "free_with_optional_ai" if client is not None else "free_rules",
        "total_events": len(events),
        "data_quality": summarize_quality(events),
        "quality_by_source": summarize_quality_by_source(events),
        "review_diagnostics": summarize_review_candidates(events),
        "source_results": health,
        "warnings": warnings,
    }
    save_status(status)
    render.write_html(events, args.out, sources_summary=summarize(events), run_status=status)

    log("\n===== 結果 =====")
    log(f"{'巡回先':<12}{'ページ':>6}{'抽出':>6}{'新規':>6}{'更新':>6}  状況")
    for name, pages, got, added, updated, st in summary:
        log(f"{name:<12}{pages:>6}{got:>6}{added:>6}{updated:>6}  {st}")
    log(f"AI呼び出し {extractor.calls}回 / AIキャッシュ利用 {extractor.cache_hits}回 / 古いデータの削除 {dropped}件")
    log(f"手動登録 {len(manual)}件 / 画面に出る合計 {len(events)}件 → {args.out}")
    if args.open:
        webbrowser.open("file://" + os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
