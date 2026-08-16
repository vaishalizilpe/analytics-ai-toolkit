"""
Model-agnostic LLM client.

Swap providers by setting LLM_PROVIDER in your .env file.
Supported: claude (default), openai, deepseek, gemini

The function signature of ask_claude() is unchanged — no other files need editing.
"""

import os
from dotenv import load_dotenv

load_dotenv()

_PROVIDER = os.getenv("LLM_PROVIDER", "claude").lower()
_MODEL_OVERRIDE = os.getenv("LLM_MODEL", "").strip()

_DEFAULTS = {
    "claude":   "claude-sonnet-4-6",
    "openai":   "gpt-4o",
    "deepseek": "deepseek-chat",
    "gemini":   "gemini-1.5-pro",
}

_SUPPORTED = set(_DEFAULTS.keys())


class LLMRefusal(RuntimeError):
    """The model declined the request (Anthropic returns HTTP 200 for this)."""


class LLMEmptyResponse(RuntimeError):
    """The response carried no text block."""


def _resolve_model() -> str:
    if _MODEL_OVERRIDE:
        return _MODEL_OVERRIDE
    if _PROVIDER not in _SUPPORTED:
        raise EnvironmentError(
            f"Unknown LLM_PROVIDER: '{_PROVIDER}'. "
            f"Supported options: {', '.join(sorted(_SUPPORTED))}"
        )
    return _DEFAULTS[_PROVIDER]


# ── Provider implementations ──────────────────────────────────────────────────

def _ask_anthropic(system_prompt: str, user_message: str, max_tokens: int, model: str,
                   api_key: str | None = None) -> str:
    import anthropic

    # An explicitly passed key wins over the environment. It is threaded in
    # as an argument rather than read from a global so that a per-visitor key
    # can never leak across concurrent sessions.
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not found. Copy .env.example to .env and add your key."
        )
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    # A refusal returns HTTP 200 with an empty content list, so indexing
    # content[0] would raise IndexError instead of surfacing why. Check
    # stop_reason before reading content.
    if message.stop_reason == "refusal":
        raise LLMRefusal(
            "The model declined to answer this request. Rephrasing the "
            "business context usually resolves it."
        )

    text = next(
        (block.text for block in message.content if block.type == "text"), None
    )
    if text is None:
        raise LLMEmptyResponse(
            f"The model returned no text (stop_reason: {message.stop_reason})."
        )

    if message.stop_reason == "max_tokens":
        text += (
            "\n\n_[Response truncated at the output limit. "
            "Narrow the question for a complete answer.]_"
        )
    return text


def _ask_openai_compatible(system_prompt: str, user_message: str, max_tokens: int, model: str) -> str:
    from openai import OpenAI

    if _PROVIDER == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise EnvironmentError("DEEPSEEK_API_KEY not found.")
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not found.")
        client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content


def _ask_gemini(system_prompt: str, user_message: str, max_tokens: int, model: str) -> str:
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not found.")

    genai.configure(api_key=api_key)
    # Gemini doesn't have a separate system role — prepend to user message
    full_prompt = f"{system_prompt}\n\n{user_message}"
    gemini_model = genai.GenerativeModel(model)
    response = gemini_model.generate_content(
        full_prompt,
        generation_config={"max_output_tokens": max_tokens},
    )
    return response.text


# ── Public interface (signature unchanged) ────────────────────────────────────

def ask_claude(system_prompt: str, user_message: str, max_tokens: int = 1500,
               api_key: str | None = None) -> str:
    """
    Send a prompt to the configured LLM provider.

    Provider is controlled by LLM_PROVIDER env var (default: claude).
    Model is controlled by LLM_MODEL env var (optional, falls back to provider default).

    api_key overrides the environment for this call only. It exists so a
    visitor can supply their own key without it ever becoming global state.
    """
    model = _resolve_model()

    if _PROVIDER == "claude":
        return _ask_anthropic(system_prompt, user_message, max_tokens, model, api_key)
    elif _PROVIDER in ("openai", "deepseek"):
        return _ask_openai_compatible(system_prompt, user_message, max_tokens, model)
    elif _PROVIDER == "gemini":
        return _ask_gemini(system_prompt, user_message, max_tokens, model)
    else:
        raise EnvironmentError(
            f"Unknown LLM_PROVIDER: '{_PROVIDER}'. "
            f"Supported options: {', '.join(sorted(_SUPPORTED))}"
        )
