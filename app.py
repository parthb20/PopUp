"""
Pop-Up — Streamlit app.
Run locally:   streamlit run app.py
Deploy:        Streamlit Community Cloud, point at this file.

Habit-forming design (Nir Eyal's Hook Model), applied honestly:
  - Trigger:   the "since we last met" framing taps a real, specific anxiety
               (looking out of touch) rather than a fabricated one.
  - Action:    zero friction to see today's must-knows - no login, no gate.
  - Variable reward: real streak milestones (reward of self), an opt-in
               "wildcard" story outside your usual categories (reward of
               the hunt), and genuine share (reward of the tribe).
  - Investment: category picks, read history, and thumbs feedback all make
               tomorrow's visit more tailored - real investment, not a fake
               progress bar. No dark patterns: no fabricated social proof,
               no fake urgency/scarcity, no guilt-based nagging copy.
"""

import json
import os
import random
import uuid
from datetime import datetime, timezone, timedelta

import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

from storage import get_or_create_user, save_preferences, toggle_read, record_feedback, log_event
from config import PUBLISHED_PATH

IST = timezone(timedelta(hours=5, minutes=30))

CAT_META = {
    "politics":      {"label": "Politics",       "color": "#6C5CE7", "emoji": "🏛"},
    "sports":        {"label": "Sports",         "color": "#009B8E", "emoji": "🏏"},
    "entertainment": {"label": "Entertainment",  "color": "#FF4B3E", "emoji": "🎬"},
    "economy":       {"label": "Economy",        "color": "#FFC845", "emoji": "💹"},
    "tech":          {"label": "Tech",           "color": "#FF3F8E", "emoji": "💻"},
    "global":        {"label": "Global",         "color": "#2C2C2C", "emoji": "🌍"},
}
DEFAULT_CATEGORIES = ["entertainment", "sports", "politics"]

ICON_PATH = "icon.png" if os.path.exists("icon.png") else "🎯"
st.set_page_config(page_title="Pop-Up — Since we last met", page_icon=ICON_PATH, layout="centered")

