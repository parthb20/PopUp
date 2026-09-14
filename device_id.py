"""
Device identity without any third-party cookie package. Uses the browser's
own localStorage (via a small injected script) plus Streamlit's native
st.query_params - both are things Streamlit itself supports directly, so
there's no external dependency that can silently break on a Python/Streamlit
version bump the way streamlit-cookies-manager did.

How it works, in order, on each page load:
  1. Check st.query_params for ?pid=... - if present, that's the device id,
     done immediately, no flicker.
  2. If not present, render a tiny invisible JS snippet that checks
     localStorage for a saved id (or creates one), then reloads the page
     with ?pid=... appended - this happens once, near-instantly, and only
     ever on a brand new browser/session that hasn't been tagged yet.
"""

import uuid

import streamlit as st
import streamlit.components.v1 as components


def get_device_id():
    existing = st.query_params.get("pid")
    if existing:
        is_new = st.query_params.get("new") == "1"
        if is_new:
            # Consume the flag so a manual page refresh doesn't re-trigger
            # the "welcome" hint every time.
            st.query_params["new"] = "0"
        return existing, is_new

    # No id in the URL yet - inject JS to check localStorage, or mint a new
    # id, then reload with it attached. This runs once per fresh browser.
    components.html(
        """
        <script>
          let pid = window.localStorage.getItem('popup_device_id');
          let isNew = false;
          if (!pid) {
            pid = crypto.randomUUID();
            window.localStorage.setItem('popup_device_id', pid);
            isNew = true;
          }
          const params = new URLSearchParams(window.parent.location.search);
          if (!params.get('pid')) {
            params.set('pid', pid);
            if (isNew) { params.set('new', '1'); }
            window.parent.location.search = params.toString();
          }
        </script>
        """,
        height=0,
    )
    st.stop()
