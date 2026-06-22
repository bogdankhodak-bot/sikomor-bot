"""Anthropic Claude AI client."""
import asyncio
import logging
import anthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

_RETRY_DELAYS = [15, 30, 60]


def _build_messages(history: list[dict], user_message: str) -> list[dict]:
    messages = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


async def _generate_with_retry(messages: list[dict]) -> str:
    last_error = None
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1})")
            await asyncio.sleep(delay)
        try:
            response = await _client.messages.create(
                model=CLAUDE_MODEL,
                system=SYSTEM_PROMPT,
                messages=messages,
                max_tokens=8192,
            )
            return response.content[0].text
        except anthropic.RateLimitError as e:
            last_error = e
        except Exception as e:
            raise
    raise last_error


async def get_reply(history: list[dict], user_message: str) -> str:
    messages = _build_messages(history, user_message)
    return await _generate_with_retry(messages)


async def get_morning_reflection(quote_text: str, quote_source: str) -> str:
    prompt = (
        f"Сегодняшнее утреннее слово: «{quote_text}» — {quote_source}.\n\n"
        "Напиши короткое (3–5 предложений) живое размышление об этом слове — "
        "как оно может коснуться человека, который живёт далеко от родины и ищет опору в вере. "
        "Не цитируй богословов, говори тепло и лично. Заверши одним мягким вопросом к читателю."
    )
    return await _generate_with_retry([{"role": "user", "content": prompt}])
