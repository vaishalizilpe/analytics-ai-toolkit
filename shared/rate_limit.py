"""
Usage caps for the public deployment.

Every request to this app runs on the maintainer's API key, so an uncapped
public URL is an open invitation to drain it. Two independent limits:

  per session  stops one visitor looping the form
  per day      stops many visitors, or one visitor across many sessions,
               from exhausting the budget

Both are advisory, not security. The daily counter lives in process memory via
st.cache_resource, so it is shared across sessions on a single Streamlit
instance but resets when the app restarts or redeploys, and does not
coordinate across replicas. That is the right tradeoff for a demo app: it
blunts casual abuse without adding a database.

Limits are env-overridable so the deployment can tighten them without a code
change. Set MAX_CALLS_PER_SESSION=0 or MAX_CALLS_PER_DAY=0 to disable a limit
(useful for local development).
"""

import os
import threading
from datetime import date

import streamlit as st

DEFAULT_PER_SESSION = 20
DEFAULT_PER_DAY = 500

_SESSION_KEY = "_llm_call_count"


class QuotaExceeded(RuntimeError):
    """Raised when a request would exceed a usage cap."""


def _limit(env_var: str, default: int) -> int:
    raw = os.getenv(env_var, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, 0)


@st.cache_resource
def _daily_counter() -> dict:
    """Process-wide counter, shared across sessions on this instance."""
    return {"day": date.today(), "count": 0, "lock": threading.Lock()}


def _consume_daily(limit: int) -> None:
    if limit == 0:
        return
    counter = _daily_counter()
    with counter["lock"]:
        today = date.today()
        if counter["day"] != today:
            counter["day"] = today
            counter["count"] = 0
        if counter["count"] >= limit:
            raise QuotaExceeded(
                f"This demo has reached its shared daily limit of {limit} AI "
                "requests. It runs on a personal API key, so the cap keeps costs "
                "predictable. To keep going right now, add your own Anthropic key "
                "under **Use your own API key** in the sidebar. Otherwise the "
                "limit resets tomorrow."
            )
        counter["count"] += 1


def _consume_session(limit: int) -> None:
    if limit == 0:
        return
    used = st.session_state.get(_SESSION_KEY, 0)
    if used >= limit:
        raise QuotaExceeded(
            f"You have used this session's limit of {limit} AI requests on the "
            "shared key. Add your own Anthropic key under **Use your own API key** "
            "in the sidebar to continue without limits."
        )
    st.session_state[_SESSION_KEY] = used + 1


def enforce_quota() -> None:
    """
    Consume one unit of quota, or raise QuotaExceeded.

    Call immediately before an LLM request. The session limit is checked first
    so a single heavy user sees the session message rather than burning the
    shared daily budget.

    Visitors using their own API key are exempt: the caps exist to protect the
    maintainer's budget, and their requests do not touch it.
    """
    from shared.byok import is_byok

    if is_byok():
        return

    _consume_session(_limit("MAX_CALLS_PER_SESSION", DEFAULT_PER_SESSION))
    try:
        _consume_daily(_limit("MAX_CALLS_PER_DAY", DEFAULT_PER_DAY))
    except QuotaExceeded:
        # Refund the session unit: the request never reached the API, and the
        # visitor shouldn't lose session quota to a shared limit they can't see.
        st.session_state[_SESSION_KEY] = max(
            st.session_state.get(_SESSION_KEY, 1) - 1, 0
        )
        raise


def remaining_this_session() -> int | None:
    """Requests left this session, or None when the session limit is disabled."""
    limit = _limit("MAX_CALLS_PER_SESSION", DEFAULT_PER_SESSION)
    if limit == 0:
        return None
    return max(limit - st.session_state.get(_SESSION_KEY, 0), 0)
