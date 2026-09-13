"""
Turns a raw RSS item into a Pop-Up "card": a punchy headline + a 2-3 line
plain-language explainer, using Gemini's free-tier API.

IMPORTANT: We only ever feed the model the article's own title + raw summary.
We never ask it to recall facts from its own training data about "what
happened" - that's how you get hallucinated scores/numbers. It only rewrites
what's given to it.
"""

import os
import json
import re
import requests
from config import GEMINI_MODEL

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
# NOTE: current Gemini API keys (the "AQ." format Google moved to in 2026)
# must be sent as a header, not a ?key= query param - the old query-param
# style silently fails auth for these newer keys.
GEMINI_HEADERS = {"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY}

SYSTEM_INSTRUCTION = """You are a copy editor for "Pop-Up", a daily briefing that helps people
sound informed at the office or in college. Rewrite the given article title
and summary into a short card, IN YOUR OWN WORDS, using ONLY the facts
provided - do not add any fact, name, number, or date that isn't in the
source text. If the source is too thin to summarize meaningfully, say so.

Return STRICT JSON only, no markdown fences, no preamble, in this exact shape:
{"headline": "...", "explainer": "...", "confident": true}

Rules:
- headline: max 12 words, plain language, no clickbait, no punctuation tricks
- explainer: 30-50 words exactly, what happened + why it matters, written for
  someone with zero context. Do not quote the source verbatim - full rewrite.
  Crisp and complete within that range - not a fragment, not padded.
- confident: false if the source text was too short/vague to summarize safely
"""


def _strip_html(text):
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _trim_to_words(text, max_words=55):
    """Safety net - if the model ignores the 30-50 word instruction, trim
    rather than publish something bloated. Cuts at the last full sentence
    that fits, falling back to a hard word cut if there's no good sentence break."""
    words = text.split()
    if len(words) <= max_words:
        return text
    truncated = " ".join(words[:max_words])
    last_period = truncated.rfind(".")
    if last_period > len(truncated) * 0.5:  # only use it if it's not too early
        return truncated[:last_period + 1]
    return truncated.rstrip(",;: ") + "..."


def summarize_item(item):
    """
    item: dict with 'title' and 'raw_summary' (raw HTML allowed).
    Returns item with 'headline' and 'explainer' added, or None if the
    API call fails / response can't be parsed (fail closed, don't publish junk).
    """
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Get a free key at https://aistudio.google.com/apikey "
            "and set it as an environment variable / GitHub Actions secret."
        )

    clean_summary = _strip_html(item["raw_summary"])[:1200]  # keep prompt small
    user_content = f"Title: {item['title']}\nSummary: {clean_summary}"

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": user_content}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 500},
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, headers=GEMINI_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Guard against accidental markdown fences
        text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
        parsed = json.loads(text)
    except Exception as e:
        print(f"[warn] summarize failed for '{item['title'][:60]}': {e}")
        return None

    if not parsed.get("confident", True):
        return None

    item["headline"] = parsed.get("headline", item["title"])[:120]
    item["explainer"] = _trim_to_words(parsed.get("explainer", ""), max_words=55)
    return item


def summarize_batch(items):
    out = []
    for item in items:
        result = summarize_item(item)
        if result:
            out.append(result)
    print(f"[summarize] {len(out)}/{len(items)} items summarized successfully")
    return out


RANK_SYSTEM_INSTRUCTION = """You are helping pick which of several news headlines, all
already confirmed to be about similarly-sized stories (same number of
sources covering each), is most likely to come up in general conversation
today - broad relevance to an average person, not niche interest.

You are given ONLY headlines - no article text. Do not invent facts about
any of them, do not assume details not in the headline itself. Just judge
which headline, taken at face value, sounds most broadly significant.

Return STRICT JSON only, no markdown fences, no preamble:
{"most_significant_index": 0}
where the index refers to the 0-based position in the list given.
"""


def rank_headlines_by_significance(headlines):
    """
    headlines: list of strings, already pre-filtered to similar corroboration
    counts (this only breaks ties, it doesn't override corroboration - see
    pipeline.py). Returns the index of the most significant one, or 0 (first/
    most recent) on any failure - fails toward the existing recency-based
    order rather than blocking the pipeline.
    """
    if len(headlines) <= 1:
        return 0
    if not GEMINI_API_KEY:
        return 0

    numbered = "\n".join(f"{i}. {h}" for i, h in enumerate(headlines))
    payload = {
        "system_instruction": {"parts": [{"text": RANK_SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": numbered}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 50},
    }
    try:
        resp = requests.post(GEMINI_URL, json=payload, headers=GEMINI_HEADERS, timeout=15)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = re.sub(r"^```json\s*|\s*```$", "", text)
        parsed = json.loads(text)
        idx = int(parsed.get("most_significant_index", 0))
        return idx if 0 <= idx < len(headlines) else 0
    except Exception as e:
        print(f"[warn] headline ranking failed, falling back to recency order: {e}")
        return 0


if __name__ == "__main__":
    sample = {
        "title": "India beat Australia in thrilling series decider",
        "raw_summary": "India chased down 267 with two balls to spare to win the five-match series 3-2 after a middle-order collapse threatened the run chase.",
        "category": "sports", "sub_tag": "cricket", "source": "Test",
        "link": "#", "published": None,
    }
    print(summarize_item(sample))
