"""
Pop-Up: source configuration.
Add/remove feeds here. Each feed is tagged with a category so the
pipeline knows how to bucket it. sub_tag is optional (e.g. cricket vs football).
"""

FEEDS = [
    # ---------------- POLITICS (India) ----------------
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms", "category": "politics", "sub_tag": "india", "source": "Times of India"},
    {"url": "https://www.ndtv.com/rss/india", "category": "politics", "sub_tag": "india", "source": "NDTV"},
    {"url": "https://www.thehindu.com/news/national/feeder/default.rss", "category": "politics", "sub_tag": "india", "source": "The Hindu"},

    # ---------------- POLITICS (Global) ----------------
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "politics", "sub_tag": "global", "source": "BBC World"},
    {"url": "https://feeds.reuters.com/reuters/worldNews", "category": "politics", "sub_tag": "global", "source": "Reuters World"},

    # ---------------- ECONOMY / BUSINESS ----------------
    {"url": "https://www.livemint.com/rss/money", "category": "economy", "sub_tag": "india", "source": "Livemint"},
    {"url": "https://feeds.reuters.com/reuters/businessNews", "category": "economy", "sub_tag": "global", "source": "Reuters Business"},

    # ---------------- SPORTS: CRICKET ----------------
    {"url": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml", "category": "sports", "sub_tag": "cricket", "source": "ESPN Cricinfo"},

    # ---------------- SPORTS: FOOTBALL ----------------
    {"url": "https://www.espn.com/espn/rss/soccer/news", "category": "sports", "sub_tag": "football", "source": "ESPN Football"},

    # ---------------- SPORTS: OTHER ----------------
    {"url": "https://www.espn.com/espn/rss/news", "category": "sports", "sub_tag": "other", "source": "ESPN"},

    # ---------------- ENTERTAINMENT: BOLLYWOOD ----------------
    {"url": "https://www.bollywoodhungama.com/rss/news.xml", "category": "entertainment", "sub_tag": "bollywood", "source": "Bollywood Hungama"},

    # ---------------- ENTERTAINMENT: HOLLYWOOD / OTT ----------------
    {"url": "https://variety.com/feed/", "category": "entertainment", "sub_tag": "hollywood", "source": "Variety"},
    {"url": "https://www.hollywoodreporter.com/feed/", "category": "entertainment", "sub_tag": "hollywood", "source": "Hollywood Reporter"},

    # ---------------- TECH ----------------
    {"url": "https://techcrunch.com/feed/", "category": "tech", "sub_tag": "global", "source": "TechCrunch"},

    # ---------------- GLOBAL MAJORS (cross-cutting, catch-all) ----------------
    {"url": "https://feeds.bbci.co.uk/news/rss.xml", "category": "global", "sub_tag": "general", "source": "BBC Top Stories"},

    # ---------------- GOOGLE NEWS TOPIC SEARCH ----------------
    # Unlike the fixed single-outlet feeds above, these aggregate across many
    # outlets per query - genuinely broadens source diversity, which directly
    # helps the corroboration-based ranking in pipeline.py (more independent
    # sources = stronger signal a story actually matters). Still text-only
    # RSS under the hood, still no social-media trending signal - see the
    # README's honest source-comparison table for what this doesn't cover.
    {"url": "https://news.google.com/rss/search?q=india+politics&hl=en-IN&gl=IN&ceid=IN:en", "category": "politics", "sub_tag": "india", "source": "Google News: India politics"},
    {"url": "https://news.google.com/rss/search?q=world+news&hl=en-IN&gl=IN&ceid=IN:en", "category": "global", "sub_tag": "general", "source": "Google News: World"},
    {"url": "https://news.google.com/rss/search?q=football&hl=en-IN&gl=IN&ceid=IN:en", "category": "sports", "sub_tag": "football", "source": "Google News: Football"},
    {"url": "https://news.google.com/rss/search?q=cricket&hl=en-IN&gl=IN&ceid=IN:en", "category": "sports", "sub_tag": "cricket", "source": "Google News: Cricket"},
    {"url": "https://news.google.com/rss/search?q=bollywood&hl=en-IN&gl=IN&ceid=IN:en", "category": "entertainment", "sub_tag": "bollywood", "source": "Google News: Bollywood"},
    {"url": "https://news.google.com/rss/search?q=hollywood+OR+streaming&hl=en-IN&gl=IN&ceid=IN:en", "category": "entertainment", "sub_tag": "hollywood", "source": "Google News: Hollywood/OTT"},
]

# How many items to keep per run
MUST_KNOW_COUNT = 5          # cross-category, high-consensus stories
PERSONALIZED_COUNT_PER_CAT = 3  # per category, for the "worth knowing" tier

# Card generation model (Gemini free-tier model name)
# Using the "-latest" alias rather than a dated model name (e.g. gemini-2.0-flash)
# since Google has been retiring dated model versions on a few-month cycle in 2026 -
# the alias auto-points to Google's current recommended flash model.
GEMINI_MODEL = "gemini-flash-latest"

# Output paths. The pipeline auto-publishes directly - no mandatory human
# review gate, since that requires daily availability that isn't realistic.
# A copy is also written to DRAFT_PATH so the optional Review page (see
# pages/Review.py) has something to tweak on days you actually have time to
# look, without ever blocking the daily publish if you don't.
PUBLISHED_PATH = "data/latest.json"
DRAFT_PATH = "data/draft.json"
OUTPUT_PATH = PUBLISHED_PATH  # pipeline.py writes the live file directly