# ---------------------------------------------------------------- STYLES
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .block-container{ padding-top: 1.8rem; padding-bottom: 3rem; max-width: 700px; }

  .popup-hero{ text-align:center; margin-bottom: 1.2rem; }
  .popup-eyebrow{
    display:inline-block; background: linear-gradient(90deg,#FF4B3E,#FF3F8E);
    color:white; font-size:12px; font-weight:700; padding:6px 16px; border-radius:999px;
    margin-bottom:14px; letter-spacing:.3px;
  }
  .popup-title{
    font-family:'Space Grotesk', sans-serif; font-weight:700;
    font-size: 2.1rem; line-height:1.15; margin-bottom:0;
  }
  .popup-title .accent{
    background: linear-gradient(90deg,#6C5CE7,#FF3F8E);
    -webkit-background-clip:text; background-clip:text; color:transparent;
  }
  .popup-sub{ color:#6B6A66; font-size:15px; max-width:480px; margin:12px auto 0; }

  div[data-testid="stVerticalBlockBorderWrapper"]{
    border-radius: 16px !important;
    transition: box-shadow .15s ease, transform .15s ease;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:hover{
    box-shadow: 3px 3px 0 rgba(22,22,26,0.9);
    transform: translate(-1px,-1px);
  }

  .popup-badge{
    display:inline-block; font-family:'Space Grotesk', sans-serif; font-size:11px; font-weight:700;
    padding:5px 12px; border-radius:7px; color:white; text-transform:uppercase; letter-spacing:.4px;
  }
  .popup-must-badge{
    display:inline-block; font-size:10px; font-weight:800; padding:4px 10px;
    border-radius:7px; background:#16161A; color:#FFC845; letter-spacing:.4px; float:right;
  }
  .popup-fresh{
    display:inline-block; font-size:10px; font-weight:700; padding:4px 10px;
    border-radius:7px; background:#F1EFE8; color:#6B6A66; float:right;
  }
  .popup-headline{
    font-family:'Space Grotesk', sans-serif; font-weight:700; font-size:18px;
    margin: 10px 0 6px; line-height:1.3;
  }
  .popup-explainer{ color:#6B6A66; font-size:14.5px; line-height:1.6; margin-bottom:4px; }

  .popup-first-visit{
    background:white; border:2px dashed #6C5CE7; border-radius:14px;
    padding:14px 18px; margin-bottom:18px; font-size:13.5px;
  }
  .popup-wildcard{
    background: linear-gradient(135deg, #FFF9EC, #FFEFDC); border:2px dashed #FFC845;
    border-radius:14px; padding:14px 18px; margin-bottom:16px;
  }
  .popup-section-head{
    font-family:'Space Grotesk', sans-serif; font-weight:700; font-size:1.2rem; margin-top:0.4rem;
  }
  .popup-throwback{
    background: linear-gradient(120deg,#6C5CE7,#FF3F8E); color:white; border-radius:16px;
    padding:18px 20px; font-size:14px; line-height:1.55;
  }
  .popup-footer{ text-align:center; color:#6B6A66; font-size:12px; padding-top:8px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- DEVICE IDENTITY
cookies = EncryptedCookieManager(
    prefix="popup/",
    password=st.secrets.get("COOKIES_PASSWORD", "dev-only-change-in-production"),
)
if not cookies.ready():
    st.stop()

is_new_device = "device_id" not in cookies or not cookies["device_id"]
if is_new_device:
    cookies["device_id"] = str(uuid.uuid4())
    cookies.save()
device_id = cookies["device_id"]

user = get_or_create_user(device_id)

if "categories" not in st.session_state:
    st.session_state.categories = user["categories"]
if "read_links" not in st.session_state:
    st.session_state.read_links = set(user.get("read_links", []))
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = set()  # links already rated this session - avoid double-counting on rerun
if "show_wildcard" not in st.session_state:
    st.session_state.show_wildcard = False
if "pageview_logged" not in st.session_state:
    log_event(device_id, "pageview")
    st.session_state.pageview_logged = True
if "search_logged" not in st.session_state:
    st.session_state.search_logged = False

# ---------------------------------------------------------------- DATA LOADING
@st.cache_data(ttl=300, show_spinner=False)
def load_today_data(_mtime_bust):
    if not os.path.exists(PUBLISHED_PATH):
        return {"generated_at": None, "must_know": [], "personalized": []}
    with open(PUBLISHED_PATH) as f:
        return json.load(f)

mtime = os.path.getmtime(PUBLISHED_PATH) if os.path.exists(PUBLISHED_PATH) else 0
today_data = load_today_data(mtime)


def time_ago(iso_string):
    if not iso_string:
        return ""
    try:
        published = datetime.fromisoformat(iso_string)
    except Exception:
        return ""
    hrs = round((datetime.now(timezone.utc) - published).total_seconds() / 3600)
    if hrs < 1:
        return "Just in"
    if hrs < 24:
        return f"{hrs}h ago"
    return f"{round(hrs/24)}d ago"


def update_indicator():
    gen = today_data.get("generated_at")
    if not gen:
        return "No live data yet - run the pipeline"
    generated = datetime.fromisoformat(gen)
    is_today = generated.astimezone(IST).date() == datetime.now(IST).date()
    time_str = generated.astimezone(IST).strftime("%I:%M %p").lstrip("0")
    if is_today:
        return f"🟢 Updated {time_str} IST today · Next refresh tomorrow 6 AM"
    return f"⚠️ Last updated {generated.astimezone(IST).strftime('%b %d')} - may be stale"


# ---------------------------------------------------------------- HERO
today_label = datetime.now(IST).strftime("%a, %b %d").upper()
st.markdown(f"""
<div class="popup-hero">
  <span class="popup-eyebrow">{today_label} · SINCE 6 AM YESTERDAY</span>
  <div class="popup-title">Here's what happened <span class="accent">since we last met</span></div>
  <p class="popup-sub">Not what's trending. What's actually worth knowing — so you're never caught out in office or college today.</p>
</div>
""", unsafe_allow_html=True)

st.caption(update_indicator())

col1, col2 = st.columns([1, 2])
with col1:
    st.metric("🔥 Streak", f"{user['streak']} day{'s' if user['streak'] != 1 else ''}")
with col2:
    search_query = st.text_input("Search today's stories", placeholder="🔍 Search today's stories...", label_visibility="collapsed")
    if search_query and not st.session_state.search_logged:
        log_event(device_id, "search_used")
        st.session_state.search_logged = True

# Variable reward - reward of the self: real streak milestones, not fabricated urgency
milestone_key = f"celebrated_{user['streak']}"
if user["streak"] > 0 and user["streak"] % 7 == 0 and not st.session_state.get(milestone_key):
    st.balloons()
    st.session_state[milestone_key] = True
    st.toast(f"🎉 {user['streak']}-day streak! You're genuinely never out of the loop.")

if is_new_device:
    st.markdown("""
    <div class="popup-first-visit">
      👋 We picked <b>Entertainment, Sports, and Politics</b> for you — change it anytime below.
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------- CARD RENDERER
def render_card(item, is_must, show_feedback=False):
    cat = item.get("category", "global")
    meta = CAT_META.get(cat, {"label": cat.title(), "color": "#2C2C2C", "emoji": "📰"})
    link = item.get("link") or ""
    is_read = link in st.session_state.read_links
    fresh = time_ago(item.get("published"))
    sub_tag = f" · {item['sub_tag'].title()}" if item.get("sub_tag") else ""
    card_key = link or item["headline"]

    with st.container(border=True):
        badge_col, tag_col = st.columns([3, 1])
        with badge_col:
            st.markdown(
                f'<span class="popup-badge" style="background:{meta["color"]}">{meta["emoji"]} {meta["label"]}{sub_tag}</span>',
                unsafe_allow_html=True,
            )
        with tag_col:
            if is_must:
                st.markdown('<span class="popup-must-badge">MUST KNOW</span>', unsafe_allow_html=True)
            elif fresh:
                st.markdown(f'<span class="popup-fresh">{fresh}</span>', unsafe_allow_html=True)

        opacity = "opacity:.5" if is_read else ""
        st.markdown(f'<div class="popup-headline" style="{opacity}">{item["headline"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="popup-explainer" style="{opacity}">{item["explainer"]}</div>', unsafe_allow_html=True)

        b1, b2, b3, b4 = st.columns([2, 1, 1, 1])
        with b1:
            if link:
                st.link_button("Read full story →", link)
        with b2:
            read_label = "↺ Unread" if is_read else "✓ Read"
            if st.button(read_label, key=f"read_{card_key}"):
                now_read = toggle_read(device_id, link)
                if now_read:
                    st.session_state.read_links.add(link)
                else:
                    st.session_state.read_links.discard(link)
                log_event(device_id, "mark_read" if now_read else "mark_unread", {"category": cat})
                st.rerun()
        with b3:
            if st.button("↗ Share", key=f"share_{card_key}"):
                opening = not st.session_state.get(f"showlink_{card_key}", False)
                st.session_state[f"showlink_{card_key}"] = opening
                if opening:
                    log_event(device_id, "share_click", {"category": cat})
        with b4:
            # Investment loop - real signal for future relevance, not fake engagement bait
            if show_feedback and card_key not in st.session_state.feedback_given:
                if st.button("👍", key=f"up_{card_key}", help="More like this"):
                    record_feedback(device_id, cat, "up")
                    st.session_state.feedback_given.add(card_key)
                    st.toast("Noted — more like this coming")
                    st.rerun()

        if st.session_state.get(f"showlink_{card_key}"):
            st.code(link, language=None)


# ---------------------------------------------------------------- MUST-KNOW SECTION
st.markdown('<div class="popup-section-head">🟡 Everyone\'s talking about this</div>', unsafe_allow_html=True)
st.caption("The non-negotiable core — everyone gets these, no matter your preferences.")

must_know = today_data.get("must_know", [])
if search_query:
    must_know = [i for i in must_know if search_query.lower() in (i["headline"] + i["explainer"]).lower()]

if not must_know:
    st.info("No must-know stories match right now — try clearing your search, or the pipeline hasn't run yet.")
else:
    for item in must_know:
        render_card(item, is_must=True)

# ---------------------------------------------------------------- CATEGORY PICKER
st.markdown('<div class="popup-section-head">⚫ Worth knowing if you\'re in the room</div>', unsafe_allow_html=True)

selected = st.multiselect(
    "Your categories — tap to change what shows up below, saved automatically",
    options=list(CAT_META.keys()),
    default=st.session_state.categories,
    format_func=lambda c: f"{CAT_META[c]['emoji']} {CAT_META[c]['label']}",
)
if set(selected) != set(st.session_state.categories):
    st.session_state.categories = selected
    save_preferences(device_id, selected)
    log_event(device_id, "category_change", {"categories": selected})
    st.toast("Saved to this device")

if st.session_state.categories:
    names = ", ".join(CAT_META[c]["label"] for c in st.session_state.categories)
    st.caption(f"Picked based on what you care about: {names}. Tap 👍 on a story to fine-tune this further.")
else:
    st.caption("Turn on a category above to personalize this section.")

personalized = [i for i in today_data.get("personalized", []) if i["category"] in st.session_state.categories]
if search_query:
    personalized = [i for i in personalized if search_query.lower() in (i["headline"] + i["explainer"]).lower()]

if not personalized:
    st.info("Nothing here yet for these categories — turn on a few more above, or check back after the next refresh.")
else:
    for item in personalized:
        render_card(item, is_must=False, show_feedback=True)

# ---------------------------------------------------------------- WILDCARD (variable reward - reward of the hunt)
outside_categories = [c for c in CAT_META if c not in st.session_state.categories]
wildcard_pool = [i for i in today_data.get("personalized", []) + today_data.get("must_know", [])
                 if i["category"] in outside_categories]

if wildcard_pool:
    st.markdown("")
    if not st.session_state.show_wildcard:
        if st.button("🎲 Show me something outside my usual categories"):
            st.session_state.show_wildcard = True
            st.session_state.wildcard_pick = random.choice(wildcard_pool)
            log_event(device_id, "wildcard_used", {"category": st.session_state.wildcard_pick["category"]})
            st.rerun()
    else:
        st.markdown('<div class="popup-wildcard">🎲 <b>Outside your usual picks</b> — thought this might be worth a look too.</div>', unsafe_allow_html=True)
        render_card(st.session_state.wildcard_pick, is_must=False)

# ---------------------------------------------------------------- THROWBACK + FOOTER
st.divider()
st.markdown("""
<div class="popup-throwback">
  🕰️ <b>In case you missed it this month:</b> A blockbuster's surprise twist ending is still being debated online three weeks after release.
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="popup-footer">
  Pop-Up · Built to keep you in the loop, not in the scroll. · Preferences, streak, and read history are saved to this device — no account needed.
  · Tip: use the ⋮ menu (top right) to switch light/dark theme.
</div>
""", unsafe_allow_html=True)
