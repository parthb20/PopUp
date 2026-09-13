"""
Commits data/latest.json straight to GitHub via the Contents API, instead of
only writing it to the local Streamlit server's disk.

Why this matters: Streamlit Community Cloud redeploys (which restart the
app from a fresh git checkout) happen automatically on every push - and the
daily pipeline pushes a new draft every morning. If "Publish" only wrote
the file locally, that review work would vanish on the next redeploy, and
the safety-net Action (which only ever sees the GitHub repo, not your
running server) would have no way to know a human already published today -
it could clobber your reviewed picks with the raw draft. Committing back to
GitHub directly avoids both problems.
"""

import base64
import json

import requests
import streamlit as st

GITHUB_API = "https://api.github.com"


def _get_config():
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")  # e.g. "yourname/popup-streamlit"
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    return token, repo, branch


def is_configured():
    token, repo, _ = _get_config()
    return bool(token and repo)


def publish_to_github(data_dict, path="data/latest.json", commit_message=None):
    """
    Commits the given dict as JSON to the given path on GitHub.
    Returns (success: bool, message: str) - never raises, so a network hiccup
    doesn't crash the Review page; it just reports failure clearly.
    """
    token, repo, branch = _get_config()
    if not token or not repo:
        return False, "GITHUB_TOKEN / GITHUB_REPO not set in secrets - see README."

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"

    # Need the current file's sha to update it (GitHub's API requires this
    # for updates, not for brand-new files).
    sha = None
    try:
        get_resp = requests.get(url, headers=headers, params={"ref": branch}, timeout=10)
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")
    except Exception as e:
        return False, f"Could not reach GitHub to check current file state: {e}"

    content_str = json.dumps(data_dict, indent=2)
    content_b64 = base64.b64encode(content_str.encode()).decode()

    payload = {
        "message": commit_message or "Publish today's reviewed picks",
        "content": content_b64,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    try:
        put_resp = requests.put(url, headers=headers, json=payload, timeout=15)
    except Exception as e:
        return False, f"Could not reach GitHub to publish: {e}"

    if put_resp.status_code in (200, 201):
        return True, "Published and committed to GitHub."
    return False, f"GitHub API rejected the update (HTTP {put_resp.status_code}): {put_resp.text[:200]}"
