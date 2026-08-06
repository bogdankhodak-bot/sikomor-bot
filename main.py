"""Sikomor — spiritual companion Telegram bot + Flask health server."""

import asyncio
import datetime
import logging
import os
import signal
import threading
from zoneinfo import ZoneInfo

from flask import Flask, jsonify
from telegram.ext import ApplicationBuilder

from bot.config import TELEGRAM_BOT_TOKEN, MORNING_HOUR, MORNING_MINUTE
from bot.handlers import register_handlers, BOT_COMMANDS
from bot.scheduler import morning_job, summary_job, reminder_job

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

flask_app = Flask(__name__)


@flask_app.route("/")
def index():
    return "Sikomor is running 🌿", 200


@flask_app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


def start_flask(port: int) -> None:
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)


async def post_init(application) -> None:
    await application.bot.set_my_commands(BOT_COMMANDS)

    jq = application.job_queue

    jq.run_daily(
        morning_job,
        time=datetime.time(hour=MORNING_HOUR, minute=MORNING_MINUTE, tzinfo=MOSCOW_TZ),
        name="morning_message",
    )
    jq.run_daily(
        summary_job,
        time=datetime.time(hour=9, minute=0, tzinfo=MOSCOW_TZ),
        name="daily_summary",
    )
    jq.run_repeating(
        reminder_job,
        interval=datetime.timedelta(days=3),
        first=datetime.time(hour=21, minute=0, tzinfo=MOSCOW_TZ),
        name="reminder",
    )

    logger.info(
        f"Jobs scheduled: morning at {MORNING_HOUR:02d}:{MORNING_MINUTE:02d} Moscow, "
        "summary at 09:00 Moscow, reminder every 3 days at 21:00 Moscow"
    )


async def run_bot_async() -> None:
    logger.info("Starting Sikomor bot...")
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    register_handlers(application)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _handle_signal(signum, frame):
        logger.info(f"Signal {signum} received, stopping bot...")
        loop.call_soon_threadsafe(stop_event.set)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("Sikomor is running.")
        await stop_event.wait()
        logger.info("Stopping updater and application...")
        await application.updater.stop()
        await application.stop()

    logger.info("Bot shut down cleanly.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Flask health server starting on port {port}")
    flask_thread = threading.Thread(target=start_flask, args=(port,), daemon=True)
    flask_thread.start()

    # Bot runs on main thread so signal handlers work correctly
    asyncio.run(run_bot_async())
