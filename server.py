"""
Serves the static site + two small JSON APIs:
  GET  /api/bootstrap     -> device's saved categories, streak, onboarded flag
  POST /api/preferences   -> save this device's chosen categories
  GET  /api/today         -> today's must-know + personalized cards

No accounts, no passwords - preferences and streak are tied to a random
device_id stored in a plain cookie (1 year expiry). Clearing cookies /
using a new browser resets it, same as most "remember this device" flows.
"""

import json
import os
import uuid

from flask import Flask, jsonify, send_from_directory, request, make_response

from storage import get_or_create_user, save_preferences, save_theme, toggle_read

app = Flask(__name__, static_folder="public", static_url_path="")

DATA_PATH = "data/latest.json"
COOKIE_NAME = "popup_device_id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


def _get_device_id():
    """Read the device_id cookie, or None if this is a brand new visitor."""
    return request.cookies.get(COOKIE_NAME)


def _set_device_cookie(resp, device_id):
    # NOTE: once deployed behind HTTPS (Render/Railway/etc. all provide this
    # automatically), add secure=True here so the cookie is only ever sent
    # over encrypted connections. Left off by default so local http testing
    # (e.g. `python server.py` on localhost) still works out of the box.
    resp.set_cookie(
        COOKIE_NAME, device_id,
        max_age=COOKIE_MAX_AGE, httponly=True, samesite="Lax"
    )


@app.route("/")
def index():
    return send_from_directory("public", "index.html")


@app.route("/api/bootstrap")
def bootstrap():
    device_id = _get_device_id()
    is_new = device_id is None
    if is_new:
        device_id = str(uuid.uuid4())

    user = get_or_create_user(device_id)

    resp = make_response(jsonify({
        "categories": user["categories"],
        "onboarded": user["onboarded"],
        "streak": user["streak"],
        "theme": user.get("theme", "light"),
        "read_links": user.get("read_links", []),
        "new_device": is_new,
    }))
    _set_device_cookie(resp, device_id)
    return resp


@app.route("/api/preferences", methods=["POST"])
def preferences():
    device_id = _get_device_id()
    if not device_id:
        return jsonify({"error": "no device_id cookie - call /api/bootstrap first"}), 400

    body = request.get_json(silent=True) or {}
    categories = body.get("categories", [])
    if not isinstance(categories, list):
        return jsonify({"error": "categories must be a list"}), 400

    user = save_preferences(device_id, categories)
    return jsonify({"categories": user["categories"], "onboarded": user["onboarded"]})


@app.route("/api/theme", methods=["POST"])
def theme():
    device_id = _get_device_id()
    if not device_id:
        return jsonify({"error": "no device_id cookie - call /api/bootstrap first"}), 400
    body = request.get_json(silent=True) or {}
    user = save_theme(device_id, body.get("theme", "light"))
    return jsonify({"theme": user["theme"]})


@app.route("/api/read", methods=["POST"])
def read_state():
    device_id = _get_device_id()
    if not device_id:
        return jsonify({"error": "no device_id cookie - call /api/bootstrap first"}), 400
    body = request.get_json(silent=True) or {}
    link = body.get("link", "")
    if not link:
        return jsonify({"error": "link is required"}), 400
    now_read = toggle_read(device_id, link)
    return jsonify({"link": link, "read": now_read})


@app.route("/api/today")
def today():
    if not os.path.exists(DATA_PATH):
        return jsonify({"error": "No data yet. Run pipeline.py first."}), 404
    with open(DATA_PATH) as f:
        return jsonify(json.load(f))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
