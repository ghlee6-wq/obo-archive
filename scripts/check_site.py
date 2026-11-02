#!/usr/bin/env python3
"""Audit the public Netlify site, using GitHub Actions' outbound networking.

This is diagnostic only. It does not change published content or claim
that the Netlify site is healthy when a request fails.
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

ORIGIN = "https://oboarchive.netlify.app"
RAW = "https://raw.githubusercontent.com/ghlee6-wq/obo-archive/main/data.json"
EXPECTED = json.loads((Path(__file__).resolve().parents[1] / "data.json").read_text(encoding="utf-8"))


def read(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "OboArchiveHealthAudit/1.0", "Cache-Control": "no-cache"}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return {
                "http": response.status,
                "body": response.read(2_000_000),
                "cors": response.headers.get("Access-Control-Allow-Origin"),
            }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"http": getattr(exc, "code", None), "error": str(exc)[:260]}


def audit():
    home = read(ORIGIN + "/?healthcheck=1")
    deployed = read(ORIGIN + "/data.json?healthcheck=1")
    raw = read(RAW + "?healthcheck=1")
    out = {
        "expected_last_change": EXPECTED.get("updated_at"),
        "expected_candidates": len(EXPECTED.get("feed_items", [])),
    }
    out["homepage"] = {
        "http": home.get("http"),
        "error": home.get("error"),
        "has_live_github_fetch": b"raw.githubusercontent.com/ghlee6-wq/obo-archive/main/data.json" in home.get("body", b""),
        "has_freshness_indicator": b'id="freshnessHeadline"' in home.get("body", b""),
    }
    for name, response in (("netlify_data", deployed), ("github_raw", raw)):
        rec = {"http": response.get("http"), "error": response.get("error")}
        if name == "github_raw":
            rec["cors_header"] = response.get("cors")
        if response.get("body"):
            try:
                body = json.loads(response["body"])
                rec["updated_at"] = body.get("updated_at")
                rec["candidates"] = len(body.get("feed_items", []))
                rec["matches_repo"] = (
                    body.get("updated_at") == EXPECTED.get("updated_at") and
                    len(body.get("feed_items", [])) == len(EXPECTED.get("feed_items", []))
                )
            except (ValueError, TypeError):
                rec["json_error"] = True
        out[name] = rec
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    if home.get("http") != 200:
        print("::warning::Netlify homepage HTTP request unsuccessful.")
    if not out["homepage"]["has_live_github_fetch"]:
        print("::warning::Netlify HTML still lacks the latest direct-GitHub data loader.")
    if out["netlify_data"].get("matches_repo") is False:
        print("::warning::Netlify packaged JSON is behind the GitHub repository.")
    if out["github_raw"].get("cors_header") not in ("*", ORIGIN):
        print("::warning::Raw GitHub CORS may block client-side cross-origin fetch.")


if __name__ == "__main__":
    audit()
