"""
Tests for shared/claude_client.py

Run with: pytest tests/test_claude_client.py -v
No API keys required — all provider calls are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch
import importlib


# ── Helpers ───────────────────────────────────────────────────────────────────

def reload_client(env_vars: dict):
    """Reload claude_client with a controlled environment."""
    with patch.dict("os.environ", env_vars, clear=False):
        import shared.claude_client as mod
        importlib.reload(mod)
        return mod


# ── _resolve_model ────────────────────────────────────────────────────────────

def test_resolve_model_defaults_to_sonnet(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    mod = reload_client({"LLM_PROVIDER": "claude", "LLM_MODEL": ""})
    assert mod._resolve_model() == "claude-sonnet-4-6"


def test_resolve_model_respects_override(monkeypatch):
    mod = reload_client({"LLM_PROVIDER": "claude", "LLM_MODEL": "claude-opus-4-7"})
    assert mod._resolve_model() == "claude-opus-4-7"


def test_resolve_model_unknown_provider_raises():
    mod = reload_client({"LLM_PROVIDER": "fakellm", "LLM_MODEL": ""})
    with pytest.raises(EnvironmentError, match="Unknown LLM_PROVIDER"):
        mod._resolve_model()


# ── ask_claude routing ────────────────────────────────────────────────────────

def test_routes_to_anthropic_when_provider_is_claude():
    mod = reload_client({"LLM_PROVIDER": "claude", "LLM_MODEL": ""})
    with patch.object(mod, "_ask_anthropic", return_value="ok") as mock:
        result = mod.ask_claude("sys", "user")
    mock.assert_called_once()
    assert result == "ok"


def test_routes_to_openai_when_provider_is_openai():
    mod = reload_client({"LLM_PROVIDER": "openai", "LLM_MODEL": ""})
    with patch.object(mod, "_ask_openai_compatible", return_value="ok") as mock:
        result = mod.ask_claude("sys", "user")
    mock.assert_called_once()
    assert result == "ok"


def test_routes_to_openai_compatible_when_provider_is_deepseek():
    mod = reload_client({"LLM_PROVIDER": "deepseek", "LLM_MODEL": ""})
    with patch.object(mod, "_ask_openai_compatible", return_value="ok") as mock:
        result = mod.ask_claude("sys", "user")
    mock.assert_called_once()
    assert result == "ok"


def test_routes_to_gemini_when_provider_is_gemini():
    mod = reload_client({"LLM_PROVIDER": "gemini", "LLM_MODEL": ""})
    with patch.object(mod, "_ask_gemini", return_value="ok") as mock:
        result = mod.ask_claude("sys", "user")
    mock.assert_called_once()
    assert result == "ok"


# ── Missing API key errors ────────────────────────────────────────────────────

def test_anthropic_raises_without_api_key():
    mod = reload_client({"LLM_PROVIDER": "claude", "LLM_MODEL": ""})
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
        with patch("anthropic.Anthropic"):
            with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
                mod._ask_anthropic("sys", "user", 100, "claude-sonnet-4-6")


def test_openai_raises_without_api_key():
    import sys
    fake_openai = MagicMock()
    mod = reload_client({"LLM_PROVIDER": "openai", "LLM_MODEL": ""})
    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
        with patch.dict(sys.modules, {"openai": fake_openai}):
            with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
                mod._ask_openai_compatible("sys", "user", 100, "gpt-4o")


def test_deepseek_raises_without_api_key():
    import sys
    fake_openai = MagicMock()
    mod = reload_client({"LLM_PROVIDER": "deepseek", "LLM_MODEL": ""})
    with patch.dict("os.environ", {"DEEPSEEK_API_KEY": ""}, clear=False):
        with patch.dict(sys.modules, {"openai": fake_openai}):
            with pytest.raises(EnvironmentError, match="DEEPSEEK_API_KEY"):
                mod._ask_openai_compatible("sys", "user", 100, "deepseek-chat")


def test_gemini_raises_without_api_key():
    import sys
    fake_genai = MagicMock()
    mod = reload_client({"LLM_PROVIDER": "gemini", "LLM_MODEL": ""})
    with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
        with patch.dict(sys.modules, {"google.generativeai": fake_genai, "google": MagicMock()}):
            with pytest.raises(EnvironmentError, match="GEMINI_API_KEY"):
                mod._ask_gemini("sys", "user", 100, "gemini-1.5-pro")


# ── max_tokens passthrough ────────────────────────────────────────────────────

def test_max_tokens_passed_to_anthropic():
    mod = reload_client({"LLM_PROVIDER": "claude", "LLM_MODEL": ""})

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="answer")]

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = fake_response
            mod._ask_anthropic("sys", "user", 300, "claude-sonnet-4-6")
            call_kwargs = MockClient.return_value.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 300
