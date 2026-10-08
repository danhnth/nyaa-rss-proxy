# nyaa-rss-proxy — Nyaa RSS fetcher (GitHub Actions)

GitHub runners have clean IPs, so they fetch `nyaa.si` RSS directly and publish
static JSON. Termux phones pull the static files and never touch Nyaa.

## Adding a search query

Edit `queries.txt` (one query per line) and push. The next scheduled run
(every 12h) or manual run generates `feed-<slug>.json` for each query, plus
`index.json` listing all feeds. `feed.json` always mirrors the first query.

One-off test without commit: Actions -> fetch-nyaa -> Run workflow -> `queries`
(comma-separated, e.g. `umamusume, bang dream`).

Each feed holds up to 75 items (Nyaa's per-feed RSS limit).
