"""APScheduler-based morning message broadcaster."""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from .config import MORNING_HOUR, MORNING_MINUTE
from .claude_client import get_morning_message
from .storage import get_all_subscribers

logger = logging.getLogger(__name__)


async def send_morning_message(bot: Bot) -> None:
    subscribers = get_all_subscribers()
    if not subscribers:
        return

    try:
        text = await get_morning_message()
    except Exception as e:
        logger.error(f"Failed to generate morning message: {e}")
        return

    sent = 0
    failed = 0
    for user_id in subscribers:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="Markdown",
            )
            sent += 1
        except Exception as e:
            logger.warning(f"Could not send morning message to {user_id}: {e}")
            failed += 1

    logger.info(f"Morning message sent: {sent} ok, {failed} failed")


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
