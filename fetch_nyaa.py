#!/usr/bin/env python3
"""Fetch Nyaa RSS on GitHub runner (IP sach) va luu feed.json. Chi dung stdlib."""
import json
import sys
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

QUERY = "bang dream"
C = "2_0"
F = "0"
NYAA_NS = "https://nyaa.si/xmlns/nyaa"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def text(el, name, ns=None):
    c = el.find(name, ns) if ns else el.find(name)
    return (c.text or "").strip() if c is not None and c.text else ""

def main():
    params = urllib.parse.urlencode({"page": "rss", "q": QUERY, "c": C, "f": F})
    url = f"https://nyaa.si/?{params}"
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code = r.status
            body = r.read()
    except Exception as e:
        print(f"FETCH_FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    if code != 200:
        print(f"NYAA_HTTP_{code}", file=sys.stderr)
        sys.exit(1)

    root = ET.fromstring(body)
    channel = root.find("channel")
    if channel is None:
        print("NO_CHANNEL", file=sys.stderr)
        sys.exit(1)

    ns = {"nyaa": NYAA_NS}
    items = []
    for it in channel.findall("item"):
        guid = text(it, "guid") or text(it, "link")
        items.append({
            "title": text(it, "title"),
            "link": text(it, "link"),
            "guid": guid,
            "pubDate": text(it, "pubDate"),
            "infoHash": text(it, "nyaa:infoHash", ns),
            "size": text(it, "nyaa:size", ns),
            "seeders": text(it, "nyaa:seeders", ns),
            "leechers": text(it, "nyaa:leechers", ns),
            "downloads": text(it, "nyaa:downloads", ns) or text(it, "nyaa:completed", ns),
            "category": text(it, "nyaa:category", ns),
        })

    out = {
        "ok": True,
        "count": len(items),
        "query": QUERY,
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "items": items,
    }
    with open("feed.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote feed.json with {len(items)} items")

if __name__ == "__main__":
    main()
