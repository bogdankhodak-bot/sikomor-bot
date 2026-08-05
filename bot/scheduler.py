"""Scheduled jobs using PTB's built-in JobQueue (runs on the bot's event loop)."""
import logging
from telegram.ext import ContextTypes
from .claude_client import get_morning_message
from .storage import get_all_subscribers, get_user_count, get_today_new_count, reset_today_count

logger = logging.getLogger(__name__)

ADMIN_ID = 552279910


async def morning_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the daily morning message to all subscribers."""
    subscribers = get_all_subscribers()
    if not subscribers:
        logger.info("Morning job fired — no subscribers, skipping")
        return

    logger.info(f"Morning job fired — sending to {len(subscribers)} subscribers")
    try:
        text = await get_morning_message()
    except Exception as e:
        logger.error(f"Morning job: failed to generate message: {e}")
        return

    sent = 0
    failed = 0
    for user_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="Markdown",
            )
            sent += 1
        except Exception as e:
            logger.warning(f"Morning job: could not send to {user_id}: {e}")
            failed += 1

    logger.info(f"Morning job done: {sent} sent, {failed} failed")


async def summary_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send daily stats summary to admin."""
    today_new = get_today_new_count()
    total = get_user_count()
    reset_today_count()
    logger.info(f"Summary job fired — today_new={today_new}, total={total}")
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📊 Сикомор сегодня: новых пользователей {today_new}, "
                f"всего уникальных за всё время {total}"
            ),
        )
    except Exception as e:
        logger.error(f"Summary job: failed to send: {e}")
