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

def _ask_anthropic(system_prompt: str, user_message: str, max_tokens: int, model: str) -> str:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
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
    return message.content[0].text


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

def ask_claude(system_prompt: str, user_message: str, max_tokens: int = 1500) -> str:
    """
    Send a prompt to the configured LLM provider.

    Provider is controlled by LLM_PROVIDER env var (default: claude).
    Model is controlled by LLM_MODEL env var (optional, falls back to provider default).
    """
    model = _resolve_model()

    if _PROVIDER == "claude":
        return _ask_anthropic(system_prompt, user_message, max_tokens, model)
    elif _PROVIDER in ("openai", "deepseek"):
        return _ask_openai_compatible(system_prompt, user_message, max_tokens, model)
    elif _PROVIDER == "gemini":
        return _ask_gemini(system_prompt, user_message, max_tokens, model)
    else:
        raise EnvironmentError(
            f"Unknown LLM_PROVIDER: '{_PROVIDER}'. "
            f"Supported options: {', '.join(sorted(_SUPPORTED))}"
        )
