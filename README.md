# Pop-Up — Streamlit app

Since-we-last-met daily briefing: Politics, Sports, Entertainment, Economy, Tech, Global.

## How it works

```
RSS feeds (config.py)
   → fetch.py       pulls last-24h entries from every feed
   → pipeline.py     dedupes near-identical stories across feeds, tracking
                      how many independent sources covered each one
                      ("corroboration count") - then ranks must-know picks
                      by that count, not by which happened to be freshest.
                      Close ties get broken by a safe Gemini pass that only
                      judges headline significance, never invents facts.
   → summarize.py    rewrites each into a card via Gemini (free tier)
   → data/latest.json   auto-published immediately - no manual gate
   → data/draft.json    same content, kept separately as an optional
                         starting point if you ever want to tweak a day
                         via pages/Review.py (fully optional, never required)
   → app.py          Streamlit reads latest.json and renders the page
```

**Why corroboration instead of recency**: the earlier version picked
"must-know" stories by whichever was most recently published per category -
which meant a niche story that happened to publish 20 minutes ago could
outrank the actual big story of the day. Now, a story covered by 3
independent RSS feeds at once (a real signal people are actually talking
about it) beats a fresher but single-source story. This is genuinely
better automated judgment, not a cosmetic change - see the pipeline's test
suite reasoning in the code comments for the exact logic.

**Nothing here requires daily human attention.** The Review page exists for
days you *want* to spend 10 minutes swapping something out or adding a
story the feeds missed - not because the site needs it to function.

`app.py` is the entire app — Streamlit handles routing, rendering, and
serving. No separate Flask/gunicorn/server file needed for this version.

## Local setup

```bash
pip install -r requirements.txt

mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml and fill in a real GEMINI_API_KEY and any
# random string for COOKIES_PASSWORD

# Generate today's data once
python pipeline.py

# Run the app
streamlit run app.py
# opens at http://localhost:8501
```

## Deploying to Streamlit Community Cloud (free)

1. Push this folder to a GitHub repo (see below for exact commands).
2. Go to **share.streamlit.io** → log in with GitHub → **New app**.
3. Pick your repo, branch `main`, main file path `app.py`.
4. Before/after deploying, go to your app's **Settings → Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your-real-key"
   COOKIES_PASSWORD = "any-random-string"
   ```
   Never commit real secrets to the repo - this Secrets panel is the only
   place they should live for the hosted version.
5. Deploy. You'll get a URL like `https://your-app-name.streamlit.app`.

## Pushing to GitHub

