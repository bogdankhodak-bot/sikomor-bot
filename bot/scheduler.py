"""APScheduler-based morning message broadcaster."""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from .config import MORNING_HOUR, MORNING_MINUTE
from .quotes import get_random_quote, get_random_question
from .claude_client import get_morning_reflection
from .storage import get_all_user_ids

logger = logging.getLogger(__name__)

_subscribers: set[int] = set()


def subscribe(user_id: int) -> None:
    _subscribers.add(user_id)


def unsubscribe(user_id: int) -> None:
    _subscribers.discard(user_id)


def is_subscribed(user_id: int) -> bool:
    return user_id in _subscribers


async def send_morning_message(bot: Bot) -> None:
    if not _subscribers:
        return

    quote = get_random_quote()
    reflection = await get_morning_reflection(quote["text"], quote["source"])
    question = get_random_question()

    text = (
        f"🌅 *Доброе утро*\n\n"
        f"_{quote['text']}_\n— {quote['source']}\n\n"
        f"{reflection}\n\n"
        f"💭 {question}"
    )

    for user_id in list(_subscribers):
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not send morning message to {user_id}: {e}")


def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        send_morning_message,
        trigger=CronTrigger(hour=MORNING_HOUR, minute=MORNING_MINUTE),
        args=[bot],
        id="morning_message",
        replace_existing=True,
    )
    return scheduler
