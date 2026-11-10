# -*- coding: utf-8 -*-
"""Official-source, deterministic seminar extraction without an AI API.

Only dates belonging to an event's own card/row or an explicitly labelled
schedule in its own announcement may be assigned. Unclear dates stay None.
"""
import datetime
import re
import unicodedata
from urllib.parse import urlparse

from extract import AUDIENCES, TOPICS, norm, validate

MONTH_DAY = re.compile(r"(?<!\d)(1[0-2]|0?[1-9])\s*月\s*(3[01]|[12]\d|0?[1-9])\s*日")
YMD = re.compile(r"(?<![\d/])(20\d{2})\s*[年./-]\s*(1[0-2]|0?[1-9])\s*[月./-]\s*(3[01]|[12]\d|0?[1-9])\s*日?")
CALENDAR_DAY = re.compile(r"^\s*(1[0-2]|0?[1-9])\s*/\s*(3[01]|[12]\d|0?[1-9])(?:\s*(?:[月火水木金土日曜祝（）().・]+|\s))?\s*$")
CALENDAR_PREFIX = re.compile(r"^\s*(1[0-2]|0?[1-9])\s*/\s*(3[01]|[12]\d|0?[1-9])(?=\D|$)")
LINK = re.compile(r"^\s*(.*?)\s*<(https?://[^>\s]+)>\s*$")
YEAR = re.compile(r"(20\d{2})\s*年|(?:^|\s)(20\d{2})\s+セミナー")
STATUS = re.compile(r"受付終了|申込終了|募集終了|受付中|申込受付中|募集受付中|満席|キャンセル待ち|残り\d+席")
PREFS = "北海道 青森 岩手 宮城 秋田 山形 福島 茨城 栃木 群馬 埼玉 千葉 東京 神奈川 新潟 富山 石川 福井 山梨 長野 岐阜 静岡 愛知 三重 滋賀 京都 大阪 兵庫 奈良 和歌山 鳥取 島根 岡山 広島 山口 徳島 香川 愛媛 高知 福岡 佐賀 長崎 熊本 大分 宮崎 鹿児島 沖縄".split()
TOPIC_HINTS = {
 "内科": ["内科", "総合診療"], "外科": ["外科", "手術", "縫合", "整形", "骨切り", "膝蓋骨", "腹腔鏡", "内視鏡実習"],
 "麻酔・救急": ["麻酔", "救急", "疼痛", "集中治療"], "画像診断": ["画像", "超音波", "エコー", "CT", "MRI"],
 "腫瘍": ["腫瘍", "リンパ腫", "癌", "がん"], "循環器": ["循環", "心臓", "心エコー", "心筋", "MMVD", "心不全"],
 "皮膚・耳": ["皮膚", "耳科", "外耳", "膿皮症"], "眼科": ["眼科", "角膜", "白内障"],
 "歯科": ["歯科", "歯周", "抜歯"], "神経": ["神経", "てんかん"],
 "内分泌": ["内分泌", "副腎", "甲状腺", "糖尿病"], "消化器": ["消化器", "消化管", "腸症", "胆嚢", "膵炎"],
 "泌尿器": ["泌尿", "腎臓", "尿道", "膀胱"], "栄養": ["栄養", "食事療法", "肥満"],
 "看護・技術": ["看護", "保定", "採血"], "院内教育・経営": ["新人教育", "病院経営", "接遇"],
 "猫": ["猫", "feline"], "行動・しつけ": ["しつけ", "行動", "ストレスサイン"],
}
TIME_RANGE = re.compile(r"(?<!\d)([01]?\d|2[0-3])[：:]([0-5]\d)\s*[〜~～－―–-]\s*([01]?\d|2[0-3])[：:]([0-5]\d)")
# Explicit time markers in VETS TECH articles.  Exclude deadlines, post dates and references.
EVENT_LABEL = re.compile(r"(?:開催日時|開催日|開催予定日|開催期間|開催時間|配信日時|配信開始日時|配信期間|日時[：:\s]|日程[：:\s]|[■●◆] ?日時)")
EXCLUDE_DATE = re.compile(r"公開日|投稿日|掲載日|更新日|申込締切|応募締切|受付締切|お申込み期限|お申し込み期限|早割|発行日|記事公開|応募期間|受付期間|申し込み期間|申込期間")


def _date(y, m, d):
    try: return datetime.date(int(y), int(m), int(d)).isoformat()
    except (ValueError, TypeError): return None


def _dates(text):
    """Full-year date literals from visible text only (not URLs)."""
    cleaned = re.sub(r"<https?://[^>]+>|https?://\S+", " ", text)
    return [d for m in YMD.finditer(cleaned) if (d := _date(*m.groups()))]


def _year(text):
    m = YEAR.search(text)
    return int(m.group(1) or m.group(2)) if m else None


def _named_date(text, year=None):
    full = _dates(text)
    if full: return full[0]
    m = MONTH_DAY.search(text)
    return _date(year, *m.groups()) if m and year else None


def _topics(title):
    s=unicodedata.normalize("NFKC",title).lower()
    out=[k for k,terms in TOPIC_HINTS.items() if k in TOPICS and any(w.lower() in s for w in terms)]
    return out[:2]


def _audience(context):
    items=[]
    if "獣医師" in context: items.append("獣医師")
    if "動物看護師" in context or "愛玩動物看護師" in context or "看護師向け" in context: items.append("動物看護師")
    if "トリマー" in context: items.append("トリマー")
    if "獣医学生" in context or "獣医学部生" in context: items.append("学生")
    if re.search(r"一般[・･、\s]*すべて|対象[：:]\s*一般|飼い主向け", context): items.append("一般")
    if "動物病院関係者" in context or "動物病院スタッフ" in context: items.append("動物病院スタッフ")
    return [a for a in items if a in AUDIENCES]


def _fmt(context):
    if re.search(r"ハイブリッド|現地.{0,12}(配信|オンライン)|オンライン.{0,12}現地",context,re.I): return "ハイブリッド"
    if re.search(r"オンデマンド|アーカイブ|録画配信|ウェブ受講|配信期間",context,re.I): return "オンデマンド"
    if re.search(r"オンライン|ライブ配信|無料ライブ|ウェビナー|zoom|webinar|(?:^|\s)ライブ(?:\s|$)",context,re.I): return "ライブ配信"
    if re.search(r"実習|会場|現地|博多開催|大宮開催|東京開催|大阪開催",context): return "現地"
    return None


def _pref(context,fmt):
    if fmt in ("ライブ配信","オンデマンド"): return None
    for p in PREFS:
        suffix = "" if p=="北海道" else "都" if p=="東京" else "府" if p in ("大阪","京都") else "県"
        if p+suffix in context: return p+suffix
    for p in ("東京","大阪","京都","神奈川","愛知","福岡","宮崎","埼玉"):
        if p in context: return p+("都" if p=="東京" else "府" if p in ("大阪","京都") else "県")
    if "博多" in context: return "福岡県"
    if "大宮" in context: return "埼玉県"
    return None


def _times(context):
    m = TIME_RANGE.search(context)
    return (f"{int(m.group(1)):02d}:{m.group(2)}",f"{int(m.group(3)):02d}:{m.group(4)}") if m else (None,None)


