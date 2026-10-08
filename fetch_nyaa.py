#!/usr/bin/env python3
"""Fetch Nyaa RSS on GitHub runner (clean IP) and save one feed file per query.

Query source, first non-empty wins:
  1. NYAA_QUERIES env (comma- or newline-separated, e.g. from workflow_dispatch input)
  2. queries.txt in repo (one query per line, # = comment)
  3. Default: ["bang dream"]

Output: feed-<slug>.json per query, feed.json copy of the first query
(backward compatible), index.json listing all feeds. Stdlib only.
"""
import json
import os
import re
import sys
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

C = "2_0"
F = "0"
NYAA_NS = "https://nyaa.si/xmlns/nyaa"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def slugify(query: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
    return slug or "feed"


def load_queries() -> list:
    env = os.environ.get("NYAA_QUERIES", "").strip()
    if env:
        queries = [q.strip() for q in re.split(r"[,\n]", env) if q.strip()]
        if queries:
            return queries
    if os.path.exists("queries.txt"):
        with open("queries.txt", encoding="utf-8") as f:
            queries = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        if queries:
            return queries
    return ["bang dream"]


def text(el, name, ns=None):
    c = el.find(name, ns) if ns else el.find(name)
    return (c.text or "").strip() if c is not None and c.text else ""


def fetch_query(query: str) -> list:
    params = urllib.parse.urlencode({"page": "rss", "q": query, "c": C, "f": F})
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
        print(f"FETCH_FAILED [{query}]: {e}", file=sys.stderr)
        sys.exit(1)
    if code != 200:
        print(f"NYAA_HTTP_{code} [{query}]", file=sys.stderr)
        sys.exit(1)

    root = ET.fromstring(body)
    channel = root.find("channel")
    if channel is None:
        print(f"NO_CHANNEL [{query}]", file=sys.stderr)
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
    return items


def main():
    queries = load_queries()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    feeds = []
    for i, query in enumerate(queries):
        items = fetch_query(query)
        out = {
            "ok": True,
            "count": len(items),
            "query": query,
            "updated": now,
            "items": items,
        }
        fname = f"feed-{slugify(query)}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        if i == 0:
            with open("feed.json", "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=1)
        feeds.append({"query": query, "file": fname, "count": len(items)})
        print(f"wrote {fname} with {len(items)} items")
    with open("index.json", "w", encoding="utf-8") as f:
        json.dump({"ok": True, "updated": now, "feeds": feeds}, f, ensure_ascii=False, indent=1)
    print(f"wrote index.json with {len(feeds)} feeds")


if __name__ == "__main__":
    main()
