# -*- coding: utf-8 -*-
"""設定ファイル。ここだけ編集すれば、巡回先や期間を変えられます。"""
import os

# --- 連絡先（User-Agentに入ります）-----------------------------------------
# 相手サイトの管理者が「誰のアクセスか」分かるようにするためのものです。
# 個人のメールアドレスは必要ありません。標準では公開リポジトリを記載します。
# 希望する場合は環境変数 SEMINAR_RADAR_CONTACT で上書きできます。
DEFAULT_CONTACT = "https://github.com/kohtarohayashi5956-ship-it/vet-seminar-radar"
CONTACT = os.environ.get("SEMINAR_RADAR_CONTACT") or DEFAULT_CONTACT
USER_AGENT = (
    "SeminarRadarPersonal/1.0 "
    f"(personal non-commercial use; contact: {CONTACT or 'not-set'})"
)
ROBOTS_TOKEN = "SeminarRadarPersonal"   # robots.txt 判定に使う名前

# --- アクセスの作法 --------------------------------------------------------
REQUEST_INTERVAL_SEC = 3      # 1リクエストごとの待ち時間（同一実行内）
TIMEOUT_SEC = 30

# --- 取得する期間 ----------------------------------------------------------
MONTHS_AHEAD = 3              # 今月を含めて何か月分を見るか

# --- AI抽出 ----------------------------------------------------------------
MODEL = "claude-sonnet-4-6"   # コストを抑えたいときは Haiku 系のモデル名に変更
MAX_TEXT_CHARS = 60000        # 1回のAI呼び出しに渡す本文の上限（超えたら分割）
MAX_OUTPUT_TOKENS = 8000

# --- データの保持 ----------------------------------------------------------
KEEP_PAST_DAYS = 45           # 終了後、何日まで残すか
KEEP_UNDATED_DAYS = 30        # 日程不明のものを最後の確認から何日まで残すか

# --- 巡回先（Phase1）-------------------------------------------------------
# kind:
#   jaha_calendar : 月ごとの表。「次月」リンクをたどる
#   html_list     : 一覧ページ（ページ送りを最大 max_pages までたどる）
#   html_page     : 単一ページ
#   wp_feed       : WordPress の RSS。category_contains を含む記事だけ使う
SOURCES = [
    {
        "id": "jaha",
        "name": "JAHA",
        "kind": "jaha_top",
        "start_url": "https://www.jaha.or.jp/seminar-calendar/top/",
        "enabled": True,
    },
    {
        "id": "lifetail",
        "name": "Life&Tail",
        "kind": "html_list",
        "urls": ["https://life-tail.com/seminars/?status=open"],
        "max_pages": 3,
        "enabled": True,
    },
    {
        "id": "gakusai",
        "name": "学際企画",
        "kind": "html_page",
        "urls": ["https://www.gakusai.co.jp/doubutu/seminar-comingup/"],
        "enabled": True,
    },
    {
        "id": "peppy",
        "name": "PEPPY",
        "kind": "peppy_list",
        "start_url": "https://www.peppy.jp/seminar",
        "enabled": False,
    },
    {
        "id": "eduone",
        "name": "EDUWARD Press",
        "kind": "eduone_lecture",
        "start_url": "https://eduone.jp/lecture/",
        "max_details": 12,
        "enabled": False,
    },
    {
        "id": "academy",
        "name": "VETS ACADEMY",
        "kind": "vets_academy_list",
        "start_url": "https://academy.eduone.jp/seminar",
        "enabled": False,
    },
    {
        "id": "jbvp",
        "name": "JBVP",
        "kind": "jbvp_meetings",
        "urls": ["https://www.jbvp.org/vn/", "https://www.jbvp.org/forum/"],
        "enabled": True,
    },
    {
        "id": "javnu",
        "name": "JAVNU",
        "kind": "society_meeting",
        "urls": ["https://www.javnu.jp/"],
        "enabled": True,
    },
    {
        "id": "javnu_cert",
        "name": "JAVNU認定講習会",
        "kind": "html_page",
        "urls": ["https://www.javnu.jp/certification/schedule/"],
        "enabled": True,
    },

    {
        "id": "jsvd",
        "name": "日本獣医皮膚科学会",
        "kind": "society_meeting",
        "urls": ["https://www.jsvd.jp/"],
        "enabled": True,
    },
    {
        "id": "jsvd_cert",
        "name": "JSVD認定医講習",
        "kind": "html_page",
        "urls": ["https://www.jsvd.jp/certifiedphysicians/certifiedphysician.html"],
        "enabled": True,
    },

    {
        "id": "jvcs",
        "name": "日本獣医がん学会",
        "kind": "society_meeting",
        "urls": ["https://www.jvcs.jp/society/"],
        "enabled": True,
    },
    {
        "id": "jsvc",
        "name": "日本獣医循環器学会",
        "kind": "society_meeting",
        "urls": ["https://www.jsvc.jp/meeting/regular/conf125/"],
        "enabled": True,
    },
    {
        "id": "jsvas",
        "name": "日本獣医麻酔外科学会",
        "kind": "html_page",
        # Public official lecture listing and conference detail, no bulk mirrors.
        "urls": [
            "https://www.jsvas.net/lectures/index.php",
            "https://www.jsvas.net/conference/2026-113.php",
        ],
        "enabled": True,
    },
    {
        "id": "jcvim",
        "name": "JCVIM",
        "kind": "html_page",
        "urls": ["https://www.jcvim.org/index.html"],
        "enabled": True,
    },
    {
        "id": "jvna",
        "name": "日本愛玩動物看護師会",
        "kind": "html_page",
        # Official programme. Avoid conflating abstract and attendee deadlines.
        "urls": ["https://www.jvna.or.jp/16thkangotaikai/"],
        "enabled": True,
    },
    {
        "id": "dourinken",
        "name": "動物臨床医学会",
        "kind": "html_page",
        "urls": ["https://dourinken.com/taikai/guide/"],
        "enabled": True,
    },
    {
        "id": "vetstech",
        "name": "VETS TECH",
        "kind": "wp_feed",
        "feed": "https://vets-tech.jp/feed/",
        "category_contains": "セミナー",
        "max_items": 40,
        "max_age_days": 120,
        "enabled": True,
    },
]
