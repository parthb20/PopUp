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
