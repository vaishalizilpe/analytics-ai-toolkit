"""
Bring your own key.

The hosted demo runs on the maintainer's API key with a usage cap, so a casual
visitor gets a working tool immediately with nothing to configure. Anyone who
hits the cap, or who would simply rather not share a budget, can paste their own
Anthropic key and use the app without limits.

Handling someone else's credential carries obligations, and this module is
deliberately small so they are easy to audit:

- The key lives in `st.session_state` and nowhere else. Never written to disk,
  never placed in a URL, never logged, never sent anywhere except Anthropic.
- `st.session_state` is per-session server-side memory, so one visitor's key is
  never visible to another and it is discarded when the session ends.
- The key is NEVER written to `os.environ`. That is process-wide, and under
  Streamlit's threading model it would leak one visitor's key into another
  visitor's requests.
- The input is masked, and the key is never rendered back to the page.
"""

from __future__ import annotations

import streamlit as st

SESSION_KEY = "_byok_api_key"

# Anthropic keys start with this. Checked only to catch paste errors early;
# it is not validation, and the API remains the only real authority.
KEY_PREFIX = "sk-ant-"


def active_key() -> str | None:
    """The visitor's own key for this session, or None to use the shared key."""
    key = st.session_state.get(SESSION_KEY)
    return key or None


def is_byok() -> bool:
    """True when the visitor supplied their own key."""
    return active_key() is not None


def render_key_input() -> None:
    """
    Sidebar control for supplying a personal key.

    Rendered on every page so someone who hits the cap can resolve it without
    hunting for a settings screen.
    """
    with st.sidebar:
        st.divider()
        with st.expander("🔑 Use your own API key", expanded=False):
            st.caption(
                "This demo runs on a shared key with a daily limit. Add your own "
                "Anthropic key to skip the limit entirely."
            )

            entered = st.text_input(
                "Anthropic API key",
                type="password",
                key="_byok_input",
                placeholder="sk-ant-...",
                help="Kept in this browser session only. Never stored or logged.",
            )

            if entered:
                if not entered.startswith(KEY_PREFIX):
                    st.warning(
                        f"Anthropic keys normally begin with `{KEY_PREFIX}`. "
                        "Double-check what you pasted."
                    )
                st.session_state[SESSION_KEY] = entered.strip()
            elif SESSION_KEY in st.session_state and not entered:
                # Clearing the box releases the key.
                del st.session_state[SESSION_KEY]

            if is_byok():
                st.success("Using your key. No usage limit applies.")

            st.caption(
                "Your key is sent directly to Anthropic to answer your requests "
                "and is held in server memory for this session only. It is never "
                "written to disk, never logged, and is discarded when you close "
                "the tab. "
                "[Read the code](https://github.com/vaishalizilpe/analytics-ai-toolkit/blob/main/shared/byok.py)"
                " · [Get a key](https://console.anthropic.com/settings/keys)"
            )
