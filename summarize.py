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
- explainer: 2-3 sentences, what happened + why it matters, written for someone
  with zero context. Do not quote the source verbatim - full rewrite.
- confident: false if the source text was too short/vague to summarize safely
"""


def _strip_html(text):
    return re.sub(r"<[^>]+>", " ", text or "").strip()


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
    item["explainer"] = parsed.get("explainer", "")[:400]
    return item


def summarize_batch(items):
    out = []
    for item in items:
        result = summarize_item(item)
        if result:
            out.append(result)
    print(f"[summarize] {len(out)}/{len(items)} items summarized successfully")
    return out


if __name__ == "__main__":
    sample = {
        "title": "India beat Australia in thrilling series decider",
        "raw_summary": "India chased down 267 with two balls to spare to win the five-match series 3-2 after a middle-order collapse threatened the run chase.",
        "category": "sports", "sub_tag": "cricket", "source": "Test",
        "link": "#", "published": None,
    }
    print(summarize_item(sample))
