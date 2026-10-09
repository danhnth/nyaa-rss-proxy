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

## Backfilling old releases

RSS only sees the newest 75 per query. For older releases, run the manual
workflow Actions -> backfill-nyaa -> Run workflow with a `query` (or `all`
for every line in `queries.txt`) and `pages` (1-50, ~75 items each). It walks
the HTML search pages and commits `catalog-<slug>.json` in the same item
schema, so the Termux client eats it unchanged. Same 5 GB cap and
start-paused guards apply on the client.
