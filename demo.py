# -*- coding: utf-8 -*-
"""画面の確認用サンプル。題名はすべて架空で、実在のセミナーではありません。"""
import datetime


def sample_events(today):
    d = lambda n: (today + datetime.timedelta(days=n)).isoformat()  # noqa: E731
    base = dict(venue=None, prefecture=None, audience=[], topics=[], price=None, is_free=None,
                status=None, deadline=None, organizer=None, end_date=None, start_time=None,
                end_time=None, format=None, url="https://example.com/", url_is_page=False,
                verified=True, also_listed=[], source="サンプル", source_id="demo",
                first_seen=today.isoformat(), last_seen=today.isoformat())
    rows = [
        dict(title="【サンプル】内分泌疾患アップデート 2日間集中講義", start_date=d(3), end_date=d(5),
             format="現地", venue="サンプル会議センター", prefecture="東京都",
             audience=["獣医師"], topics=["内分泌", "内科"], price="会員 50,000円／一般 60,000円",
             status="受付中", deadline=d(1), organizer="サンプル協会", also_listed=["サンプル配信社"]),
        dict(title="【サンプル】麻酔中のトラブル対応 第2回（短頭種）", start_date=d(4), start_time="20:00",
             end_time="21:30", format="ライブ配信", audience=["獣医師", "動物看護師"], topics=["麻酔・救急"],
             price="3,500円", status="締切まであと3日", deadline=d(2), organizer="サンプル配信社"),
        dict(title="【サンプル】動物看護師のための採血・留置の基本", start_date=d(6), start_time="10:30",
             end_time="12:00", format="現地", venue="サンプル動物看護専門学校", prefecture="神奈川県",
             audience=["動物看護師"], topics=["看護・技術"], price="8,800円", status="受付中",
             organizer="サンプル看護師会"),
        dict(title="【サンプル】無料ウェビナー 成犬のストレスサインと病院でできる支援", start_date=d(9),
             start_time="20:00", end_time="21:30", format="ライブ配信",
             audience=["獣医師", "動物看護師", "動物病院スタッフ"], topics=["行動・しつけ"], is_free=True,
             status="受付中", organizer="サンプル配信社"),
        dict(title="【サンプル】腹部エコー実習（定員20名）", start_date=d(11), start_time="10:00",
             end_time="17:00", format="現地", venue="サンプル研修施設", prefecture="大阪府",
             audience=["獣医師"], topics=["画像診断"], price="45,000円", status="満席",
             organizer="サンプル学際社"),
        dict(title="【サンプル】循環器学会 定例大会", start_date=d(14), end_date=d(15), format="ハイブリッド",
             venue="サンプルホール", prefecture="東京都", audience=["獣医師"], topics=["循環器", "学会・大会"],
             price="会員 8,000円", status=None, organizer="サンプル循環器学会", verified=False),
        dict(title="【サンプル】犬のしつけ方講座（飼い主向け）", start_date=d(7), start_time="14:00",
             format="現地", venue="サンプルドッグラン", prefecture="千葉県", audience=["一般"],
             price="3,000円", status="受付中", organizer="サンプル協会"),
        dict(title="【サンプル】シニアケア講座 第1回", start_date=d(20), start_time="20:00", end_time="21:30",
             format="ライブ配信", audience=["獣医師", "動物看護師"], topics=["看護・技術", "内科"],
             price="会員 4,000円／一般 5,500円", status="受付中", deadline=d(18), organizer="サンプル協会"),
        dict(title="【サンプル】軟部外科ウェットラボ（2会場）", start_date=d(26), end_date=d(27), format="現地",
             venue="サンプル大学", prefecture="宮崎県", audience=["獣医師"], topics=["外科"],
             price="95,000円", status="受付終了", organizer="サンプル学際社"),
        dict(title="【サンプル】録画配信 猫の血尿 症例から学ぶ", start_date=d(2), format="オンデマンド",
             audience=["獣医師"], topics=["泌尿器", "猫"], is_free=True, status="配信中", organizer="サンプル配信社"),
        dict(title="【サンプル】開催日が未掲載の講習会", start_date=None, format=None, audience=["獣医師"],
             topics=["その他"], organizer="サンプル協会", verified=False),
        dict(title="【サンプル】終了済みの講習会", start_date=d(-1), start_time="19:00", end_time="21:00",
             format="ライブ配信", audience=["動物看護師"], topics=["看護・技術"], price="2,000円",
             status="受付終了", organizer="サンプル配信社"),
    ]
    out = []
    for i, r in enumerate(rows):
        e = dict(base); e.update(r); e["id"] = f"demo{i:02d}"
        out.append(e)
    return out
