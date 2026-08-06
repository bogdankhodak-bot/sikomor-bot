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
        "Составь утренний «Компас дня» для человека ищущего Бога в обычной жизни.\n\n"
        "Формат строго такой (без отступлений):\n"
        "1. Выбери одну короткую цитату из Евангелия — живую, конкретную, не банальную. "
        "Приведи её курсивом в формате Markdown: _«текст цитаты»_ — Евангелие от [имя], глава:стих\n"
        "2. На новой строке напиши один вопрос-компас для этого дня — конкретный, живой, "
        "вытекающий именно из этой цитаты. Вопрос должен помочь человеку увидеть эту цитату "
        "в своём сегодняшнем дне. Не общий — а точный, как будто ты знаешь его день.\n\n"
        "Никаких вступлений, заголовков, подписей и лишних слов — только цитата и вопрос."
    )
    text = await _generate_with_retry([{"role": "user", "content": prompt}])
    return f"🧭 *Компас дня*\n\n{text}"
