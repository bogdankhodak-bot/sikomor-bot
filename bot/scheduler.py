"""Scheduled jobs using PTB's built-in JobQueue (runs on the bot's event loop)."""
import logging
import random
from telegram.ext import ContextTypes
from .claude_client import get_morning_message
from .storage import get_all_subscribers, get_all_known_users, get_user_count, get_today_new_count, reset_today_count

logger = logging.getLogger(__name__)

ADMIN_ID = 552279910

REMINDERS = [
    "По дороге домой сегодня — найди один момент тишины. Хотя бы минуту. Просто посмотри вокруг. Бог рядом.",
    "Что сегодня тебя удивило? Даже маленькое — солнечный луч, улыбка незнакомца, запах кофе. Замечай это.",
    "Сегодня вечером перед сном — вспомни один момент дня когда тебе было хорошо. Просто вспомни и побудь в нём.",
    "Посмотри что вокруг тебя сейчас. Что видишь, что чувствуешь. Бог не только в храме.",
    "Есть ли рядом с тобой сегодня кто-то кому ты был нужен? Или кто был нужен тебе? Это не случайно.",
    "Одна минута тишины сегодня — просто сиди и ничего не делай. Это уже молитва.",
    "Что тебя держит сегодня? Работа, усталость, тревога? Попробуй сказать об этом вслух — хотя бы себе.",
    "Сегодня по дороге — подними взгляд от телефона хоть на минуту. Посмотри на людей вокруг. У каждого своя история.",
    "Вспомни человека который сделал тебе что-то доброе. Давно или недавно. Просто вспомни.",
    "Есть ли в твоём дне сегодня что-то за что можно сказать спасибо? Это важно.",
    "Когда ты последний раз жил просто, медленно? Без спешки, без телефона. Только ты и твоя жизнь. Попробуй.",
    "Сегодня ночью перед сном — три вещи которые произошли сегодня. Любые. Просто три.",
    "Есть ли место в твоём городе где тебе спокойно? Парк, набережная, тихая улица. Вспомни его прямо сейчас.",
    "Что сегодня прошло мимо твоего внимания? Может закат за окном. Или чья-то доброта. Или тишина между делами.",
    "Бог часто говорит тишиной. Найди сегодня пять минут без музыки, без подкастов, без новостей. Просто иди и слушай.",
]


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


async def reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a random reminder to all known users every 3 days."""
    users = get_all_known_users()
    if not users:
        logger.info("Reminder job fired — no users, skipping")
        return

    text = random.choice(REMINDERS)
    logger.info(f"Reminder job fired — sending to {len(users)} users")

    sent = 0
    failed = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
            sent += 1
        except Exception as e:
            logger.warning(f"Reminder job: could not send to {user_id}: {e}")
            failed += 1

    logger.info(f"Reminder job done: {sent} sent, {failed} failed")
