"""
Admin analytics dashboard - password gated.
Streamlit auto-discovers this as a second page since it lives in pages/.
Access via the sidebar page selector, or directly at /Admin_Analytics.
"""

import streamlit as st
import pandas as pd

from storage import get_analytics_summary

st.set_page_config(page_title="Pop-Up — Admin Analytics", page_icon="📊", layout="centered")

st.title("📊 Pop-Up Analytics")
st.caption("Real data from actual visitors - device counts, not personal identities.")

# ---------------------------------------------------------------- PASSWORD GATE
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)

if not ADMIN_PASSWORD:
    st.warning(
        "No ADMIN_PASSWORD is set in secrets, so this page is unprotected. "
        "Add `ADMIN_PASSWORD = \"something-only-you-know\"` to your secrets "
        "before deploying, or anyone who finds this URL can see your analytics."
    )
else:
    entered = st.text_input("Admin password", type="password")
    if entered != ADMIN_PASSWORD:
        st.info("Enter the admin password to view analytics.")
        st.stop()

# ---------------------------------------------------------------- DATA
summary = get_analytics_summary()

if summary["total_devices"] == 0:
    st.info("No visitor data yet - once people start using the app, stats will show up here.")
    st.stop()

# ---------------------------------------------------------------- TOP-LINE NUMBERS
col1, col2, col3 = st.columns(3)
col1.metric("Unique devices ever seen", summary["total_devices"])
col2.metric("Total pageviews logged", summary["total_pageviews"])
col3.metric(
    "Avg pageviews / device",
    round(summary["total_pageviews"] / summary["total_devices"], 1) if summary["total_devices"] else 0,
)

st.caption(
    "'Unique devices' counts distinct browser cookies, not people - the same "
    "person on two browsers/phones counts twice, and clearing cookies resets "
    "the count for that device. Treat this as a solid proxy, not an exact "
    "human headcount."
)

st.divider()

# ---------------------------------------------------------------- VISITS OVER TIME
st.subheader("Visits by day")
if summary["visits_by_day"]:
    df = pd.DataFrame(
        {"pageviews": list(summary["visits_by_day"].values())},
        index=list(summary["visits_by_day"].keys()),
    )
    st.bar_chart(df)
else:
    st.caption("No pageview events logged yet.")

st.divider()

# ---------------------------------------------------------------- WHAT PEOPLE CLICK
st.subheader("What people actually do")
if summary["event_counts"]:
    df = pd.DataFrame(
        {"count": list(summary["event_counts"].values())},
        index=list(summary["event_counts"].keys()),
    )
    st.bar_chart(df)
    st.caption(
        "pageview = loaded the app · mark_read/mark_unread = tapped the read toggle · "
        "share_click = opened the share link · search_used = used search at least once · "
        "category_change = changed their category picks · wildcard_used = tried the 🎲 wildcard"
    )
else:
    st.caption("No interaction events logged yet.")

st.divider()

# ---------------------------------------------------------------- CATEGORY POPULARITY
st.subheader("Category popularity (across all devices' saved preferences)")
if summary["category_popularity"]:
    df = pd.DataFrame(
        {"devices with this on": list(summary["category_popularity"].values())},
        index=list(summary["category_popularity"].keys()),
    )
    st.bar_chart(df)
else:
    st.caption("No category preference data yet.")

st.divider()

# ---------------------------------------------------------------- FEEDBACK (👍)
st.subheader("Story feedback (👍 given per category)")
if summary["feedback_totals"]:
    rows = {cat: counts.get("up", 0) for cat, counts in summary["feedback_totals"].items()}
    df = pd.DataFrame({"👍 count": list(rows.values())}, index=list(rows.keys()))
    st.bar_chart(df)
else:
    st.caption("No feedback given yet.")

st.divider()

# ---------------------------------------------------------------- STREAK DISTRIBUTION
st.subheader("Streak distribution")
if summary["streak_distribution"]:
    order = ["1", "2-6", "7-29", "30+"]
    ordered = {k: summary["streak_distribution"].get(k, 0) for k in order if k in summary["streak_distribution"]}
    df = pd.DataFrame({"devices": list(ordered.values())}, index=list(ordered.keys()))
    st.bar_chart(df)
    st.caption("How many devices are at day-1, still building a habit (2-6), a real habit (7-29), or a power user (30+).")
else:
    st.caption("No streak data yet.")