def _price(context):
    """Require an unambiguous free admission statement, not a free member tier."""
    for line in context.splitlines():
        if re.search(r"(?:参加費|受講料|料金|受講費)[：:\s]", line) and len(line) < 130:
            value = line.strip()
            # Paid tiers take precedence over any free tier on the same line.
            if re.search(r"[0-9０-９,，]+\s*円", value):
                return value[:110], None
            if re.search(r"(?:[：:\s]|^)無料(?:$|\s|[（(])", value) and not re.search(r"無料会員", value):
                return value[:110], True
            return value[:110], None
    if re.search(r"(?:^|\n)\s*無料(?:\s|$)|無料ライブ|無料配信", context):
        return "無料", True
    return None, None


def _speakers_in_title(title):
    """Only explicitly written names followed by 先生 in this event's title."""
    matches = re.findall(
        r"(?:(?<=先生)|(?<![一-龥々ぁ-ゖァ-ヺー]))"
        r"([一-龥々ぁ-ゖァ-ヺー]{1,6}[ 　]+[一-龥々ぁ-ゖァ-ヺー]{1,6}"
        r"|[一-龥々ぁ-ゖァ-ヺー]{2,8})\s*先生(?!方)",
        title,
    )
    names = []
    for name in matches:
        clean = " ".join(name.split())
        if clean not in names:
            names.append(clean)
    return "・".join(names[:3]) if names else None


