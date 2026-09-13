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
from summarize import summarize_batch, rank_headlines_by_significance

CATEGORY_ORDER = ["politics", "sports", "entertainment", "economy", "tech", "global"]


def _is_similar(a, b, threshold=0.6):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold


def dedupe(items):
    """
    Drop near-duplicate headlines (same story picked up by multiple feeds),
    but keep count of how many raw items merged into each survivor - that
    count is a real "how many independent sources are covering this" signal,
    which is a much better proxy for "this actually matters" than recency
    alone. A story that's fresh but only covered by one obscure feed is
    probably niche; a story covered by 3+ independent feeds at once is
    probably genuinely big.
    """
    kept = []
    for item in items:
        match = next((k for k in kept if _is_similar(item["title"], k["title"])), None)
        if match:
            match["corroboration_count"] += 1
            match["corroborating_sources"].append(item.get("source"))
        else:
            item["corroboration_count"] = 1
            item["corroborating_sources"] = [item.get("source")]
            kept.append(item)
    print(f"[dedupe] {len(kept)}/{len(items)} unique stories after dedup")
    return kept


def group_by_category(items):
    grouped = {cat: [] for cat in CATEGORY_ORDER}
    for item in items:
        grouped.setdefault(item["category"], []).append(item)
    return grouped


def _rank_bucket(bucket):
    """
    Sort a category's candidates: most-corroborated first. Among items tied
    on corroboration count, ask Gemini to judge which headline sounds most
    broadly significant (headlines only - no fact invention, see
    summarize.rank_headlines_by_significance). Falls back to recency if
    that call fails or no API key is set - never blocks the pipeline.
    """
    by_corroboration = {}
    for item in bucket:
        by_corroboration.setdefault(item.get("corroboration_count", 1), []).append(item)

    ranked = []
    for count in sorted(by_corroboration.keys(), reverse=True):
        tied_group = sorted(by_corroboration[count], key=lambda i: i.get("published") or "", reverse=True)
        if len(tied_group) > 1:
            headlines = [i["title"] for i in tied_group]
            best_idx = rank_headlines_by_significance(headlines)
            tied_group.insert(0, tied_group.pop(best_idx))
        ranked.extend(tied_group)
    return ranked


def curate(items):
    """
    Split into:
      must_know    -> one strong story per category (in CATEGORY_ORDER), capped
                       at MUST_KNOW_COUNT, ranked by corroboration then recency -
                       NOT just "whichever published most recently."
      personalized -> next few stories per category, same ranking, capped at
                       PERSONALIZED_COUNT_PER_CAT.
    """
    grouped = group_by_category(items)
    for cat in grouped:
        grouped[cat] = _rank_bucket(grouped[cat])

    must_know = []
    for cat in CATEGORY_ORDER:
        if len(must_know) >= MUST_KNOW_COUNT:
            break
        bucket = grouped.get(cat, [])
        if bucket:
            must_know.append(bucket.pop(0))  # take the top-ranked, remove from pool

    personalized = []
    for cat in CATEGORY_ORDER:
        bucket = grouped.get(cat, [])
        personalized.extend(bucket[:PERSONALIZED_COUNT_PER_CAT])

    print(f"[curate] must_know={len(must_know)} personalized={len(personalized)}")
    for item in must_know:
        print(f"  [must-know] ({item.get('corroboration_count')} sources) {item['title'][:70]}")
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
        "corroboration_count": item.get("corroboration_count", 1),
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

    # Also keep a draft copy - same content, but this is what the optional
    # Review page edits/republishes from, kept separate so a manual edit
    # there doesn't get silently overwritten by re-running the pipeline.
    from config import DRAFT_PATH
    with open(DRAFT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[pipeline] auto-published to {OUTPUT_PATH} "
          f"({len(output['must_know'])} must-know, {len(output['personalized'])} personalized)")


if __name__ == "__main__":
    run()
