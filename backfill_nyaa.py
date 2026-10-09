#!/usr/bin/env python3
"""One-off backfill: walk Nyaa HTML search pages to collect old releases.

RSS only gives the newest 75 items per query, so this script paginates the
HTML search (which runners can reach) and saves a catalog-<slug>.json with
the same item schema as the feeds, so sync_nyaa.py eats it unchanged.

Config (env, also wired to workflow_dispatch inputs):
  NYAA_BACKFILL_QUERY  single query, or "all" = every line in queries.txt (default "bang dream")
  NYAA_BACKFILL_PAGES  max pages to walk, clamped 1..50 (default 10)

Stdlib only. Sleeps 2s between pages to avoid 429s.
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

C = "2_0"
F = "0"
PAGE_SLEEP = 2
MAX_PAGES = 50

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def slugify(query: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
    return slug or "catalog"


def load_targets() -> list:
    q = os.environ.get("NYAA_BACKFILL_QUERY", "").strip() or "bang dream"
    if q.lower() == "all":
        if os.path.exists("queries.txt"):
            with open("queries.txt", encoding="utf-8") as f:
                targets = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            if targets:
                return targets
        return ["bang dream"]
    return [q]


def max_pages() -> int:
    try:
        n = int(os.environ.get("NYAA_BACKFILL_PAGES", "10"))
    except ValueError:
        n = 10
    return max(1, min(MAX_PAGES, n))


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def parse_page(html: str) -> list:
    items = []
    for block in re.split(r"<tr\b", html)[1:]:
        m_mag = re.search(r"magnet:\?xt=urn:btih:([a-fA-F0-9]{40})", block)
        if not m_mag:
            continue
        m_view = re.search(r'href="/view/(\d+)"[^>]*>(.*?)</a>', block, re.S)
        if not m_view:
            continue
        info_hash = m_mag.group(1).lower()
        vid = m_view.group(1)
        title = strip_tags(m_view.group(2))
        m_size = re.search(r"([\d.,]+\s+[KMGT]?i?B)", block)
        size = m_size.group(1).strip() if m_size else ""
        nums = re.findall(r'<td class="text-center">\s*(\d+)\s*</td>', block)
        seeders = nums[0] if len(nums) > 0 else ""
        leechers = nums[1] if len(nums) > 1 else ""
        downloads = nums[2] if len(nums) > 2 else ""
        m_ts = re.search(r'data-timestamp="(\d+)"', block)
        pub = ""
        if m_ts:
            pub = datetime.datetime.fromtimestamp(
                int(m_ts.group(1)), tz=datetime.timezone.utc
            ).isoformat()
        link = f"https://nyaa.si/view/{vid}"
        items.append({
            "title": title,
            "link": link,
            "guid": link,
            "pubDate": pub,
            "infoHash": info_hash,
            "size": size,
            "seeders": seeders,
            "leechers": leechers,
            "downloads": downloads,
            "category": "",
        })
    return items


def fetch_html(query: str, page: int) -> str:
    params = urllib.parse.urlencode({"f": F, "c": C, "q": query, "p": page})
    url = f"https://nyaa.si/?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            print(f"NYAA_HTTP_{r.status} [{query}] p={page}", file=sys.stderr)
            sys.exit(1)
        return r.read().decode("utf-8", "replace")


def backfill(query: str, pages: int) -> dict:
    seen = set()
    items = []
    fetched = 0
    for p in range(1, pages + 1):
        if p > 1:
            time.sleep(PAGE_SLEEP)
        rows = parse_page(fetch_html(query, p))
        fetched = p
        fresh = [r for r in rows if r["infoHash"] not in seen]
        for r in fresh:
            seen.add(r["infoHash"])
        items.extend(fresh)
        print(f"[{query}] page {p}: {len(rows)} rows, {len(fresh)} new, total {len(items)}")
        if not rows:
            break
    return {"fetched": fetched, "items": items}


def main():
    pages = max_pages()
    for query in load_targets():
        result = backfill(query, pages)
        out = {
            "ok": True,
            "query": query,
            "pages_fetched": result["fetched"],
            "count": len(result["items"]),
            "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "items": result["items"],
        }
        fname = f"catalog-{slugify(query)}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f"wrote {fname} with {len(result['items'])} items")


if __name__ == "__main__":
    main()