def _explicit_deadline(body, event_date=None):
    """Use a labelled calendar date, or explicit 当日 tied to this event date."""
    # Some RSS articles put signup details after a long introduction.
    # Restrict evidence to this article and the same 5,500-character
    # window used for its other descriptive fields.
    lines = [line.strip() for line in body[:5500].splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if not re.match(r"^(?:申込締切|お申込み締切|申し込み締切|受付締切|申込期限|応募締切)[：:\s]?",line):
            continue
        # Do not mistake the next field (e.g. 開催日時) for a deadline.
        local = line
        if not _dates(line) and i + 1 < len(lines) and re.match(
            r"^20\d{2}\s*[年./-]\s*\d{1,2}\s*[月./-]\s*\d{1,2}",
            lines[i + 1],
        ):
            local += " " + lines[i + 1]
        dates = _dates(local)
        if dates:
            return dates[0]
        # 当日 is meaningful only next to a labelled registration deadline,
        # and only if this specific event already has a verified start date.
        if re.match(r"^(?:申込締切|お申込み締切|申し込み締切|受付締切|申込期限|応募締切)[：:\s]*当日(?:\s|[0-9０-９]|$)", line):
            if event_date and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", event_date):
                try:
                    datetime.date.fromisoformat(event_date)
                except ValueError:
                    continue
                return event_date
    return None


def _event(title,when,url,page,context="",organizer=None,end=None):
    fmt=_fmt(context+" "+title)
    t1,t2=_times(context)
    price,free=_price(context)
    m=STATUS.search(context)
    return {"title":title.strip(), "start_date":when, "end_date":end, "start_time":t1,"end_time":t2,
        "format":fmt,"venue":None,"prefecture":_pref(context+" "+title,fmt),
        "audience":_audience(context+" "+title),"topics":_topics(title),
        "price":price,"is_free":free,"status":m.group(0) if m else None,
        "deadline":None,"abstract_deadline":None,"detail_url":None,
        "certification_note":None,"certification_url":None,
        "certification_program":None,
        "speaker":_speakers_in_title(title),"organizer":organizer,"url":url or page,"evidence":title.strip()}


def _line_link(line):
    m=LINK.match(line)
    return (m.group(1).strip(),m.group(2).strip()) if m else None


def _jaha(text,page,today,stats):
    m=re.search(r"(20\d{2})\s*年\s*(1[0-2]|[1-9])\s*月",text)
    if not m:
        stats["missing_calendar_heading"]=stats.get("missing_calendar_heading",0)+1
        return []
    year,month=map(int,m.groups())
    lines=text.splitlines()
    marks=[(i,match) for i,line in enumerate(lines) if (match:=CALENDAR_PREFIX.match(line)) and int(match.group(1))==month]
    stats["calendar_days"]=len(marks)
    out=[]
    for n,(i,match) in enumerate(marks):
        when=_date(year,month,match.group(2))
        if not when: continue
        block=lines[i+1:marks[n+1][0] if n+1<len(marks) else len(lines)]
        links=[]
        for j,line in enumerate(block):
            item=_line_link(line)
            if not item: continue
            title,url=item
            if len(title)<6 or re.fullmatch(r"詳細|MAP|前月|次月|申込|お申し込み|ホーム",title,re.I) or "/seminar-calendar" in url: continue
            # The date is attached to this calendar row. Avoid other seminars'
            # details by ending context at the next substantive event link.
            links.append((j,title,url))
        for k,(j,title,url) in enumerate(links):
            previous=links[k-1][0] if k else -1
            following=links[k+1][0] if k+1<len(links) else len(block)
            local="\n".join(block[max(previous+1,j-4):min(following,j+5)])
            e=_event(title,when,url,page,local,"JAHA")
            after=[x.strip() for x in block[j+1:min(following,j+6)] if x.strip()]
            for ln in after:
                if ln.startswith("詳細") or "<https?://" in ln or ln in ("受付終了","受付中"):continue
                if re.fullmatch(r".{2,3}[都府県]|北海道",ln):continue
                if len(ln)>=4 and ln not in ("金","土","日","月","火","水","木"):
                    e["venue"]=ln[:110];break
            out.append(e)
    # Coalesce consecutive days only for exactly the same title and URL.
    grouped={}
    for e in out:grouped.setdefault((norm(e["title"]),e["url"]),[]).append(e)
    result=[]
    for group in grouped.values():
        last=None
        for ev in sorted(group,key=lambda x:x["start_date"]):
            if last and datetime.date.fromisoformat(ev["start_date"])<=datetime.date.fromisoformat(last["end_date"] or last["start_date"])+datetime.timedelta(days=1):
                last["end_date"]=max(ev["start_date"],last["end_date"] or last["start_date"])
            else:
                last=dict(ev);result.append(last)
    return result


JAHA_DATE_RANGE = re.compile(
    r"(?<!\d)(20\d{2})[-./](1[0-2]|0?[1-9])[-./](3[01]|[12]\d|0?[1-9])"
    r"\s*[～〜~–ー－-]\s*"
    r"(20\d{2})[-./](1[0-2]|0?[1-9])[-./](3[01]|[12]\d|0?[1-9])"
)


def _jaha_top(text, page, today, stats):
    """Extract own dated cards from the official JAHA upcoming listing.

    Each card is a status, a linked seminar title, an ISO date range,
    prefecture and audience. Never borrow a date from an adjacent card.
    """
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    out = []
    for i, line in enumerate(lines):
        if not re.search(r"20\d{2}[-./]\d{1,2}[-./]\d{1,2}", line):
            continue
        # Some JAHA date ranges include whitespace or a line break.
        group = " ".join(lines[i:i + 3])
        m = JAHA_DATE_RANGE.search(group)
        if not m:
            continue
        start = _date(*m.groups()[:3])
        end = _date(*m.groups()[3:])
        if not start or not end or end < start:
            continue
        link = None
        link_idx = None
        for j in range(i - 1, max(-1, i - 9), -1):
            candidate = _line_link(lines[j])
            if candidate and len(candidate[0]) >= 6 and not re.fullmatch(
                r"画像|詳細|MAP|前月|次月|ホーム", candidate[0], re.I
            ):
                link, link_idx = candidate, j
                break
        if not link:
            continue
        title, url = link
        # The audience is the explicit label immediately after the date;
        # content before the title can belong to the previous card.
        target = next((ln for ln in lines[i + 1:i + 3]
                       if re.match(r"^対象\s*[：:]", ln)), "")
        context = title + "\n" + line + "\n" + target
        e = _event(title, start, url, page, context, "JAHA", end=end if end != start else None)
        # Audience must come only from the explicit 対象 field, never the title.
        e["audience"] = _audience(target)
        for ln in lines[max(0,link_idx - 2):link_idx]:
            if ln in ("受付中", "受付終了", "予告", "満席"):
                e["status"] = ln
        out.append(e)
    stats["jaha_date_ranges"] = len(out)
    return out


def _gakusai(text,page,today):
    year=_year(text)
    if not year:return []
    lines=text.splitlines()
    heads=[i for i,ln in enumerate(lines) if re.match(r"^(?:No\.\s*\d+|MS\s*\d+)\b",unicodedata.normalize("NFKC",ln))]
    out=[]
    for n,i in enumerate(heads):
        seg=lines[i:heads[n+1] if n+1<len(heads) else min(i+18,len(lines))]
        title=re.sub(r"^(?:No\.\s*\d+|MS\s*\d+)\s*","",seg[0])
        title=re.sub(r"<https?://[^>]+>|[»>]\s*詳細はこちら.*","",title).strip()
        if len(title)<6:continue
        # Detail links may appear inline on the No./MS heading or on a
        # separate line. Only URLs actually shown in THIS card are eligible.
        # An unlinked "詳細はこちら" is not evidence of a published detail page.
        detail = None
        for candidate in seg:
            m = re.search(r"(?:»|›|>)\s*詳細はこちら\s*<(https?://[^>\s]+)>", candidate)
            if not m:
                continue
            u = urlparse(m.group(1))
            if (u.scheme == "https"
                    and u.hostname in ("www.gakusai.co.jp", "gakusai.co.jp")
                    and re.fullmatch(r"/vet/vet-seminar/\d+/?", u.path)):
                detail = m.group(1)
                break
        date_line=next((s for s in seg[1:8] if MONTH_DAY.search(s) and not s.startswith("No.")),"")
        if not date_line:continue
        for section in re.split(r"[｜|]",date_line):
            if "ウェブ受講" in section or "オンデマンド" in section:continue
            m=MONTH_DAY.search(section)
            if not m:continue
            sd=_date(year,*m.groups())
            if sd:out.append(_event(title,sd,detail,page,section,"学際企画"))
    return out


def _feed_event_schedule(body, published=None):
    """Only dates under this announcement's own schedule heading.

    The article posting date is used ONLY to resolve the year of an
    explicitly labelled month/day. It is never itself an event date.
    """
    lines = [re.sub(r"<https?://[^>]*>|https?://\S+", "", ln).strip()
             for ln in body.splitlines()]
    for i, line in enumerate(lines):
        if EXCLUDE_DATE.search(line):
            continue
        is_heading = bool(EVENT_LABEL.search(line) or
                          re.fullmatch(r"(?:日時|開催日|開催日時|開催期間|日程|配信日時)\s*[：:]?", line))
        if not is_heading:
            continue
        # Use at most two following lines, stopping before a new field such
        # as '申込締切'. This prevents a deadline from becoming a start date.
        context = [line]
        for following in lines[i + 1:i + 3]:
            if EXCLUDE_DATE.search(following):
                break
            context.append(following)
        local = " ".join(context)
        dates = _dates(local)
        if dates:
            return dates[0]
        monthday = MONTH_DAY.search(local)
        if monthday and published:
            try:
                postdate = datetime.date.fromisoformat(published)
                y, m, d = postdate.year, int(monthday.group(1)), int(monthday.group(2))
                inferred = datetime.date(y, m, d)
                if inferred < postdate - datetime.timedelta(days=3):
                    inferred = datetime.date(y + 1, m, d)
                if 0 <= (inferred - postdate).days <= 370:
                    return inferred.isoformat()
            except ValueError:
                pass
    # Unlabelled full-year dates are accepted only if event is explicit
    # on that SAME line. Ignore article URLs, publication and deadlines.
    for line in lines:
        if EXCLUDE_DATE.search(line):
            continue
        if re.search(r"ライブ配信|オンライン開催|開催\s*[:：]|セミナー開始", line):
            dates = _dates(line)
            if dates:
                return dates[0]
    return None



def _feed_schedule_times(body, event_date):
    """Return times only from a schedule field matching this event's date.

    Single times, and explicit ranges, are supported. A date range or several
    independent sessions are ambiguous and must not be merged.
    """
    if not event_date:
        return None, None
    try:
        target = datetime.date.fromisoformat(event_date)
    except (TypeError, ValueError):
        return None, None
    lines = [re.sub(r"<https?://[^>]*>|https?://\S+", "", ln).strip()
             for ln in body[:5500].splitlines()]
    for i, line in enumerate(lines):
        if EXCLUDE_DATE.search(line):
            continue
        if not re.match(
            r"^(?:[■●◆]\s*)?(?:開催日時|開催日|開催時間|配信日時|配信開始日時|日時|日程)"
            r"(?:\s*[：:]|\s*$)",
            line,
        ):
            continue
        context = [line]
        if i + 1 < len(lines):
            following = lines[i + 1]
            # Allow the schedule to wrap onto a second line, but do not
            # consume a different labelled field (especially a deadline).
            if (not EXCLUDE_DATE.search(following)
                    and not re.match(
                        r"^(?:参加費|受講料|料金|講師|主催|会場|対象|詳細|申込|応募|受付|視聴期限)[：:]",
                        following,
                    )
                    and re.match(
                        r"^(?:20\d{2}\s*年|\d{1,2}\s*月|\d{1,2}[：:]\d{2}\b)",
                        following,
                    )):
                context.append(following)
        local = " ".join(context)
        dates = _dates(local)
        if dates:
            if len(dates) != 1 or dates[0] != event_date:
                continue
        else:
            monthdays = list(MONTH_DAY.finditer(local))
            if (len(monthdays) != 1
                    or (int(monthdays[0].group(1)), int(monthdays[0].group(2)))
                    != (target.month, target.day)):
                continue
        matches = list(re.finditer(
            r"(?<!\d)([01]?\d|2[0-3])[：:]([0-5]\d)(?!\d)", local
        ))
        if len(matches) == 1:
            m = matches[0]
            return f"{int(m.group(1)):02d}:{m.group(2)}", None
        if len(matches) == 2:
            range_match = TIME_RANGE.search(local)
            if range_match and range_match.start() == matches[0].start():
                return (
                    f"{int(range_match.group(1)):02d}:{range_match.group(2)}",
                    f"{int(range_match.group(3)):02d}:{range_match.group(4)}",
                )
    return None, None


def _feed_explicit_start_time(body, event_date):
    """A single-start helper; multi-time fields must not be guessed."""
    start, end = _feed_schedule_times(body, event_date)
    return start if end is None else None


def _feed_price(body):
    """Require an explicit price heading; generic '無料' may refer to a gift."""
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    for i, line in enumerate(lines):
        m = re.match(r"^(?:参加費|受講料|料金)[：:\s]*(.*)$", line)
        if not m:
            continue
        value = m.group(1).strip() or (lines[i + 1] if i + 1 < len(lines) else "")
        if len(value) > 100 or not value:
            continue
        # A free member account, free trial, or free tier alongside a
        # paid amount does not make the entire seminar free.
        if re.search(r"[0-9０-９,，]+\s*円", value):
            return value[:100], None
        if re.fullmatch(r"無料(?:\s*[（(]税込[）)])?", value):
            return "無料", True
    return None, None


def _feed_status(title, body):
    """Avoid '満席' from sidebar recommendations or unrelated events."""
    m = STATUS.search(title)
    if m:
        return m.group(0)
    for line in body.splitlines():
        matched = re.search(r"^(?:受付状況|申込状況|募集状況)\s*[：:]\s*(受付終了|申込終了|募集終了|受付中|申込受付中|満席|キャンセル待ち|残り\d+席)", line.strip())
        if matched:
            return matched.group(1)
    return None


def _feed(text,page,today):
    out=[]
    for chunk in re.split(r"(?m)^=====\s*$",text):
        m=re.search(r"(?m)^記事タイトル:\s*(.+)$",chunk)
        u=re.search(r"(?m)^記事URL:\s*<(https?://[^>]+)>",chunk)
        if not (m and u):
            continue
        title=m.group(1).strip()
        if not re.search(r"セミナー|ライブ|講習|学会|実習|ウェビナー|勉強会|講演|講座|腫瘍|内科|外科|看護|眼科",title):
            continue
        post = re.search(r"(?m)^公開日:\s*(20\d{2}-\d{2}-\d{2})\s*$",chunk)
        body=re.sub(r"(?m)^公開日:.*$","",chunk)
        when=_feed_event_schedule(body, post.group(1) if post else None)
        # Explicit labels win over unrelated sidebar text and promotions.
        content=re.sub(r"<https?://[^>]*>","",body)
        e=_event(title,when,u.group(1),page,content[:5500],"VETS TECH")
        e["status"] = _feed_status(title, content)
        e["price"], e["is_free"] = _feed_price(content)
        e["deadline"] = _explicit_deadline(content, when)
        e["start_time"], e["end_time"] = _feed_schedule_times(content, when)
        if re.search(r"[\[［【]録画[\]］】]|(?:^|　)録画", title):
            e["format"] = "オンデマンド"
        elif re.search(r"[\[［【]ライブ[\]］】]", title):
            e["format"] = "ライブ配信"
        elif "実習" in title:
            e["format"] = "現地"
        out.append(e)
    return out


def _lifetail(text,page,today,stats):
    lines=text.splitlines();out=[]
    for i,line in enumerate(lines):
        item=_line_link(line)
        if not item:continue
        raw,url=item
        if len(raw)<8 or re.search(r"^(申込|詳細|一覧|ログイン|マイページ|メニュー|会員|もっと見る|ALL|カテゴリ)",raw,re.I):continue
        if not re.search(r"セミナー|講座|講習|実習|学会|獣医|犬|猫|内科|外科|麻酔|看護|腹腔|画像|臨床|病理|救急|栄養",raw):continue
        # Each listing link contains its OWN session date and time in its label.
        # Do not look at preceding or following cards: that assigned wrong dates.
        dates=_dates(raw)
        when=dates[0] if dates else None
        # On-demand distribution ranges may carry two full dates. Only link
        # them when a range separator occurs between those exact date spans.
        matches=list(YMD.finditer(raw))
        between=raw[matches[0].end():matches[1].start()] if len(matches)>1 else ""
        end=dates[1] if len(dates)>1 and re.search(r"[〜～~–-]",between) else None
        if not when:stats["undated_cards"]=stats.get("undated_cards",0)+1
        # The web page uses a combined label containing title/speaker/time.
        # Retain the full label until card-level selectors are verified.
        e=_event(raw,when,url,page,raw,"Life&Tail",end=end)
        # Broadcast listings end in ライブ; do not infer an on-site venue from
        # a word like 東京 in the talk's title.
        if re.search(r"(?:^|\s)ライブ\s*$",raw) or "無料ライブ" in raw: e["format"]="ライブ配信"
        if re.search(r"(?:^|\s)実習\s*$",raw): e["format"]="現地"
        e["prefecture"]=_pref(raw,e["format"])
        out.append(e)
    return out


# --------------------------------------------------------------------------
# New free sources: each record is strictly tied to its own official link.
# --------------------------------------------------------------------------
PEPPY_CARD = re.compile(r"^CARD\[(web|onsite|unknown)\]\s+(.+?)\s+<(https?://[^>\s]+)>$")
PEPPY_TARGETS = re.compile(
    r"\s+(?:受付中|受付終了|申込終了|募集終了|満席)(?=\s|$)"
)
PEPPY_WDAY = re.compile(r"^\s*[\(（][月火水木金土日][\)）]\s*")



def _vets_academy(text, page, today, stats):
    """Parse only dates and metadata carried by the same official card."""
    import json
    out = []
    for line in text.splitlines():
        if not line.startswith("ACADEMY_CARD "):
            continue
        try:
            item = json.loads(line[len("ACADEMY_CARD "):])
        except (ValueError, TypeError):
            continue
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str):
            continue
        parsed = urlparse(url)
        if (parsed.scheme != "https" or parsed.hostname != "academy.eduone.jp"
                or not re.fullmatch(r"/seminar/detail/\d+/?", parsed.path)):
            continue
        title = item.get("title")
        schedule = item.get("schedule")
        if not isinstance(title, str) or len(title.strip()) < 5 or not isinstance(schedule, str):
            continue
        dates = re.findall(r"(?<!\d)(20\d{2})/(\d{1,2})/(\d{1,2})(?!\d)", schedule)
        if not dates or len(dates) > 2:
            continue
        start = _date(*dates[0])
        end = _date(*dates[1]) if len(dates) == 2 else None
        if not start or (len(dates) == 2 and (not end or end < start)):
            continue
        kind = item.get("kind")
        if kind not in ("LIVE", "オンデマンド", "会場型"):
            continue
        event = _event(title, start, url, page, title, "VETS ACADEMY", end=end)
        event["format"] = ("ライブ配信" if kind == "LIVE" else
                           "オンデマンド" if kind == "オンデマンド" else "現地")
        explicit = item.get("audiences")
        if not isinstance(explicit, list):
            explicit = []
        event["audience"] = [
            value for source, value in (("獣医師", "獣医師"),
                                        ("動物看護", "動物看護師"),
                                        ("トリマー", "トリマー"))
            if source in explicit
        ]
        status = item.get("status")
        event["status"] = status if status in ("募集中", "募集終了") else None
        if item.get("free") == "無料":
            event["price"], event["is_free"] = "無料", True
        # Live sessions and on-demand publication dates have different
        # semantics. Only a time printed on this card may be populated.
        if kind != "オンデマンド":
            times = re.findall(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)", schedule)
            if times:
                event["start_time"] = f"{int(times[0][0]):02d}:{times[0][1]}"
        out.append(event)
    stats["academy_cards"] = len(out)
    return out


