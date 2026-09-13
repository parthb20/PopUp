"""
Daily Review page - the actual 10-15 min workflow.
Password gated. Shows today's DRAFT (from the pipeline), lets you remove a
bad pick or manually add one RSS missed, then publish it live.
"""

import json
import os
import uuid
from datetime import datetime, timezone

import streamlit as st

from config import DRAFT_PATH, PUBLISHED_PATH
from github_publish import is_configured, publish_to_github

st.set_page_config(page_title="Pop-Up — Review Today's Picks", page_icon="📝", layout="centered")

CATEGORIES = ["politics", "sports", "entertainment", "economy", "tech", "global"]

# ---------------------------------------------------------------- PASSWORD GATE
REVIEW_PASSWORD = st.secrets.get("REVIEW_PASSWORD", st.secrets.get("ADMIN_PASSWORD", None))

if not REVIEW_PASSWORD:
    st.warning(
        "No REVIEW_PASSWORD (or ADMIN_PASSWORD) is set in secrets, so this "
        "page is unprotected. Set one before deploying."
    )
else:
    entered = st.text_input("Review password", type="password")
    if entered != REVIEW_PASSWORD:
        st.info("Enter the password to review today's picks.")
        st.stop()

st.title("📝 Review today's picks (optional)")
st.caption(
    "The pipeline already auto-published today's picks - this page is for the "
    "days you have a spare 10 minutes and want to swap something out or add "
    "a story the feeds missed. Nothing here is required."
)

# ---------------------------------------------------------------- LOAD DRAFT
if not os.path.exists(DRAFT_PATH):
    st.error("No draft yet - the pipeline hasn't run today. Trigger it from GitHub Actions, or wait for the 6 AM run.")
    st.stop()

with open(DRAFT_PATH) as f:
    draft = json.load(f)

draft_date = draft.get("generated_at", "")[:10]
st.caption(f"Draft generated: {draft.get('generated_at', 'unknown')}")

# Track removed items across reruns within this review session
if "removed_links" not in st.session_state:
    st.session_state.removed_links = set()
if "manual_additions" not in st.session_state:
    st.session_state.manual_additions = []


def review_card(item, section_label):
    link = item.get("link") or item["headline"]
    removed = link in st.session_state.removed_links
    with st.container(border=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"**{item['headline']}**" + (" ~~(removed)~~" if removed else ""))
            st.caption(f"{item['category'].title()} · {item.get('source', 'unknown source')}")
            st.write(item.get("explainer", ""))
            if item.get("link"):
                st.caption(item["link"])
        with col2:
            if removed:
                if st.button("Restore", key=f"restore_{section_label}_{link}"):
                    st.session_state.removed_links.discard(link)
                    st.rerun()
            else:
                if st.button("Remove", key=f"remove_{section_label}_{link}"):
                    st.session_state.removed_links.add(link)
                    st.rerun()


# ---------------------------------------------------------------- MUST-KNOW REVIEW
st.subheader("🟡 Must-know picks")
must_know = draft.get("must_know", [])
if not must_know:
    st.caption("Nothing here yet.")
for item in must_know:
    review_card(item, "must")

st.divider()

# ---------------------------------------------------------------- PERSONALIZED REVIEW
st.subheader("⚫ Personalized picks")
personalized = draft.get("personalized", [])
if not personalized:
    st.caption("Nothing here yet.")
for item in personalized:
    review_card(item, "personal")

st.divider()

# ---------------------------------------------------------------- MANUALLY ADD SOMETHING RSS MISSED
st.subheader("➕ Add something the feeds missed")
st.caption("The most useful part of this review - drop in whatever's actually blowing up that RSS didn't catch yet.")

with st.form("add_story_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        new_category = st.selectbox("Category", CATEGORIES)
        new_is_must = st.checkbox("Mark as must-know (everyone sees it)", value=True)
    with col2:
        new_link = st.text_input("Link (optional but recommended)")
    new_headline = st.text_input("Headline (plain language, what happened)")
    new_explainer = st.text_area("Quick explainer (1-2 sentences, why it matters)")
    submitted = st.form_submit_button("Add this to today's picks")
    if submitted:
        if not new_headline:
            st.error("Needs at least a headline.")
        else:
            st.session_state.manual_additions.append({
                "category": new_category,
                "sub_tag": None,
                "source": "Manually added",
                "headline": new_headline,
                "explainer": new_explainer or "No explainer provided.",
                "link": new_link or "#",
                "published": datetime.now(timezone.utc).isoformat(),
                "must_know": new_is_must,
            })
            st.success("Added below - don't forget to Publish when you're done.")

if st.session_state.manual_additions:
    st.write("**Manually added so far:**")
    for i, item in enumerate(st.session_state.manual_additions):
        col1, col2 = st.columns([5, 1])
        with col1:
            tag = "MUST-KNOW" if item["must_know"] else "personalized"
            st.write(f"- [{tag}] **{item['headline']}** ({item['category']})")
        with col2:
            if st.button("Remove", key=f"remove_manual_{i}"):
                st.session_state.manual_additions.pop(i)
                st.rerun()

st.divider()

# ---------------------------------------------------------------- PUBLISH
st.subheader("🚀 Publish")

final_must = [i for i in must_know if (i.get("link") or i["headline"]) not in st.session_state.removed_links]
final_personal = [i for i in personalized if (i.get("link") or i["headline"]) not in st.session_state.removed_links]
for item in st.session_state.manual_additions:
    if item["must_know"]:
        final_must.append(item)
    else:
        final_personal.append(item)

st.write(f"Will publish **{len(final_must)}** must-know picks and **{len(final_personal)}** personalized picks.")

if not is_configured():
    st.warning(
        "GITHUB_TOKEN / GITHUB_REPO aren't set in secrets - Publish will only "
        "write locally, which **won't survive the next redeploy** and the "
        "safety-net job won't see it as reviewed. Set these up (see README) "
        "for this to actually stick."
    )

if st.button("✅ Publish today's picks", type="primary"):
    published = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "must_know": final_must,
        "personalized": final_personal,
    }
    # Always write locally too, so the change is visible immediately on
    # this running server without waiting for a redeploy.
    with open(PUBLISHED_PATH, "w") as f:
        json.dump(published, f, indent=2)

    if is_configured():
        with st.spinner("Committing to GitHub..."):
            success, message = publish_to_github(published)
        if success:
            st.success(f"Published! {message}")
            st.balloons()
        else:
            st.error(
                f"Published locally, but committing to GitHub failed: {message}. "
                "This means it may not survive the next redeploy - check your "
                "GITHUB_TOKEN/GITHUB_REPO secrets."
            )
    else:
        st.success("Published locally (see warning above about persistence).")
        st.balloons()

    st.session_state.removed_links = set()
    st.session_state.manual_additions = []

st.caption(
    "Today's picks are already live either way - this just overwrites them "
    "with your edits. If you don't visit this page at all, the site still "
    "updates every day on its own."
)
