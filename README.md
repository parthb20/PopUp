# Pop-Up — Daily Cultural Literacy Digest

Since-we-last-met briefing across Politics, Sports, Entertainment, Economy, Tech, and Global majors.

## How it works

```
RSS feeds (config.py)
   → fetch.py       pulls last-24h entries from every feed
   → pipeline.py     dedupes near-identical stories, splits into
                      "must-know" (one big story per category) and
                      "personalized" (a few more per category)
   → summarize.py    rewrites each into a Pop-Up card via Gemini
                      (free tier) — only rewrites what's given, never
                      invents facts
   → data/latest.json   final output, served to the frontend
   → server.py       Flask app: serves public/index.html + /api/today
```

## Local setup

```bash
pip install -r requirements.txt

# Get a free Gemini API key: https://aistudio.google.com/apikey
# Keys now come in the newer "AQ.Ab..." format (Google's 2026 migration away
# from the older "AIzaSy..." format) - both are handled correctly here, the
# code sends it via the X-goog-api-key header either way.
# NEVER commit this key or paste it into chat/code - only set it as an env
# var locally, or as a GitHub Actions / hosting-provider secret.
export GEMINI_API_KEY="your-key-here"

# Run the pipeline once to generate today's data
python pipeline.py

# Serve the site
python server.py
# visit http://localhost:5000
```

## Automating the daily refresh

`.github/workflows/daily.yml` runs the pipeline every day at **6:00 AM IST**
(00:30 UTC) via GitHub Actions, and commits the fresh `data/latest.json`
back to the repo.

Setup:
1. Push this repo to GitHub.
2. Go to **Settings → Secrets and variables → Actions**.
3. Add a secret named `GEMINI_API_KEY` with your free Gemini key.
4. **Important for reliability**: also add a secret named `DEPLOY_HOOK_URL`
   pointing to your host's deploy-hook (Render/Railway: Settings → Deploy
   Hook → copy URL). Without this, the daily commit updates the *repo* but
   your *live* server may keep serving yesterday's data until it happens to
   redeploy for some other reason. With it, every daily run also triggers
   a fresh deploy automatically.
5. That's it — runs daily automatically. Trigger manually anytime from the
   **Actions** tab (`workflow_dispatch`).

## Hosting the site (free tier)

- **Render / Railway free tier**: point it at `server.py`, it'll serve the
  site + API together. Data updates whenever GitHub Actions pushes a new
  `data/latest.json` and you redeploy (or just have the host auto-redeploy
  on push).
- **Simpler alternative**: skip the Flask server entirely and have GitHub
  Actions push `data/latest.json` straight into a static hosting service
  (Vercel/Netlify), with `public/index.html` fetching `/data/latest.json`
  directly instead of `/api/today`. Fewer moving parts, still free.

## Editorial control (important)

The pipeline currently auto-picks "must-know" stories using a simple
recency-per-category rule. **Review `data/latest.json` daily** before
trusting it fully — swap in manual curation logic in `pipeline.py`'s
`curate()` function once you have a feel for what "actually worth knowing"
means day to day. The AI (Gemini) only rewrites text you already selected;
it does not decide what's important.

## Adding more sources or categories

Edit `config.py` — add a feed URL, category, and sub_tag. No other code
changes needed; the pipeline and frontend both key off `category`.

## Cost

- RSS: free
- Gemini free tier: free (rate-limited, fine at this scale)
- GitHub Actions: free (public repo) or free minutes allotment (private)
- Hosting: free tier on Render/Railway/Vercel/Netlify

Estimated monthly cost at MVP scale: **$0**.
