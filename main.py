"""Sikomor — spiritual companion Telegram bot + Flask health server."""

import asyncio
import logging
import os
import threading

from flask import Flask, jsonify
from telegram.ext import ApplicationBuilder

from bot.config import TELEGRAM_BOT_TOKEN
from bot.handlers import register_handlers, BOT_COMMANDS
from bot.scheduler import create_scheduler

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)


@flask_app.route("/")
def index():
    return "Sikomor is running 🌿", 200


@flask_app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


async def post_init(application) -> None:
    await application.bot.set_my_commands(BOT_COMMANDS)
    scheduler = create_scheduler(application.bot)
    scheduler.start()
    logger.info("Scheduler started — morning messages at 08:00 Moscow time")


async def run_bot_async() -> None:
    logger.info("Starting Sikomor bot...")
    application = (
        ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    )
    register_handlers(application)

    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("Sikomor is running.")
        await asyncio.sleep(float("inf"))


def bot_thread() -> None:
    asyncio.run(run_bot_async())


if __name__ == "__main__":
    t = threading.Thread(target=bot_thread, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Flask health server starting on port {port}")
    flask_app.run(host="0.0.0.0", port=port)
