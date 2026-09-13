"""
Tiny device-linked storage layer. No accounts, no passwords - just a
random device_id stored in a cookie, mapped to preferences + streak in
a JSON file. Good enough for MVP scale; swap for a real DB later if
this needs to survive redeploys reliably or scale past a few thousand
users.
"""

import json
import os
from datetime import datetime, timezone, timedelta

STORE_PATH = "data/users.json"
IST = timezone(timedelta(hours=5, minutes=30))

DEFAULT_CATEGORIES = ["entertainment", "sports", "politics"]


def _default_user(today):
    return {
        "categories": DEFAULT_CATEGORIES,
        "onboarded": True,
        "streak": 1,
        "last_visit": today,
        "theme": "light",
        "read_links": [],
        "feedback": {},  # {category: {"up": n, "down": n}} - shapes future relevance
    }


def _load():
    if not os.path.exists(STORE_PATH):
        return {}
    try:
        with open(STORE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    os.makedirs(os.path.dirname(STORE_PATH) or ".", exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _today_ist():
    return datetime.now(IST).date().isoformat()


def get_or_create_user(device_id):
    """
    Returns the user record for this device, updating the daily streak
    as a side effect:
      - same day as last visit -> streak unchanged
      - exactly one day after last visit -> streak += 1
      - any bigger gap (or first-ever visit) -> streak resets to 1
    """
    data = _load()
    today = _today_ist()
    user = data.get(device_id)

    if user is None:
        user = _default_user(today)
    else:
        # backfill fields for records saved before theme/read_links existed
        user.setdefault("theme", "light")
        user.setdefault("read_links", [])
        user.setdefault("feedback", {})
        last_visit = user.get("last_visit")
        if last_visit != today:
            try:
                gap_days = (
                    datetime.fromisoformat(today) - datetime.fromisoformat(last_visit)
                ).days
            except Exception:
                gap_days = 999
            user["streak"] = user.get("streak", 0) + 1 if gap_days == 1 else 1
            user["last_visit"] = today

    data[device_id] = user
    _save(data)
    return user


def save_preferences(device_id, categories):
    data = _load()
    user = data.get(device_id) or get_or_create_user(device_id)
    user["categories"] = categories
    user["onboarded"] = True
    data[device_id] = user
    _save(data)
    return user


def save_theme(device_id, theme):
    if theme not in ("light", "dark"):
        theme = "light"
    data = _load()
    user = data.get(device_id) or get_or_create_user(device_id)
    user["theme"] = theme
    data[device_id] = user
    _save(data)
    return user


def toggle_read(device_id, link):
    """Add/remove a story link from this device's read-list. Returns the new read state (bool)."""
    data = _load()
    user = data.get(device_id) or get_or_create_user(device_id)
    read_links = set(user.get("read_links", []))
    if link in read_links:
        read_links.discard(link)
        now_read = False
    else:
        read_links.add(link)
        now_read = True
    user["read_links"] = list(read_links)
    data[device_id] = user
    _save(data)
    return now_read


def record_feedback(device_id, category, sentiment):
    """
    sentiment: 'up' or 'down'. Stored per-category, not per-article (articles
    rotate daily, category-level signal is what's actually durable). This is
    the "investment" loop - real signal for future personalization, not yet
    wired into automatic ranking (that's a roadmap item, not claimed as live
    magic here - see README).
    """
    data = _load()
    user = data.get(device_id) or get_or_create_user(device_id)
    fb = user.get("feedback", {})
    cat_fb = fb.get(category, {"up": 0, "down": 0})
    cat_fb[sentiment] = cat_fb.get(sentiment, 0) + 1
    fb[category] = cat_fb
    user["feedback"] = fb
    data[device_id] = user
    _save(data)
    return cat_fb


# ---------------------------------------------------------------------------
# Analytics - honest, minimal, no external service. Logs real interactions
# to a plain append-only file. No IP addresses, no fingerprinting beyond the
# same device_id already used for preferences - this is the same "device,
# not person" model as the rest of the app, just also counting visits.
# ---------------------------------------------------------------------------

EVENTS_PATH = "data/events.jsonl"


def log_event(device_id, event_type, meta=None):
    """Append one event line. Cheap, no locking needed at this scale -
    worst case with concurrent writes is an interleaved line, not corruption,
    since each write is a single atomic line append."""
    os.makedirs(os.path.dirname(EVENTS_PATH) or ".", exist_ok=True)
    record = {
        "device_id": device_id,
        "event": event_type,
        "meta": meta or {},
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(EVENTS_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass  # analytics should never break the actual app


def _load_events():
    if not os.path.exists(EVENTS_PATH):
        return []
    events = []
    with open(EVENTS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue  # skip a corrupted line rather than fail the whole read
    return events


def get_analytics_summary():
    """
    Returns a dict of everything the admin dashboard needs, computed fresh
    from data/events.jsonl and data/users.json. No caching here - this is
    meant to be checked occasionally, not hit on every page load.
    """
    events = _load_events()
    users = _load()

    total_devices = len(users)
    total_pageviews = sum(1 for e in events if e["event"] == "pageview")

    event_counts = {}
    for e in events:
        event_counts[e["event"]] = event_counts.get(e["event"], 0) + 1

    visits_by_day = {}
    for e in events:
        if e["event"] != "pageview":
            continue
        day = e["ts"][:10]
        visits_by_day[day] = visits_by_day.get(day, 0) + 1

    category_popularity = {}
    for user in users.values():
        for cat in user.get("categories", []):
            category_popularity[cat] = category_popularity.get(cat, 0) + 1

    feedback_totals = {}
    for user in users.values():
        for cat, counts in user.get("feedback", {}).items():
            if cat not in feedback_totals:
                feedback_totals[cat] = {"up": 0, "down": 0}
            feedback_totals[cat]["up"] += counts.get("up", 0)
            feedback_totals[cat]["down"] += counts.get("down", 0)

    streak_distribution = {}
    for user in users.values():
        s = user.get("streak", 1)
        bucket = "1" if s == 1 else ("2-6" if s < 7 else ("7-29" if s < 30 else "30+"))
        streak_distribution[bucket] = streak_distribution.get(bucket, 0) + 1

    return {
        "total_devices": total_devices,
        "total_pageviews": total_pageviews,
        "event_counts": event_counts,
        "visits_by_day": dict(sorted(visits_by_day.items())),
        "category_popularity": category_popularity,
        "feedback_totals": feedback_totals,
        "streak_distribution": streak_distribution,
    }
