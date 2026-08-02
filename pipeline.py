"""
End-to-end daily pipeline:
  1. Fetch all RSS feeds (last 24h)
  2. Dedupe near-identical stories (same headline across sources)
  3. Pick a "must-know" tier (one strong story per category, capped)
  4. Pick a "personalized" tier (a few more per category)
  5. Summarize everything via Gemini
  6. Write data/latest.json in the shape the frontend expects

Run manually:      GEMINI_API_KEY=xxx python pipeline.py
Run on schedule:    see .github/workflows/daily.yml
"""

import json
import os
from datetime import datetime, timezone
from difflib import SequenceMatcher

from config import MUST_KNOW_COUNT, PERSONALIZED_COUNT_PER_CAT, OUTPUT_PATH
from fetch import fetch_all
from summarize import summarize_batch

CATEGORY_ORDER = ["politics", "sports", "entertainment", "economy", "tech", "global"]


def _is_similar(a, b, threshold=0.6):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold


def dedupe(items):
    """Drop near-duplicate headlines (same story picked up by multiple feeds)."""
    kept = []
    for item in items:
        if any(_is_similar(item["title"], k["title"]) for k in kept):
            continue
        kept.append(item)
    print(f"[dedupe] {len(kept)}/{len(items)} unique stories after dedup")
    return kept


def group_by_category(items):
    grouped = {cat: [] for cat in CATEGORY_ORDER}
    for item in items:
        grouped.setdefault(item["category"], []).append(item)
    return grouped


def curate(items):
    """
    Split into:
      must_know  -> one top story per category (in CATEGORY_ORDER), capped at MUST_KNOW_COUNT
      personalized -> next few stories per category, capped at PERSONALIZED_COUNT_PER_CAT
    Items are assumed already roughly time-sorted (most recent first) per category
    since RSS feeds return newest-first.
    """
    grouped = group_by_category(items)

    must_know = []
    for cat in CATEGORY_ORDER:
        if len(must_know) >= MUST_KNOW_COUNT:
            break
        bucket = grouped.get(cat, [])
        if bucket:
            must_know.append(bucket.pop(0))  # take the freshest, remove from pool

    personalized = []
    for cat in CATEGORY_ORDER:
        bucket = grouped.get(cat, [])
        personalized.extend(bucket[:PERSONALIZED_COUNT_PER_CAT])

    print(f"[curate] must_know={len(must_know)} personalized={len(personalized)}")
    return must_know, personalized


def to_card(item, is_must_know):
    return {
        "category": item["category"],
        "sub_tag": item.get("sub_tag"),
        "source": item.get("source"),
        "headline": item.get("headline", item["title"]),
        "explainer": item.get("explainer", ""),
        "link": item.get("link"),
        "published": item.get("published"),
        "must_know": is_must_know,
    }


def run():
    raw_items = fetch_all(hours_lookback=24)
    unique_items = dedupe(raw_items)
    must_know_raw, personalized_raw = curate(unique_items)

    print("[pipeline] summarizing must-know tier...")
    must_know_summarized = summarize_batch(must_know_raw)
    print("[pipeline] summarizing personalized tier...")
    personalized_summarized = summarize_batch(personalized_raw)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "must_know": [to_card(i, True) for i in must_know_summarized],
        "personalized": [to_card(i, False) for i in personalized_summarized],
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[pipeline] wrote {OUTPUT_PATH} "
          f"({len(output['must_know'])} must-know, {len(output['personalized'])} personalized)")


if __name__ == "__main__":
    run()
