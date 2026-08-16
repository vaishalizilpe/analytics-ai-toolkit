"""
Bring-your-own-key behavior, focused on the ways it could leak.

The functional part (an explicit key overrides the environment) is easy. The
part worth testing is the security boundary: a visitor's key must never become
process-global, because Streamlit serves concurrent sessions from one process
and `os.environ` is shared by all of them.
"""

from __future__ import annotations

import importlib
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


def reload_client(env_vars: dict):
    with patch.dict("os.environ", env_vars, clear=False):
        import shared.claude_client as mod
        importlib.reload(mod)
        return mod


def _text_response(text: str = "ok"):
    block = MagicMock(type="text")
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


# ── the key reaches the SDK ───────────────────────────────────────────────────

def test_explicit_key_overrides_environment():
    """A visitor's key must win over the maintainer's."""
    mod = reload_client({"LLM_PROVIDER": "claude", "LLM_MODEL": ""})

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-SHARED"}):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _text_response()
            mod._ask_anthropic("sys", "user", 100, "claude-sonnet-4-6",
                               api_key="sk-ant-VISITOR")
            assert MockClient.call_args.kwargs["api_key"] == "sk-ant-VISITOR"


def test_falls_back_to_environment_when_no_key_supplied():
    """Casual visitors keep using the shared key with no configuration."""
    mod = reload_client({"LLM_PROVIDER": "claude", "LLM_MODEL": ""})

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-SHARED"}):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _text_response()
            mod._ask_anthropic("sys", "user", 100, "claude-sonnet-4-6")
            assert MockClient.call_args.kwargs["api_key"] == "sk-ant-SHARED"


def test_ask_claude_threads_the_key_through():
    mod = reload_client({"LLM_PROVIDER": "claude", "LLM_MODEL": ""})

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-SHARED"}):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _text_response()
            mod.ask_claude("sys", "user", api_key="sk-ant-VISITOR")
            assert MockClient.call_args.kwargs["api_key"] == "sk-ant-VISITOR"


# ── the key must not leak ─────────────────────────────────────────────────────

def test_visitor_key_never_written_to_environ():
    """
    The critical one.

    os.environ is process-wide. Streamlit serves concurrent sessions from a
    single process, so a key placed there would be handed to other visitors.
    """
    mod = reload_client({"LLM_PROVIDER": "claude", "LLM_MODEL": ""})
    before = dict(os.environ)

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-SHARED"}):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _text_response()
            mod.ask_claude("sys", "user", api_key="sk-ant-VISITOR-SECRET")

    assert "sk-ant-VISITOR-SECRET" not in str(dict(os.environ))
    assert os.environ.get("ANTHROPIC_API_KEY") == before.get("ANTHROPIC_API_KEY")


def test_key_is_not_in_module_state_between_calls():
    """Two calls with different keys must not contaminate one another."""
    mod = reload_client({"LLM_PROVIDER": "claude", "LLM_MODEL": ""})

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-SHARED"}):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _text_response()

            mod.ask_claude("sys", "user", api_key="sk-ant-ALICE")
            assert MockClient.call_args.kwargs["api_key"] == "sk-ant-ALICE"

            # A later call with no key must fall back to the shared key,
            # not reuse Alice's.
            mod.ask_claude("sys", "user")
            assert MockClient.call_args.kwargs["api_key"] == "sk-ant-SHARED"


def test_byok_module_does_not_touch_credential_environ_at_import():
    """
    Importing the module must not add or alter any credential variable.

    Checks credential keys specifically rather than the whole environment:
    importing Streamlit pulls in matplotlib, which legitimately sets
    MPLBACKEND, and a byte-identical comparison would fail on that.
    """
    def creds() -> dict:
        return {k: v for k, v in os.environ.items()
                if "KEY" in k.upper() or "TOKEN" in k.upper()
                or "SECRET" in k.upper() or "PASSWORD" in k.upper()}

    sys.modules.pop("shared.byok", None)
    before = creds()
    importlib.import_module("shared.byok")
    assert creds() == before


def test_byok_module_writes_nothing_to_disk():
    """No persistence: grep the source for file-writing calls."""
    from pathlib import Path

    source = Path("shared/byok.py").read_text()
    for forbidden in ("open(", "write_text", ".write(", "os.environ["):
        assert forbidden not in source, (
            f"shared/byok.py must not contain {forbidden!r}: a visitor's key "
            "must never be persisted or made global"
        )