def _peppy(text, page, today, stats):
    out = []
    for line in text.splitlines():
        m = PEPPY_CARD.match(line.strip())
        if not m:
            continue
        kind, label, url = m.groups()
        parsed = urlparse(url)
        if (parsed.scheme != "https"
                or parsed.hostname not in ("peppy.jp", "www.peppy.jp")
                or not re.fullmatch(r"/seminar/\d+/?", parsed.path)):
            continue
        found = list(YMD.finditer(label))
        if not found:
            continue
        dates = [_date(*d.groups()) for d in found]
        if not dates[0]:
            continue
        candidate = PEPPY_WDAY.sub("", label[found[-1].end():]).strip()
        candidate = PEPPY_TARGETS.split(candidate, 1)[0].strip()
        candidate = candidate.lstrip("～〜~ー- ：:")
        # Keep seminar title tied to this linked card; never borrow from neighbors.
        if len(candidate) < 7:
            continue
        end = None
        if len(found) >= 2 and dates[-1] and dates[-1] >= dates[0]:
            between = label[found[0].end():found[1].start()]
            if re.search(r"[～〜~－–]", between):
                end = dates[-1]
        e = _event(candidate, dates[0], url, page, label, "PEPPY", end=end)
        # List headings explicitly distinguish online from in-person events.
        if kind == "web":
            e["format"] = "ライブ配信"
            e["prefecture"] = None
        elif kind == "onsite":
            e["format"] = "現地"
        if "【無料】" in candidate or "〖無料〗" in candidate:
            e["price"], e["is_free"] = "無料", True
        out.append(e)
    stats["peppy_cards"] = len(out)
    return out