```bash
cd popup-streamlit
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

`.streamlit/secrets.toml` is gitignored on purpose - only
`secrets.toml.example` (with placeholder values) gets committed.

## Keeping data fresh daily

`.github/workflows/daily.yml` runs the pipeline every day at 6:00 AM IST
and commits the fresh `data/latest.json` back to the repo. Add
`GEMINI_API_KEY` as a **GitHub Actions secret** too (Settings → Secrets and
variables → Actions) - this is separate from the Streamlit Cloud secret
above; both are needed since the pipeline (GitHub Actions) and the live
app (Streamlit Cloud) run in different places.

**Important**: Streamlit Community Cloud auto-redeploys whenever it detects
a new commit on your connected branch - so once GitHub Actions pushes the
daily data update, Streamlit Cloud picks it up automatically. No separate
deploy-hook step is needed here (unlike the earlier Render setup), which
is one of the nice things about this hosting choice.

## Checking your visitor/usage data

Go to your app's URL with `/Admin_Analytics` appended (Streamlit auto-adds
any file in `pages/` as a page, accessible from the sidebar or directly),
enter your `ADMIN_PASSWORD` (set in secrets - see above), and you'll see:

- Unique devices ever seen + total pageviews
- Visits by day (bar chart)
- What people actually click (read/unread, share, search used, wildcard,
  category changes)
- Category popularity across all saved preferences
- 👍 feedback totals per category
- Streak distribution (how many devices are at day-1 vs a real habit)

This is all real, logged data - not estimated or simulated. It's stored in
`data/events.jsonl` (append-only event log) and `data/users.json`
(per-device state), both already on your server. No external analytics
service, no cookies-consent-banner complexity, no data leaving your app.

**Important caveats, stated plainly:**
- "Unique devices" ≠ unique people. Same person on two browsers/phones
  counts twice; clearing cookies resets the count. Treat it as a solid
  proxy, not an exact headcount.
- Link clicks on "Read full story →" are **not tracked** - Streamlit's
  `st.link_button` opens a new tab natively without a server round-trip,
  so there's no reliable way to log that click server-side without
  injecting custom JavaScript (which Streamlit's sandboxing makes fragile
  across versions). Everything else (read-toggle, share, search, wildcard,
  category changes, feedback) *is* tracked, since those are real Streamlit
  button interactions.
- If you want peace of mind, don't skip setting `ADMIN_PASSWORD` - without
  it, the analytics page is unprotected and visible to anyone who finds
  the URL.
- **Complementary, not a replacement**: Streamlit Community Cloud's own
  dashboard (share.streamlit.io → your app → the small chart icon) shows
  basic traffic (viewer count trend) with zero setup - worth checking
  alongside this for a sanity-check cross-reference.

## Device-linked preferences (no accounts)

A real encrypted browser cookie (via `streamlit-cookies-manager`) stores a
random device ID. Preferences, streak, and read-story state are all saved
against that ID in `data/users.json` - same pattern as before, just wired
through Streamlit instead of Flask routes. Clearing cookies / switching
browsers resets it, same tradeoff as any device-linked (no login) system.

## Delight features included

- 🎈 Balloons + toast celebration every 7-day streak milestone
- 🔥 Native streak metric widget
- Freshness tags ("2h ago") computed from real publish timestamps
- One-time dismissable hint for first-time visitors explaining default picks
- `st.code()` share block has a built-in copy-to-clipboard button for free
- Search filters both must-know and personalized sections live
- 🎲 "Show me something outside my usual categories" - an opt-in wildcard
  story pulled from categories you haven't selected, for a bit of
  serendipity without forcing anything on you
- Custom favicon/app icon (`icon.png`, generated to match the brand)
- 👍 Lightweight per-category feedback on personalized stories - real
  signal saved to your device for future relevance (see note below on
  what this does and doesn't do yet)

## Habit-forming design - done honestly, not manipulatively

This app borrows structure from Nir Eyal's Hook Model (Trigger → Action →
Variable Reward → Investment), but deliberately avoids the manipulative
version of that framework:

- **Trigger**: the "since we last met" framing taps a real, specific
  concern (looking out of touch in a real conversation) - not a fabricated
  one.
- **Action**: zero friction to see today's content - no login, no gate,
  defaults shown immediately.
- **Variable reward**: real streak milestones (not fake progress bars),
  an opt-in wildcard story (genuine unpredictability, not manufactured
  FOMO), and real share (not a fake "X people shared this" counter -
  there's no fabricated social proof anywhere in this app).
- **Investment**: category picks, read history, and thumbs feedback are
  real inputs that make the app more tailored over time - not busywork
  designed purely to trigger sunk-cost attachment.

Explicitly **not** included, on purpose: fake urgency/scarcity, fabricated
"other people are reading this" counters, guilt-based copy ("don't lose
your streak!"), or infinite-scroll mechanics. The goal is a genuinely
useful daily habit, not an engagement-maximizing trap.

**Honest limitation**: the 👍 feedback is currently stored per-device but
not yet fed back into automatic story ranking - the pipeline that picks
tomorrow's stories doesn't read `users.json` yet. Wiring that up (e.g.
biasing category selection toward categories a device has upvoted more)
is a natural next step, not yet built.

## Where the content actually comes from - being honest about this

`config.py`'s `FEEDS` list is the entire source of raw material. It's RSS-based:
fixed feeds from specific outlets (Times of India, NDTV, ESPN Cricinfo, etc.)
plus Google News topic-search RSS (aggregates many outlets per query -
broader net than a single fixed feed, still text-only under the hood).

**What this setup can't see**: anything trending on social media before a
news outlet writes an article about it - which is often where pop-culture
and sports moments actually break first. Real alternatives exist, each with
a real tradeoff:

| Source | Cost | What it adds | Real catch |
|---|---|---|---|
| Google News topic RSS (included) | Free | Broader outlet coverage per topic | Still no social-buzz signal |
| Reddit hot posts | Free (basic read) | Genuine "people are discussing this" signal | Rate-limited without auth, skews to Reddit's demographic |
| NewsAPI/GNews | Free tier (~100 req/day) | Structured search | Hits rate limits fast at daily scale |
| Twitter/X API | Paid, no real free tier since 2023 | Best trending signal there is | Cost-prohibitive for a $0 project |
| Google Trends | Free | Good topic-level trend signal | Gives topics, not article content - needs pairing with another source |

Add more feeds any time by editing `config.py`'s `FEEDS` list - no other
code changes needed, the pipeline and frontend both key off `category`.

## Known limitations (being upfront, not hiding them)

- `data/users.json` is a flat file - fine at small scale, but concurrent
  writes from many simultaneous users has no locking. Move to a real DB
  (e.g. SQLite via `st.connection`) if this grows past casual/personal use.
- Streamlit Community Cloud's filesystem is not guaranteed persistent
  across redeploys/restarts in all cases - `data/users.json` (device
  preferences) could reset on a cold restart. This is a real constraint of
  the free tier; a proper production version would use an external DB
  (e.g. free-tier Supabase/Postgres) instead of a local JSON file.
- Dark/light theme is controlled by Streamlit's own native theme switcher
  (the ⋮ menu, top right) rather than a custom in-app toggle - this is
  simpler and more consistent with the platform, but preference isn't
  saved per-device the way the old custom Flask version did it.
