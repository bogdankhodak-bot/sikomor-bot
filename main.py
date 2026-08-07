"""Sikomor — spiritual companion Telegram bot + Flask health server."""

import asyncio
import datetime
import logging
import os
import signal
import threading
from zoneinfo import ZoneInfo

from flask import Flask, jsonify
from telegram.error import Conflict
from telegram.ext import ApplicationBuilder, ContextTypes

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

    # Compute a concrete first-run datetime so the job fires today at 21:30 Moscow
    # regardless of when the bot was last started. If 21:30 has already passed today,
    # it will fire at 21:30 three days from now (same cadence, no silent skip).
    now_moscow = datetime.datetime.now(MOSCOW_TZ)
    first_reminder = now_moscow.replace(hour=21, minute=30, second=0, microsecond=0)
    if first_reminder <= now_moscow:
        first_reminder += datetime.timedelta(days=3)

    jq.run_repeating(
        reminder_job,
        interval=datetime.timedelta(days=3),
        first=first_reminder,
        name="reminder",
    )
    jq.run_repeating(
        scheduler_health_job,
        interval=datetime.timedelta(minutes=5),
        first=datetime.timedelta(seconds=30),
        name="scheduler_health",
    )

    logger.info(
        f"Jobs scheduled: morning at {MORNING_HOUR:02d}:{MORNING_MINUTE:02d} Moscow, "
        f"summary at 09:00 Moscow, reminder first at {first_reminder.strftime('%Y-%m-%d %H:%M')} Moscow then every 3 days"
    )


async def scheduler_health_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prove periodically that the JobQueue is alive and report next runs."""
    jobs = context.application.job_queue.jobs()
    next_runs = ", ".join(
        f"{job.name}={job.next_t.isoformat() if job.next_t else 'none'}"
        for job in jobs
    )
    logger.info("JOBQUEUE HEARTBEAT: running; %d jobs; next runs: %s", len(jobs), next_runs)


def run_bot() -> None:
    logger.info("Starting Sikomor bot...")
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    register_handlers(application)
    logger.info(
        "Starting PTB run_polling lifecycle; post_init will register "
        "the Telegram menu and all JobQueue jobs before polling begins"
    )
    # PTB's supported lifecycle guarantees this order:
    # initialize -> post_init -> start polling -> start application.
    # In particular, post_init is invoked automatically and JobQueue starts
    # before the process begins waiting for Telegram updates.
    try:
        application.run_polling(
            drop_pending_updates=True,
            stop_signals=(signal.SIGINT, signal.SIGTERM),
            close_loop=True,
        )
    except Conflict:
        logger.critical(
            "Telegram polling conflict: another process is using this bot token. "
            "Stopping this instance instead of retrying indefinitely."
        )
        raise
    logger.info("Bot shut down cleanly.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Flask health server starting on port {port}")
    flask_thread = threading.Thread(target=start_flask, args=(port,), daemon=True)
    flask_thread.start()

    # Bot runs on main thread so PTB's signal handlers work correctly.
    run_bot()