def _eduone(text, page, today, stats):
    heading = re.search(r"(?m)^TITLE:\s*(.+)$", text)
    link = re.search(r"(?m)^URL:\s*<(https?://[^>]+)>", text)
    if not heading or not link:
        return []
    title = heading.group(1).strip()
    body = text.split("BODY:\n", 1)[-1]
    when = _feed_event_schedule(body)
    if not when:
        # Never classify a registration window or publication timestamp as
        # lecture start. Explicit schedule label only.
        stats["eduone_missing_schedule"] = stats.get("eduone_missing_schedule", 0) + 1
        return []
    e = _event(title, when, link.group(1), page, body, "EDUWARD Press")
    e["price"], e["is_free"] = _feed_price(body)
    # Lecture end time may be expressed after a repeated full date, not
    # a conventional HH:MM-HH:MM span.
    if not e["start_time"]:
        detail = re.search(r"(?:開催日時|開催日)[^\n]*\n?([^\n]{0,150})", body)
        if detail:
            ts = re.findall(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)", detail.group(0))
            if ts:
                e["start_time"] = f"{int(ts[0][0]):02d}:{ts[0][1]}"
                if len(ts)>1:
                    e["end_time"] = f"{int(ts[-1][0]):02d}:{ts[-1][1]}"
    if re.search(r"オンデマンド|録画配信", title):
        e["format"] = "オンデマンド"
    elif e["format"] is None:
        e["format"] = "ライブ配信"
    stats["eduone_detail"] = stats.get("eduone_detail", 0) + 1
    return [e]



# Official, *event-specific* conference notices verified on 2026-11-07.
# The original source URL is retained; this is a separate details link.
JBVP_DETAIL_LINKS = {
    "名古屋": ("2027-02-28", "https://www.jbvp.org/regional/nagoya.html"),
    "京都": ("2027-03-07", "https://www.jbvp.org/regional/kyoto.html"),
    "九州": ("2027-03-21", "https://www.jbvp.org/regional/kyushu.html"),
    "東北": ("2027-03-28", "https://www.jbvp.org/regional/tohoku.html"),
    "北海道": ("2027-03-28", "https://www.jbvp.org/regional/hokkaido.html"),
}


def _jbvp_detail_url(title, start_date):
    if "地区大会" not in title:
        return None
    for region, (date, official_url) in JBVP_DETAIL_LINKS.items():
        if region in title and date == start_date:
            return official_url
    return None


def _jsvd_abstract_deadline(lines, index, event_pat, event_date):
    """Separate scientific abstract submission from event registration.

    The conference's own explicit "一般演題募集" range is required. Dates
    mentioned under other events, membership, or registration are ignored.
    """
    for j in range(index + 1, min(index + 31, len(lines))):
        line = lines[j]
        if event_pat.search(line):
            break
        compact = re.sub(r"\s+", "", line)
        if not re.match(r"^(?:一般演題募集|演題募集期間|一般講演募集|抄録募集期間)[|:：]?", compact):
            continue
        date_string = compact
        if len(_dates(date_string)) < 2 and j + 1 < len(lines) and not event_pat.search(lines[j+1]):
            date_string += lines[j+1].strip()
        matches = _dates(date_string)
        if len(matches) >= 2 and matches[0] <= matches[-1] <= event_date:
            return matches[-1]
    return None



def _jbvp_listing_venue(lines, start):
    """Only read the venue from the same explicitly dated JBVP listing card."""
    dated = False
    for i, line in enumerate(lines):
        normalized = unicodedata.normalize("NFKC", line).strip()
        if re.match(r"^(?:日程|日時|開催日)\s*[：:|]?", normalized):
            schedule = re.sub(r"^(?:日程|日時|開催日)\s*[：:|]?", "", normalized).strip()
            if not schedule and i + 1 < len(lines):
                schedule = lines[i + 1].strip()
            if start in _dates(schedule):
                dated = True
        if not dated:
            continue
        venue_label = re.match(r"^会場\s*[：:|]?\s*(.*)$", normalized)
        if not venue_label:
            continue
        value = venue_label.group(1).strip()
        if not value and i + 1 < len(lines):
            value = lines[i + 1].strip()
        if not (3 <= len(value) <= 90):
            return None
        if (re.search(r"https?://|<|>|〒|TEL|FAX|E-mail|お問い合わせ", value, re.I)
                or _dates(value)
                or value.startswith(("日程", "日時", "会場", "登録", "申込", "主催"))):
            return None
        return value
    return None


def _jbvp(text, page, today, stats):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    out, seen = [], set()
    today_floor = today  # new listings are upcoming-only
    for i, line in enumerate(lines):
        if not re.search(r"(?:地区大会|年次大会|企業フォーラム|WJVF)", line):
            continue
        # Event heading excludes navigation. Require a titled meeting.
        if not re.search(r"(?:第\d+回|第\d+期|2027|2026|オンラインプログラム)", line):
            continue
        if len(line) > 110 or "サイトはこちら" in line:
            continue
        # Date must occur soon after THIS heading, before another meeting.
        fragment = []
        for following in lines[i+1:i+9]:
            if re.search(r"(?:第\d+回|第\d+期)\s*.+(?:地区大会|年次大会)",following):
                break
            fragment.append(following)
        block = "\n".join(fragment)
        full = _dates(block)
        if not full:
            continue
        start = full[0]
        if start < today_floor.isoformat():
            continue
        k = (norm(line), start)
        if k in seen:
            continue
        seen.add(k)
        e = _event(line, start, page, page, block, "JBVP", end=_range_end(block, start))
        e["topics"] = ["学会・大会"]
        online = "オンライン" in line or "オンライン配信" in block
        e["format"] = "オンデマンド" if online else "現地"
        # 配信方法・配信場所を実在する物理会場として登録しない。
        # Official physical meeting venues are extracted only for onsite cards.
        if not online:
            venue = _jbvp_listing_venue(fragment, start)
            if venue and not re.fullmatch(r"(?:オンライン|オンライン配信|WEB|Web|Zoom|ウェブ配信|配信のみ)", venue, re.I):
                e["venue"] = venue
        e["detail_url"] = _jbvp_detail_url(line, start)
        out.append(e)
    stats["jbvp_meetings"] = len(out)
    return out


