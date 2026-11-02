#!/usr/bin/env python3
"""Discover *candidate* Korean press corrections using public RSS metadata.

Strictly metadata-only: no article body, images or AI interpretation.
Never upgrade discovery entries to "verified" automatically.
The source site / court decision must be checked before claiming an actual false report.
"""
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.json"
MAX_BYTES = 3_000_000
MAX_KOREAN = 900

# Sources are publicly advertised RSS endpoints; check each publisher's terms
# before expanding beyond the current noncommercial prototype.
DIRECT_FEEDS = [
    ("연합뉴스", "https://www.yna.co.kr/rss/news.xml"),
    ("동아일보", "https://rss.donga.com/total.xml"),
    ("경향신문", "https://www.khan.co.kr/rss/rssdata/total_news.xml"),
    ("국민일보", "https://www.kmib.co.kr/rss/data/kmibRssAll.xml"),
    ("한겨레", "https://www.hani.co.kr/rss/"),
    ("조선일보", "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("매일경제", "https://www.mk.co.kr/rss/30000001/"),
    ("노컷뉴스", "https://rss.nocutnews.co.kr/news/news.xml"),
    ("뉴시스", "https://www.newsis.com/RSS/sokbo.xml"),
    ("서울신문", "https://www.seoul.co.kr/xml/rss/google_plan.xml"),
    ("프레시안", "https://www.pressian.com/api/v3/site/rss/news"),
    ("한국경제", "https://www.hankyung.com/feed/all-news"),
    ("이투데이", "https://rss.etoday.co.kr/eto/etoday_news_all.xml"),
    ("파이낸셜뉴스", "https://www.fnnews.com/rss/r20/fn_realnews_all.xml"),
    ("미디어오늘", "https://www.mediatoday.co.kr/rss/allArticle.xml"),
    ("오마이뉴스", "https://rss.ohmynews.com/rss/ohmynews.xml"),
]
# Search RSS broadens discovery beyond the most recent 20–100 items in direct feeds.
# Titles are still subject to the exact-title filter below.
SEARCHES = [
    "intitle:바로잡습니다 when:2y",
    "intitle:정정보도 when:2y",
    "intitle:정정합니다 when:2y",
    '"[바로잡습니다]" "조선일보" when:2y',
    '"[정정보도]" "매일경제" when:2y',
    '"[정정보도]" "국민일보" when:2y',
    '"바로잡습니다" "동아일보" when:2y',
    '"정정보도" "노컷뉴스" when:2y',
]
# Historical correction notices are indexed once, not fetched on each 6-hour sync.
BACKFILL_QUERIES = [
    f"intitle:{word} after:{year}-01-01 before:{year+1}-01-01"
    for year in (2022, 2023, 2024, 2025)
    for word in ("바로잡습니다", "정정보도", "정정합니다")
]
TITLE_START = re.compile(
    r"^\s*(?:[\[【(]\s*)?"
    r"(?:바로잡습니다|정정보도|정정\s*및\s*반론보도|정정합니다|정정보도문|기사\s*정정)"
    r"(?:[\]】)\s:\-｜]|$)",
    re.I,
)
MIN_DATE = dt.date(2022, 1, 1)

def get_url(url):
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS is accepted")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; OboArchive/0.6; news correction metadata index)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=13) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError("Oversized feed")
    return body

def local_name(tag):
    return tag.rsplit("}", 1)[-1]

def subtext(element, name):
    for child in element:
        if local_name(child.tag) == name:
            return "".join(child.itertext()).strip()
    return ""

def rss_entries(xml_bytes):
    """Parse RSS or Atom with no remote entity expansion or XML extensions."""
    root = ET.fromstring(xml_bytes)
    entries = []
    for item in root.iter():
        if local_name(item.tag) not in ("item", "entry"):
            continue
        title = html.unescape(subtext(item, "title")).strip()
        link = subtext(item, "link")
        if not link:
            for child in item:
                if local_name(child.tag) == "link":
                    link = child.get("href", "")
                    if link:
                        break
        date_text = (subtext(item, "pubDate") or subtext(item, "published")
                     or subtext(item, "updated"))
        source = subtext(item, "source")
        entries.append({"title": title, "link": link.strip(), "date_text": date_text, "source": source})
    return entries

def parse_date(raw):
    if not raw:
        return None
    try:
        value = email.utils.parsedate_to_datetime(raw)
        return value.date()
    except (ValueError, TypeError, OverflowError):
        pass
    try:
        return dt.date.fromisoformat(raw[:10])
    except ValueError:
        return None

def normalize_title(raw):
    # Google News appends " - Publisher" to some RSS titles.
    value = re.sub(r"\s+", " ", html.unescape(raw)).strip()
    return value[:260]

def accepted(record):
    title = normalize_title(record.get("title", ""))
    if not TITLE_START.search(title):
        return False
    link = record.get("link", "")
    try:
        u = urllib.parse.urlparse(link)
        if u.scheme != "https" or not u.netloc or "@" in u.netloc:
            return False
    except ValueError:
        return False
    date = parse_date(record.get("date_text", ""))
    if not date or date < MIN_DATE or date > dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1):
        return False
    return True

