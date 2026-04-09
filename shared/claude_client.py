import os
import anthropic
from dotenv import load_dotenv
from shared.constants import CLAUDE_MODEL

load_dotenv()


def get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not found. Copy .env.example to .env and add your key."
        )
    return anthropic.Anthropic(api_key=api_key)


def ask_claude(system_prompt: str, user_message: str, max_tokens: int = 1500) -> str:
    client = get_client()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text
