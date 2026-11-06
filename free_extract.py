# -*- coding: utf-8 -*-
"""APIを使わない保守的なセミナー情報抽出。情報不明ならnullで残す。"""
import datetime
import re
import unicodedata
from extract import validate, norm, TOPICS

LINK = re.compile(r"^(.*?)\s*<(https?://[^>\s]+)>\s*$")
MONTH_DAY = re.compile(r"(1[0-2]|0?[1-9])\s*月\s*([12]?\d|3[01])\s*日")
YMD = re.compile(r"(20\d{2})\s*[年./-]\s*(1[0-2]|0?[1-9])\s*[月./-]\s*([12]?\d|3[01])\s*日?")
DAY = re.compile(r"^\s*(1[0-2]|0?[1-9])\s*/\s*([12]?\d|3[01])\s*$")
STATUS = re.compile(r"受付中|申込受付中|受付終了|募集終了|満席|キャンセル待ち|残り\d+席")
TOPIC_HINTS = {
 "内科":"内科 総合診療", "外科":"外科 手術 縫合 整形 骨切り 実習 膝蓋骨",
 "麻酔・救急":"麻酔 救急 疼痛 集中治療", "画像診断":"画像 超音波 エコー CT MRI",
 "腫瘍":"腫瘍 リンパ腫 癌 がん", "循環器":"循環 心臓 心筋 MMVD 心不全",
 "皮膚・耳":"皮膚 耳科 外耳 膿皮症", "歯科":"歯科 歯周 抜歯",
 "神経":"神経 てんかん", "内分泌":"内分泌 副腎 甲状腺 糖尿病",
 "消化器":"消化器 消化管 腸症 胆嚢 膵炎", "泌尿器":"泌尿 腎臓 尿道",
 "栄養":"栄養 食事療法 肥満", "看護・技術":"看護 保定 採血",
 "院内教育・経営":"新人教育 病院経営 接遇", "猫":"猫 feline",
}
PREFS = ["東京都","大阪府","京都府","神奈川県","愛知県","兵庫県","埼玉県","千葉県","北海道",
         "福岡県","宮崎県","静岡県","茨城県","栃木県","群馬県","長野県","岡山県","広島県"]

def date(y,m,d):
    try: return datetime.date(int(y),int(m),int(d)).isoformat()
    except (ValueError,TypeError): return None

def year_in(text):
    m=re.search(r"(20\d{2})\s*年|(?:^|\s)(20\d{2})\s+セミナー",text)
    return int(m.group(1) or m.group(2)) if m else None

def event_date(text,year=None):
    m=YMD.search(text)
    if m: return date(*m.groups())
    m=MONTH_DAY.search(text)
    return date(year,*m.groups()) if m and year else None

def event(title,when,url,page,body="",organizer=None):
    s=unicodedata.normalize("NFKC",title).lower()
    topics=[k for k,words in TOPIC_HINTS.items() if k in TOPICS and any(w.lower() in s for w in words.split())][:2]
    aud=[]
    if "獣医師" in body: aud.append("獣医師")
    if "動物看護師" in body: aud.append("動物看護師")
    if "獣医学生" in body: aud.append("学生")
    if "一般すべて" in body: aud.append("一般")
    if "動物病院関係者" in body: aud.append("動物病院スタッフ")
    fmt=None
    combined=title+" "+body
    if re.search("ハイブリッド|現地.*オンライン",combined): fmt="ハイブリッド"
    elif re.search("オンデマンド|アーカイブ|ウェブ受講|録画配信",combined): fmt="オンデマンド"
    elif re.search("オンライン|ライブ配信|Zoom",combined,re.I): fmt="ライブ配信"
    elif re.search("会場|実習|東京|大阪",combined): fmt="現地"
    pref=next((p for p in PREFS if p in body),None) if fmt not in ("ライブ配信","オンデマンド") else None
    if not pref and fmt=="現地":
        for label,full in (("東京","東京都"),("大阪","大阪府"),("京都","京都府"),("宮崎","宮崎県")):
            if label in body: pref=full; break
    tm=re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)\s*[〜~～－―-]\s*([01]?\d|2[0-3]):([0-5]\d)",body)
    price=None; free=None
    for line in body.splitlines():
        if re.search(r"(参加費|受講料|料金|受講費)[：: ]",line) and len(line)<160:
            price=line.strip()[:120];free=True if "無料" in line else None;break
    status=STATUS.search(body)
    return dict(title=title.strip(),start_date=when,end_date=None,
        start_time=f"{int(tm.group(1)):02d}:{tm.group(2)}" if tm else None,
        end_time=f"{int(tm.group(3)):02d}:{tm.group(4)}" if tm else None,
        format=fmt,venue=None,prefecture=pref,audience=aud,topics=topics,
        price=price,is_free=free,status=status.group(0) if status else None,
        deadline=None,organizer=organizer,url=url or page,evidence=title.strip())

def linked(line):
    m=LINK.match(line)
    return (m.group(1).strip(),m.group(2).strip()) if m else None