SOCIETY_TITLE_PATTERNS = {
    "javnu": re.compile(r"第\d+回\s*(?:日本獣医腎泌尿器学会\s*)?学術集会(?:・総会)?"),
    "jsvd": re.compile(r"(?:第\d+回.{0,40}獣医皮膚科学会学術大会|日本医真菌学会.{0,50}共催シンポジウム)"),
    "jvcs": re.compile(r"第\d+回.{0,30}日本獣医がん学会"),
    "jsvc": re.compile(r"第\d+回.{0,40}日本獣医循環器学会定例大会"),
}


def _range_end(label, start):
    """Second day of a clearly printed interval; never invent a missing date."""
    cleaned = unicodedata.normalize("NFKC", label)
    first = YMD.search(cleaned)
    if not first:
        return None
    tail = cleaned[first.end():first.end()+48]
    m = re.search(r"[～〜~・、,]\s*(?:(\d{1,2})\s*月)?\s*(\d{1,2})\s*日", tail)
    if not m:
        return None
    sd = datetime.date.fromisoformat(start)
    month = int(m.group(1)) if m.group(1) else sd.month
    y = sd.year + (1 if month < sd.month else 0)
    end = _date(y, month, int(m.group(2)))
    return end if end and end > start else None


def _jsvd_participant_deadline(lines, index, event_pat, event_date):
    """Participant registration only; tolerate HTML table cells on separate lines.

    JA/JSVD homepages often use <th>参加受付期間</th><td>...</td>, whose
    extracted text spans multiple lines. Bound parsing to the matching
    symposium and never use abstract, sponsor or exhibition deadlines.
    """
    for j in range(index + 1, min(len(lines), index + 42)):
        if event_pat.search(lines[j]):
            break
        label = re.sub(r"\s+", "", lines[j])
        if not re.match(r"^参加(?:受付|申込|申し込み)期間[|:：]?", label):
            continue
        # A date can occupy several adjacent table cells/lines; stop before
        # the next labeled field or prose so unrelated dates cannot enter.
        parts = [label]
        for nextline in lines[j+1:min(len(lines),j+9)]:
            compact = re.sub(r"\s+", "", nextline)
            if (event_pat.search(nextline)
                or re.match(r"^(?:参加ご希望|参加費|参加費用|会場|日程|演題|申込み|お申込み|"
                            r"申込はこちら|次回|AiANZ|認定医更新)", compact)):
                break
            parts.append(compact)
            if len(YMD.findall("".join(parts))) >= 2:
                break
        piece = "".join(parts)
        full = list(YMD.finditer(piece))
        if not full:
            continue
        first = _date(*full[0].groups())
        if not first:
            continue
        if len(full) >= 2:
            deadline = _date(*full[-1].groups())
        else:
            tail = piece[full[0].end():]
            m = re.search(r"(?:\([月火水木金土日]\))?\s*[～〜~－–-]\s*"
                          r"(\d{1,2})月\s*(\d{1,2})日", tail)
            if not m:
                continue
            month, day = map(int, m.groups())
            year = int(full[0].group(1)) + (month < int(full[0].group(2)))
            deadline = _date(year, month, day)
        if deadline and first <= deadline <= event_date:
            return deadline
    return None

# Only meeting+date combinations with explicitly supported official information.
# Never infer credentials from the title or from a different society's page.
def _certification_for_meeting(society, title, start, section_lines):
    if society == "jsvd" and "共催シンポジウム" in title and start == "2026-11-22":
        region = "\n".join(section_lines)
        m = re.search(r"(?:日本獣医皮膚科学会)?認定医更新評価点\s*(\d{1,2})\s*ポイント", region)
        if m:
            return ("日本獣医皮膚科学会認定医更新評価点 " + m.group(1) +
                    "ポイント（参加条件・実績認定は主催者で確認）",
                    "https://www.jsvd.jp/")
        return None, None
    if society == "jsvd" and "学術大会" in title and start == "2027-03-20":
        return ("一般講演での発表は認定医制度上「国内学会発表」扱い（点数は明記なし）",
                "https://www.jsvd.jp/topics/30meeting/announcement.html")
    if society == "javnu" and "第19回学術集会" in title and start == "2027-08-21":
        return ("認定医制度の学術集会参加単位：認定された出席1回につき1単位。"
                "個人のプログラム参加時期・出席確認条件に注意",
                "https://www.javnu.jp/certification/faq/")
    if society == "jsvc" and "第125回" in title and start == "2026-12-19":
        return ("2026年度認定医講習会の開催予定大会（講座22・23・34とアドバンスコース）。"
                "取得単位・受講条件は公式案内で確認",
                "https://www.jsvc.jp/certification/session/records/session2026/")
    return None, None


def _society(text, page, today, stats, society):
    pat = SOCIETY_TITLE_PATTERNS[society]
    orig = [line.strip() for line in text.splitlines() if line.strip()]
    lines = [unicodedata.normalize("NFKC", line) for line in orig]
    out, seen = [], set()
    for i, line in enumerate(lines):
        match = pat.search(line)
        if not match or len(line) > 115:
            continue
        # A heading is a name, not a long sentence mentioning another meeting.
        if len(line[match.end():].strip()) > 5:
            continue
        title = orig[i]
        # Find a nearby labelled event date, rejecting deadlines and
        # announcement timestamps even when they occur nearer to title.
        found = None
        section = []
        for j in range(i+1,min(len(lines),i+18)):
            nxt = lines[j]
            if j > i+1 and pat.search(nxt):
                break
            section.append(nxt)
            compact = re.sub(r"\s+", "", nxt)
            if EXCLUDE_DATE.search(compact):
                continue
            if not re.search(r"(?:会期|日程|日時|開催日)", compact):
                continue
            label = nxt + (" " + lines[j+1] if j+1<len(lines) else "")
            dates = _dates(label)
            if dates:
                found = (dates[0], label)
                break
        if not found and society == "javnu":
            # The JAVNU homepage prints the congress date immediately under
            # '第19回学術集会・総会' without a separate 会期 label.
            for line_after in lines[i+1:min(len(lines),i+5)]:
                if EXCLUDE_DATE.search(line_after):
                    continue
                dates = _dates(line_after)
                if dates:
                    found = (dates[0], line_after)
                    break
        if not found or found[0] < today.isoformat():
            continue
        start, label = found
        key = (norm(title),start)
        if key in seen:
            continue
        seen.add(key)
        context = "\n".join(section[:15])
        ev = _event(title,start,page,page,context,society.upper() if society!="jsvd" else "日本獣医皮膚科学会",
                    end=_range_end(label,start))
        ev["topics"] = ["学会・大会"]
        ev["format"] = "オンデマンド" if "オンライン" in title or "オンライン配信" in context else "現地"
        if society == "jsvd" and "共催シンポジウム" in title:
            ev["deadline"] = _jsvd_participant_deadline(lines, i, pat, start)
            if start == "2026-11-22":
                ev["detail_url"] = "https://2026.jsmm.org/"
        if society == "jsvd" and "学術大会" in title:
            ev["abstract_deadline"] = _jsvd_abstract_deadline(lines, i, pat, start)
            if start == "2027-03-20":
                ev["detail_url"] = "https://www.jsvd.jp/topics/30meeting/announcement.html"
        # Bound the evidence to this event, not the next conference/announcement.
        scope = []
        for following in lines[i+1:min(len(lines), i+75)]:
            if pat.search(following) or (
                society == "jsvd" and re.match(r"^AiANZ", following)
            ):
                break
            scope.append(following)
        ev["certification_note"], ev["certification_url"] = _certification_for_meeting(
            society, title, start, scope)
        out.append(ev)
    stats["society_meetings"] = len(out)
    return out



