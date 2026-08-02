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
]

# How many items to keep per run
MUST_KNOW_COUNT = 5          # cross-category, high-consensus stories
PERSONALIZED_COUNT_PER_CAT = 3  # per category, for the "worth knowing" tier

# Card generation model (Gemini free-tier model name)
# Using the "-latest" alias rather than a dated model name (e.g. gemini-2.0-flash)
# since Google has been retiring dated model versions on a few-month cycle in 2026 -
# the alias auto-points to Google's current recommended flash model.
GEMINI_MODEL = "gemini-flash-latest"

# Output path
OUTPUT_PATH = "data/latest.json"
