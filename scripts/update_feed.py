#!/usr/bin/env python3
"""Fetch The Guardian corrections RSS metadata.

Unreviewed feed entries are never labeled as verified false reports.
"""
import argparse
import datetime as dt
import email.utils
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.json"
RSS_URL = "https://www.theguardian.com/theguardian/series/corrections-and-clarifications/rss"

def parse_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    entries = []
    for item in root.findall(".//channel/item"):
        def field(name):
            return (item.findtext(name) or "").strip()
        link = field("link")
        if not re.match(r"^https://www\.theguardian\.com/(?:news|theguardian)/\d{4}/", link):
            continue
        headline = field("title") or "Corrections and clarifications"
        if not ("correction" in headline.lower() or "clarification" in headline.lower() or "correction" in link.lower()):
            continue
        try:
            date = email.utils.parsedate_to_datetime(field("pubDate")).date().isoformat()
        except (TypeError, ValueError, OverflowError, AttributeError):
            continue
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", link.split("theguardian.com/")[-1]).strip("-")
        entries.append({
            "id": "rss-" + slug,
            "title": "새로운 정정·해명 공지 · " + date,
            "before": "자동 수집된 공지입니다. 원보도를 확인하지 않았습니다.",
            "after": "정정문의 세부 내용을 공식 원문에서 확인하세요.",
            "summary": "공식 정정·해명 공지를 수집했습니다. 세부 사실관계는 아직 검증되지 않았습니다.",
            "category": "기타", "country": "영국", "publisher": "The Guardian",
            "type": "정정 공지 · 미검토", "date": date, "originalDate": "확인 전",
            "icon": "🗞️", "tone": "#f0f0e9", "titleOriginal": headline,
            "source": link, "sourceLabel": "정정 공지 원문",
            "originalUrl": None, "confirmed": "정정란 공지 게재(세부 내용 미검토)",
            "reviewStatus": "unreviewed",
            "events": [{"date": date, "title": "정정·해명 공지 등록",
                        "desc": "RSS로 발견한 공지입니다. 최초 기사와의 대조는 진행되지 않았습니다.",
                        "url": link, "label": "공식 공지 보기"}]
        })
    return sorted({x["id"]: x for x in entries}.values(), key=lambda x: x["date"], reverse=True)[:40]

def refresh(xml_bytes=None):
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if xml_bytes is None:
        req = urllib.request.Request(RSS_URL, headers={
            "User-Agent": "OboArchive/0.4 (https://github.com/ghlee6-wq/obo-archive)",
            "Accept": "application/rss+xml,application/xml,text/xml;q=0.9"
        })
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status != 200:
                raise ValueError("RSS HTTP " + str(response.status))
            xml_bytes = response.read(1_500_001)
    if len(xml_bytes) > 1_500_000:
        raise ValueError("RSS response too large")
    records = parse_feed(xml_bytes)
    if not records:
        raise ValueError("No relevant RSS records found; old data retained")
    verified_urls = {r.get("source") for r in data["verified"]}
    records = [r for r in records if r["source"] not in verified_urls]
    existing = {r["id"]: r for r in data.get("feed_items", [])
                if r.get("id") and r.get("reviewStatus") == "unreviewed"}
    # Prevent no-op commits and unnecessary Netlify builds every six hours.
    if not any(r["id"] not in existing for r in records):
        return {"verified": len(data["verified"]), "discovered": len(existing), "unchanged": True}
    existing.update({r["id"]: r for r in records})
    data["feed_items"] = sorted(existing.values(), key=lambda r: (r.get("date", ""), r["id"]), reverse=True)[:300]
    data["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    data["sync_status"] = "ok"
    fd, temp_path = tempfile.mkstemp(prefix=".data-", suffix=".json", dir=ROOT)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    os.replace(temp_path, DATA)
    return {"verified": len(data["verified"]), "discovered": len(data["feed_items"]), "updated_at": data["updated_at"]}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", help="Local fixture XML for testing")
    args = parser.parse_args()
    try:
        xml = Path(args.fixture).read_bytes() if args.fixture else None
        print(json.dumps({"ok": True, **refresh(xml)}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