# --------------------------------------------------------------------------
# New official sources: meeting- and course-specific, no date inference.
# Source-specific details are read only from the associated card or programme
# section. This avoids borrowing application dates from old meetings.
def _jsvas(text, page, today, stats):
    """JSVAS regional lectures (linked cards) and current meeting programme."""
    lines = [unicodedata.normalize("NFKC", x.strip()) for x in text.splitlines() if x.strip()]
    found = []
    if "/lectures/index.php" in page:
        for line in lines:
            # Each HTML card is a single linked block after html_to_text.
            link = re.search(r"<(https://(?:www\.)?jsvas\.net/lectures/[a-zA-Z0-9_-]+\.php)>", line)
            if not link:
                continue
            card = line[:link.start()].strip()
            if "日時" not in card or not ("地区講習会" in card or "症例検討会" in card):
                continue
            date_section = card.split("日時", 1)[1].split("会場", 1)[0]
            dates = _dates(date_section)
            if not dates or dates[0] < today.isoformat():
                continue
            # Preserve the official lecture title and any seminar subtitle,
            # but never copy an adjacent speaker, date, or venue into it.
            head = re.split(r"講師|演者|日時|会場",card, maxsplit=1)[0].strip()
            title_match = re.search(r"20\d{2}年度|第\d+回",head)
            if not title_match:
                continue
            title = head[title_match.start():].strip()
            if not (8 <= len(title) <= 180):
                continue
            start = dates[0]
            url = link.group(1)
            ev = _event(title,start,url,page,card,"日本獣医麻酔外科学会")
            ev["audience"] = ["獣医師"]
            # Keep known venue only where this event's card explicitly says it.
            if "会場" in card:
                venue = card.rsplit("会場",1)[1].strip()
                if venue and len(venue) < 100:
                    ev["venue"] = venue
            ev["topics"] = _topics(title)
            if "岡山国際交流センター" in card:
                ev["prefecture"] = "岡山県"
            elif "ライトキューブ宇都宮" in card:
                ev["prefecture"] = "栃木県"
            if "講師" in card and "日時" in card:
                speakers = card.split("講師",1)[1].split("日時",1)[0]
                ev["speaker"] = _speakers_in_title(speakers)
            found.append(ev)
    elif re.search(r"/conference/20\d{2}-\d+\.php$",page):
        body = "\n".join(lines)
        # The event number and name must be explicitly printed in the same
        # programme. Do not use global site navigation's archive links.
        edition = re.search(r"20\d{2}年度\s+第(\d{2,3})回",body)
        if not edition:
            edition = re.search(r"20\d{2}年度第(\d{2,3})回",body)
        ix = next((i for i,line in enumerate(lines) if line == "開催期間"),None)
        if edition and ix is not None:
            # "動画配信期間" often repeats the first congress date on the
            # next line. Never use that as the congress's end date.
            schedule_lines = lines[ix+1:ix+4]
            dated_line = next((i for i, ln in enumerate(schedule_lines) if _dates(ln)), None)
            datestr = schedule_lines[dated_line] if dated_line is not None else ""
            if dated_line is not None and datestr.endswith(("〜", "～", "-", "–")):
                if dated_line+1 < len(schedule_lines):
                    datestr += " " + schedule_lines[dated_line+1]
            dates = _dates(datestr)
            if dates and dates[0] >= today.isoformat():
                date = dates[0]
                title = f"第{edition.group(1)}回 日本獣医麻酔外科学会学術集会"
                # Confirm title is genuinely present, not just a nav item.
                if norm(title) in norm(body):
                    end = _range_end(datestr, date)
                    if not end:
                        # Fully specified second dates on the SAME labeled
                        # schedule line are permissible only for a short meeting.
                        following = [d for d in dates[1:] if d > date and
                                     (datetime.date.fromisoformat(d) -
                                      datetime.date.fromisoformat(date)).days <= 7]
                        end = following[0] if following else None
                    scope = "\n".join(lines[ix:min(len(lines),ix+20)])
                    ev = _event(title,date,page,page,scope,"日本獣医麻酔外科学会",end=end)
                    ev["format"] = "ハイブリッド" if "ハイブリッド開催" in body else "現地"
                    ev["audience"] = ["獣医師"]
                    ev["topics"] = ["学会・大会"]
                    vi = next((j for j in range(ix+1,min(len(lines),ix+15))
                               if lines[j]=="会場"),None)
                    if vi is not None and vi+1 < len(lines):
                        v=lines[vi+1].split(" <")[0].strip()
                        if len(v)<=100:
                            ev["venue"]=v
                            if "大阪" in v: ev["prefecture"]="大阪府"
                    # Registration periods can extend AFTER the in-person
                    # meeting for recorded lectures; no invented final deadline.
                    found.append(ev)
    stats["jsvas_cards"]=len(found)
    return found


def _jcvim(text,page,today,stats):
    """One dated JCVIM congress announcement; ignore earlier years' news."""
    lines=[unicodedata.normalize("NFKC",x.strip()) for x in text.splitlines() if x.strip()]
    out=[]
    for i,line in enumerate(lines):
        m=re.match(r"^(第\d+回日本獣医内科学アカデミー学術大会)(?:\s*[（(]JCVIM(\d{4})[)）])?のご案内$",line)
        if not m:
            continue
        year = int(m.group(2)) if m.group(2) else None
        if year is None:
            continue
        block = lines[i+1:min(len(lines),i+8)]
        when = next((x for x in block if x.startswith("会期")),None)
        if not when:
            continue
        dates = _dates(when)
        if not dates or not dates[0].startswith(str(year)) or dates[0] < today.isoformat():
            continue
        date=dates[0]
        end=dates[-1] if len(dates)>1 else _range_end(when,date)
        ev = _event(m.group(1),date,page,page,when,"日本獣医内科学アカデミー",end=end)
        ev["topics"]=["学会・大会"]
        ev["audience"]=["獣医師","動物看護師"]
        ev["format"]="現地"
        venue = next((x.split("：",1)[-1].split(":",1)[-1].strip()
                      for x in block if re.match(r"^会場[：:]",x)),None)
        if venue:
            ev["venue"]=venue
            if "横浜" in venue: ev["prefecture"]="神奈川県"
        # This meeting-specific official conference microsite was verified
        # against the exact event number and date, not a sponsor's advert.
        if year == 2027 and date == "2027-02-19" and "第23回" in m.group(1):
            ev["detail_url"]="https://smartconf.jp/content/jcvim2027/outline"
        out.append(ev)
        break
    stats["jcvim_meetings"]=len(out)
    return out


