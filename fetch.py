"""
Pulls entries from every feed in config.FEEDS and normalizes them
into a flat list of dicts: title, summary, link, published, category, sub_tag, source
"""

import feedparser
from datetime import datetime, timedelta, timezone
from config import FEEDS


def _parse_time(entry):
    """Best-effort parse of the entry's published time -> aware datetime (UTC)."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def fetch_all(hours_lookback=24):
    """
    Fetch every configured feed, keep only entries published within
    `hours_lookback` hours, and return a flat normalized list.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)
    items = []

    for feed_cfg in FEEDS:
        try:
            parsed = feedparser.parse(feed_cfg["url"])
        except Exception as e:
            print(f"[warn] failed to fetch {feed_cfg['url']}: {e}")
            continue

        for entry in parsed.entries:
            published = _parse_time(entry)
            # If we can't determine time, include it anyway (better to over-include
            # than silently drop a real story) but flag it.
            if published and published < cutoff:
                continue

            items.append({
                "title": entry.get("title", "").strip(),
                "raw_summary": entry.get("summary", entry.get("description", "")).strip(),
                "link": entry.get("link", ""),
                "published": published.isoformat() if published else None,
                "category": feed_cfg["category"],
                "sub_tag": feed_cfg["sub_tag"],
                "source": feed_cfg["source"],
            })

    print(f"[fetch] collected {len(items)} raw items from {len(FEEDS)} feeds")
    return items


if __name__ == "__main__":
    for item in fetch_all()[:5]:
        print(item["category"], "-", item["title"])
