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
TIME_RANGE = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)\s*[〜~～－―–-]\s*([01]?\d|2[0-3]):([0-5]\d)")
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
    if "一般すべて" in context or "飼い主向け" in context: items.append("一般")
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
    if re.search(r"(?:^|\s)無料(?:\s|$)|無料ライブ|無料配信",context): return "無料", True
    for line in context.splitlines():
        if re.search(r"(参加費|受講料|料金|受講費)[：: ]",line) and len(line)<130:
            return line.strip()[:110], True if "無料" in line else None
    return None,None


def _event(title,when,url,page,context="",organizer=None,end=None):
    fmt=_fmt(context+" "+title)
    t1,t2=_times(context)
    price,free=_price(context)
    m=STATUS.search(context)
    return {"title":title.strip(), "start_date":when, "end_date":end, "start_time":t1,"end_time":t2,
        "format":fmt,"venue":None,"prefecture":_pref(context+" "+title,fmt),
        "audience":_audience(context+" "+title),"topics":_topics(title),
        "price":price,"is_free":free,"status":m.group(0) if m else None,
        "deadline":None,"organizer":organizer,"url":url or page,"evidence":title.strip()}


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
        detail=next((l[1] for s in seg[:4] if (l:=_line_link(s)) and "詳細はこちら" in l[0]),None)
        date_line=next((s for s in seg[1:8] if MONTH_DAY.search(s) and not s.startswith("No.")),"")
        if not date_line:continue
        for section in re.split(r"[｜|]",date_line):
            if "ウェブ受講" in section or "オンデマンド" in section:continue
            m=MONTH_DAY.search(section)
            if not m:continue
            sd=_date(year,*m.groups())
            if sd:out.append(_event(title,sd,detail,page,section,"学際企画"))
    return out


def _feed_event_schedule(body):
    """Extract event dates only, never an article URL, posting date or deadline."""
    lines=[re.sub(r"<https?://[^>]*>|https?://\S+","",ln).strip() for ln in body.splitlines()]
    # Find dates explicitly associated with an event schedule label.
    candidates=[]
    for i,line in enumerate(lines):
        if EXCLUDE_DATE.search(line):continue
        if not EVENT_LABEL.search(line):continue
        local=" ".join(lines[i:min(len(lines),i+3)])
        dates=_dates(local)
        if not dates:
            y=_year(local)
            m=MONTH_DAY.search(local)
            if m and y:dates=[_date(y,*m.groups())]
        if dates:
            candidates.extend(d for d in dates if d)
    if candidates:
        # More than one date can represent a broadcast interval; the first
        # explicitly labelled occurrence is the event start.
        return candidates[0]
    # Only if a standalone full-year date line itself mentions the event and
    # a time/online/venue, without a post/registration label.
    for line in lines:
        if EXCLUDE_DATE.search(line):continue
        if re.search(r"ライブ配信|オンライン開催|開催\s*[:：]|セミナー開始",line) and (_dates(line)):
            return _dates(line)[0]
    return None


def _feed(text,page,today):
    out=[]
    for chunk in re.split(r"(?m)^=====\s*$",text):
        m=re.search(r"(?m)^記事タイトル:\s*(.+)$",chunk)
        u=re.search(r"(?m)^記事URL:\s*<(https?://[^>]+)>",chunk)
        if not (m and u):continue
        title=m.group(1).strip()
        if not re.search(r"セミナー|ライブ|講習|学会|実習|ウェビナー|勉強会|講演|講座|腫瘍|内科|外科|看護|眼科",title):continue
        body=re.sub(r"(?m)^公開日:.*$","",chunk)
        when=_feed_event_schedule(body)
        # Do not include article URL or publish date in context/time extraction.
        content=re.sub(r"<https?://[^>]*>","",body)
        out.append(_event(title,when,u.group(1),page,content[:5500],"VETS TECH"))
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


def extract_free(source_name,page_url,hint,text,today,stats):
    source=source_name.lower().replace("&","")
    if "jaha" in source or "日本動物病院協会" in source:raw=_jaha(text,page_url,today,stats)
    elif "学際" in source:raw=_gakusai(text,page_url,today)
    elif "vets tech" in source or "vetstech" in source:raw=_feed(text,page_url,today)
    elif "lifetail" in source or "life" in source:raw=_lifetail(text,page_url,today,stats)
    else:raw=[]
    checked=validate(raw,text,page_url,today,stats)
    for e in checked:
        if not e["start_date"] or e["url_is_page"]:e["verified"]=False
    stats["free_extracted"]=stats.get("free_extracted",0)+len(checked)
    return checked