# --------------------------------------------------------------------------
# JVNA and the Annual Meeting of Veterinary Clinical Medicine.
# Scope parsing to official events and their own labeled registration blocks.
def _jvna_congress(text, page, today, stats):
    """Only the dated JVNA nursing congress, not its abstract / file deadlines."""
    lines=[unicodedata.normalize("NFKC",x.strip()) for x in text.splitlines() if x.strip()]
    out=[]
    if not page.rstrip("/").endswith("/16thkangotaikai"):
        return out
    title="第16回 動物看護大会"
    if not any(re.search(r"第16回\s*動物看護大会",line) for line in lines):
        return out
    # A meeting date needs the explicit event-date label, never 2026 dates in
    # the later presentation-submission timetable.
    date_idx=next((i for i,line in enumerate(lines) if re.match(r"^開催日時\s*[：:]?",line)),None)
    if date_idx is None:
        return out
    schedule=" ".join(lines[date_idx:date_idx+3])
    dates=_dates(schedule)
    if not dates or dates[0] < today.isoformat():
        return out
    date=dates[0]
    ev=_event(title,date,page,page,schedule,"日本愛玩動物看護師会")
    ev["audience"]=["動物看護師","学生"]
    ev["topics"]=["学会・大会"]
    ev["format"]="現地"
    ev["prefecture"]="大阪府"
    # Do not derive time by reading abstract deadlines; this is specifically
    # the date row's HH時 text.
    time_pair=re.search(r"(?<!\d)(\d{1,2})\s*時\s*[～〜~\-]\s*(\d{1,2})\s*時",schedule)
    if time_pair:
        ev["start_time"]=f"{int(time_pair.group(1)):02d}:00"
        ev["end_time"]=f"{int(time_pair.group(2)):02d}:00"
    # Venue can be wrapped over the next one or two rows.
    venue_i=next((i for i in range(date_idx+1,min(len(lines),date_idx+18))
                  if re.match(r"^会場\s*[：:]?$",lines[i])),None)
    if venue_i is not None:
        scope=" ".join(lines[venue_i+1:venue_i+5])
        if "大阪ペピイ動物看護専門学校" in scope:
            ev["venue"]="大阪ペピイ動物看護専門学校"
    # Bounded: the attendance deadline precedes '動物看護研究演題募集'.
    end_idx=next((i for i,line in enumerate(lines)
                  if i>date_idx and "動物看護研究演題募集" in line),len(lines))
    for i in range(date_idx+1,end_idx):
        line=lines[i]
        if not re.match(r"^申込期限\s*[：:]?",line):
            continue
        candidates=_dates(" ".join(lines[i:i+3]))
        if candidates and candidates[0]<=date:
            ev["deadline"]=candidates[0]
        break
    # Fees only from explicit membership pricing on the meeting's own page.
    before=" ".join(lines[date_idx:end_idx])
    m1=re.search(r"JVNA正会員\s*([\d,]+円)",before)
    m2=re.search(r"非会員\s*([\d,]+円)",before)
    if m1 and m2:
        ev["price"]="JVNA正会員 "+m1.group(1)+"（実習なし）／非会員 "+m2.group(1)+"（実習なし）"
        ev["is_free"]=None
    out.append(ev)
    stats["jvna_congresses"]=len(out)
    return out


def _dourinken_meeting(text,page,today,stats):
    """Exact annual meeting in the official next-year section (Reiwa calendar).

    The page also retains the previous annual meeting, its abstract deadlines
    and certification examinations. Only next year's event dates count.
    """
    lines=[unicodedata.normalize("NFKC",x.strip()) for x in text.splitlines() if x.strip()]
    out=[]
    if not page.startswith("https://dourinken.com/taikai/guide"):
        return out
    idx=next((i for i,line in enumerate(lines) if "来年の御案内" in line),None)
    if idx is None:
        return out
    section=lines[idx+1:idx+12]
    if not any("第48回動物臨床医学会年次大会" in l for l in section):
        return out
    scheduled=next((l for l in section if re.match(r"^日\s*時[：:]",l)),None)
    if not scheduled:
        return out
    m=re.search(r"令和\s*(\d{1,2})年\s*(\d{1,2})月\s*(\d{1,2})日",scheduled)
    if not m:
        return out
    reiwa,month,day=map(int,m.groups())
    if not 1<=reiwa<=40:
        return out
    year=2018+reiwa
    date=_date(year,month,day)
    if not date or date < today.isoformat():
        return out
    ev=_event("第48回動物臨床医学会年次大会",date,page,page,scheduled,
              "動物臨床医学会")
    ev["audience"]=["獣医師","動物看護師","学生"]
    ev["topics"]=["学会・大会"]
    ev["format"]="現地"
    ev["prefecture"]="大阪府"
    m2=re.search(r"[,、・~～〜]\s*(\d{1,2})日",scheduled[m.end():])
    if m2:
        end=_date(year,month,int(m2.group(1)))
        if end and date<end and (datetime.date.fromisoformat(end)-datetime.date.fromisoformat(date)).days<=4:
            ev["end_date"]=end
    venue=next((l for l in section if re.match(r"^会\s*場[：:]",l)),None)
    if venue:
        v=venue.split(":",1)[-1].split("：",1)[-1].strip()
        if len(v)<=100 and "大阪府立国際会議場" in v:
            ev["venue"]="大阪府立国際会議場（グランキューブ大阪）"
    out.append(ev)
    stats["dourinken_meetings"]=len(out)
    return out


def extract_free(source_name,page_url,hint,text,today,stats):
    source=source_name.lower().replace("&","")
    if "jaha" in source or "日本動物病院協会" in source:
        raw=_jaha_top(text,page_url,today,stats) if "/seminar-calendar/top/" in page_url else _jaha(text,page_url,today,stats)
    elif "vets academy" in source:raw=_vets_academy(text,page_url,today,stats)
    elif "peppy" in source:raw=_peppy(text,page_url,today,stats)
    elif "eduward" in source or "eduone" in source:raw=_eduone(text,page_url,today,stats)
    elif source in ("javnu", "日本獣医腎泌尿器学会"):raw=_society(text,page_url,today,stats,"javnu")
    elif source in ("日本獣医皮膚科学会","jsvd"):raw=_society(text,page_url,today,stats,"jsvd")
    elif source in ("日本獣医がん学会","jvcs"):raw=_society(text,page_url,today,stats,"jvcs")
    elif source in ("日本獣医循環器学会","jsvc"):raw=_society(text,page_url,today,stats,"jsvc")
    elif source in ("日本獣医麻酔外科学会","jsvas"):raw=_jsvas(text,page_url,today,stats)
    elif source in ("jcvim","日本獣医内科学アカデミー"):raw=_jcvim(text,page_url,today,stats)
    elif source in ("日本愛玩動物看護師会","jvna"):raw=_jvna_congress(text,page_url,today,stats)
    elif source in ("動物臨床医学会","dourinken"):raw=_dourinken_meeting(text,page_url,today,stats)
    elif "jbvp" in source:raw=_jbvp(text,page_url,today,stats)
    elif "学際" in source:raw=_gakusai(text,page_url,today)
    elif "vets tech" in source or "vetstech" in source:raw=_feed(text,page_url,today)
    elif "lifetail" in source or "life" in source:raw=_lifetail(text,page_url,today,stats)
    else:raw=[]
    checked=validate(raw,text,page_url,today,stats)
    for e in checked:
        if not e["start_date"] or e["url_is_page"]:e["verified"]=False
    stats["free_extracted"]=stats.get("free_extracted",0)+len(checked)
    return checked
