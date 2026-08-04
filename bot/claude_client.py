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


async def get_morning_message() -> str:
    prompt = (
        "Напиши короткое утреннее сообщение — ровно 2–3 предложения — которое помогает человеку "
        "увидеть Бога в обычных моментах сегодняшнего дня. "
        "Говори тепло и лично, без религиозного пафоса. "
        "Не используй заголовки, вступления или подписи — только само сообщение. "
        "Не задавай вопросов. Каждый раз пиши по-новому, не повторяй одни и те же образы."
    )
    text = await _generate_with_retry([{"role": "user", "content": prompt}])
    return f"🌅 {text}"