def make_entry(rec, name, source_type):
    headline = normalize_title(rec["title"])
    date = parse_date(rec["date_text"]).isoformat()
    pub = html.unescape(rec.get("source") or "").strip() if source_type == "search" else name
    if not pub:
        pub = "국내 언론사 확인 전"
    # Hide the - publisher suffix only if supplied with the source.
    if headline.endswith(" - " + pub):
        headline = headline[:-(len(pub) + 3)].strip()
    key = f"{pub.lower()}|{headline.lower()}|{date}"
    identity = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    link = rec["link"].strip()
    is_original = urllib.parse.urlparse(link).hostname not in {"news.google.com"}
    return {
        "id": "kr-feed-" + identity,
        "title": headline,
        "titleOriginal": headline,
        "before": "아직 최초 보도를 대조하지 않았습니다.",
        "after": "정정·해명 공지인지 원문에서 직접 확인해야 합니다.",
        "summary": "국내 기사 제목에서 정정 공지로 보이는 항목을 자동 발견했습니다. 사실오류 여부, 정정 유형, 원보도 연결은 검토 전입니다.",
        "category": "기타",
        "country": "대한민국",
        "publisher": pub[:65],
        "type": "정정 공지 후보 · 미검토",
        "date": date,
        "originalDate": "확인 전",
        "icon": "📰",
        "tone": "#eff4ea",
        "source": link,
        "sourceLabel": "언론사 원문" if is_original else "뉴스 검색 경유",
        "originalUrl": None,
        "confirmed": "자동 발견 · 원문 검토 전",
        "reviewStatus": "unreviewed",
        "discoverySource": "국내 언론사 RSS" if source_type == "direct" else "Google 뉴스 검색 RSS",
        "events": [{"date": date, "title": "정정 보도로 보이는 제목 발견",
                    "desc": "자동 수집된 링크입니다. 정정 사실과 최초 기사를 검증하기 전입니다.",
                    "url": link, "label": "원문으로 이동"}],
    }

def discover(fetch=get_url, sources=None, searches=None):
    direct_sources = DIRECT_FEEDS if sources is None else sources
    queries = SEARCHES if searches is None else searches
    found, checked, succeeded, errors = [], 0, 0, []
    for name, url in direct_sources:
        checked += 1
        try:
            records = rss_entries(fetch(url))
            succeeded += 1
            found.extend(make_entry(a, name, "direct") for a in records if accepted(a))
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {str(exc)[:100]}")
    for query in queries:
        checked += 1
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
            "q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko",
        })
        try:
            records = rss_entries(fetch(url))
            succeeded += 1
            found.extend(make_entry(a, "Google News", "search") for a in records if accepted(a))
        except Exception as exc:
            errors.append(f"검색 {query[:25]}: {type(exc).__name__}: {str(exc)[:100]}")
    # Prefer publisher's direct link over search intermediaries on duplicates.
    unique = {}
    for item in found:
        key = item["id"]
        if key not in unique or (item["discoverySource"] == "국내 언론사 RSS" and
                                 unique[key]["discoverySource"] != "국내 언론사 RSS"):
            unique[key] = item
    return list(unique.values()), {"checked": checked, "success": succeeded, "errors": errors[:25]}

def refresh(fetch=get_url, sources=None, searches=None):
    data = json.loads(DATA.read_text(encoding="utf-8"))
    new_items, stats = discover(fetch, sources, searches)
    if sources is None and searches is None and not data.get("korean_backfill_completed_at"):
        backfill_items, backfill_stats = discover(fetch, [], BACKFILL_QUERIES)
        if backfill_stats["success"]:
            new_items.extend(backfill_items)
            data["korean_backfill_completed_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        stats["archive_queries_checked"] = backfill_stats["checked"]
        stats["archive_queries_reachable"] = backfill_stats["success"]
        stats["archive_candidates"] = len(backfill_items)
        stats["errors"].extend(backfill_stats["errors"][:10])
    if stats["success"] == 0:
        raise ValueError("All Korea feeds failed; preserve previous data")
    old = data.get("feed_items", [])
    keep_foreign = [x for x in old if x.get("country") != "대한민국"]
    old_korean = [x for x in old if x.get("country") == "대한민국" and x.get("reviewStatus") == "unreviewed"]
    verified_links = {x.get("source") for x in data.get("verified", [])}
    verified_links.update(x.get("originalUrl") for x in data.get("verified", []))
    unique = {x["id"]: x for x in old_korean if x.get("id")}
    for x in new_items:
        if x["source"] not in verified_links:
            unique[x["id"]] = x
    korean = sorted(unique.values(), key=lambda x: (x["date"], x["id"]), reverse=True)[:MAX_KOREAN]
    data["feed_items"] = korean + keep_foreign
    data["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    data["korean_sync"] = {
        "checked_at": data["updated_at"],
        "feeds_checked": stats["checked"],
        "feeds_reachable": stats["success"],
        "discovered_new": len(new_items),
        "total_korean_unreviewed": len(korean),
        "errors": stats["errors"],
    }
    fd, temp_path = tempfile.mkstemp(prefix=".kr-feed-", suffix=".json", dir=ROOT)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    os.replace(temp_path, DATA)
    return {
        "verified_korean": len([x for x in data.get("verified",[]) if x.get("country")=="대한민국"]),
        "korean_candidates": len(korean),
        **stats,
    }

if __name__ == "__main__":
    try:
        print(json.dumps({"ok": True, **refresh()}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