def jaha(text,page,today):
    head=re.search(r"(20\d{2})年\s*(\d{1,2})月",text)
    if not head:return []
    year,month=map(int,head.groups())
    lines=text.splitlines()
    markers=[(i,m) for i,line in enumerate(lines) if (m:=DAY.fullmatch(line))]
    raw=[]
    for n,(i,m) in enumerate(markers):
        if int(m.group(1))!=month:continue
        when=date(year,month,m.group(2))
        if not when:continue
        block=lines[i+1:markers[n+1][0] if n+1<len(markers) else len(lines)]
        for j,line in enumerate(block):
            item=linked(line)
            if not item:continue
            title,url=item
            if len(title)<6 or title in ("詳細","MAP","前月","次月","申込") or "/seminar-calendar" in url:continue
            nearby="\n".join(block[max(0,j-3):min(len(block),j+4)])
            record=event(title,when,url,page,nearby,"JAHA")
            after=block[j+1:j+4]
            if record["format"] not in ("ライブ配信","オンデマンド"):
                venues=[x.strip() for x in after if x.strip() and not STATUS.fullmatch(x)
                        and not re.fullmatch(r".{2,3}[都府県]",x) and
                        not re.search("詳細|MAP|<https?://",x)]
                if venues:record["venue"]=venues[0][:120]
            raw.append(record)
    # Link and title repeated on consecutive dates represent one multi-day seminar.
    groups={}
    for e in raw: groups.setdefault((norm(e["title"]),e["url"]),[]).append(e)
    out=[]
    for group in groups.values():
        prev=None
        for e in sorted(group,key=lambda x:x["start_date"]):
            if prev and datetime.date.fromisoformat(e["start_date"]) <= datetime.date.fromisoformat(prev["end_date"] or prev["start_date"])+datetime.timedelta(days=1):
                if e["start_date"]>(prev["end_date"] or prev["start_date"]):prev["end_date"]=e["start_date"]
            else:
                prev=e
                out.append(e)
    return out

def gakusai(text,page,today):
    year=year_in(text)
    if not year:return []
    lines=text.splitlines()
    heads=[i for i,line in enumerate(lines) if re.match(r"^(?:No\.\s*\d+|MS\s*\d+)\b",line)]
    out=[]
    for n,i in enumerate(heads):
        block=lines[i:heads[n+1] if n+1<len(heads) else min(len(lines),i+14)]
        title=re.sub(r"^(?:No\.\s*\d+|MS\s*\d+)\s*","",block[0])
        title=re.sub(r"<https?://[^>]+>|[»>]\s*詳細はこちら.*","",title).strip()
        if len(title)<6:continue
        detail=next((p[1] for line in block[:4] if (p:=linked(line)) and "詳細はこちら" in p[0]),None)
        date_line=next((line for line in block[1:7] if MONTH_DAY.search(line)),None)
        if not date_line:continue
        for section in re.split(r"[｜|]",date_line):
            if "ウェブ受講" in section or "オンデマンド" in section:continue
            m=MONTH_DAY.search(section)
            if not m:continue
            when=date(year,*m.groups())
            if when:out.append(event(title,when,detail,page,section,"学際企画"))
    return out

def feed(text,page,today):
    out=[]
    for block in re.split(r"(?m)^=====\s*$",text):
        title=re.search(r"(?m)^記事タイトル:\s*(.+)$",block)
        link=re.search(r"(?m)^記事URL:\s*<(https?://[^>]+)>",block)
        if not title or not link:continue
        t=title.group(1).strip()
        if not re.search(r"セミナー|ライブ|講習|学会|実習|ウェビナー|勉強会|講演|講座|腫瘍|内科|外科|看護",t):continue
        # The article's publication date must not be mistaken for an event date.
        body=re.sub(r"(?m)^公開日:.*$","",block)
        out.append(event(t,event_date(body,year_in(body)),link.group(1),page,body[:2500],"VETS TECH"))
    return out

def lifetail(text,page,today):
    lines=text.splitlines();out=[]
    for i,line in enumerate(lines):
        item=linked(line)
        if not item:continue
        title,url=item
        if len(title)<8 or re.search("申込|詳細|一覧|ログイン|マイページ|メニュー|会員|もっと見る|カテゴリ",title):continue
        if not re.search("セミナー|講座|講習|実習|学会|獣医|犬|猫|内科|外科|麻酔|看護|腹腔|画像|臨床|病理|救急",title):continue
        near="\n".join(lines[max(0,i-2):min(len(lines),i+5)])
        out.append(event(title,event_date(near,year_in(near)),url,page,near,"Life&Tail"))
    return out

def extract_free(source_name,page_url,hint,text,today,stats):
    name=source_name.lower().replace("&","")
    if "jaha" in name or "日本動物病院協会" in name: raw=jaha(text,page_url,today)
    elif "学際" in name: raw=gakusai(text,page_url,today)
    elif "vets tech" in name or "vetstech" in name: raw=feed(text,page_url,today)
    elif "lifetail" in name: raw=lifetail(text,page_url,today)
    else: raw=[]
    records=validate(raw,text,page_url,today,stats)
    for e in records:
        if not e["start_date"] or e["url_is_page"]:e["verified"]=False
    stats["free_extracted"]=stats.get("free_extracted",0)+len(records)
    return records
