"""Telegram command and message handlers."""
import logging
import random
from telegram import Update, BotCommand
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    Application,
)
from .claude_client import get_reply
from .storage import add_message, get_history, clear_history
from .quotes import get_random_quote
from .scheduler import subscribe, unsubscribe, is_subscribed

logger = logging.getLogger(__name__)

_pourout_waiting: set[int] = set()

POUROUT_RESPONSES = [
    "Я слышал. Это настоящее. Иди.",
    "Ты сказал это вслух. Это уже много. Иди жить.",
    "Это нужно было сказать. Ты сказал. Теперь иди.",
    "Я здесь был. Слышал каждое слово. Иди.",
    "Ты человек. И это всё — по-человечески. Иди.",
    "Это честно. Это твоё. Теперь можно выдохнуть.",
    "Ничего лишнего. Всё настоящее. Иди дальше.",
    "Хорошо что сказал. Не каждый может. Иди.",
    "Это было внутри. Теперь снаружи. Стало немного легче — и этого достаточно.",
    "Я не сужу. Никто здесь не судит. Иди с миром.",
    "Столько всего. И ты всё равно здесь. Это сила.",
    "Слова упали — и пусть лежат здесь. Ты иди.",
    "Это было тяжело нести. Спасибо что доверил. Иди.",
    "Сказано — значит отпущено. Хоть немного. Иди.",
    "Ты живой. Это чувствуется. Иди жить.",
]

WELCOME_MESSAGE = """Привет. Я — Сикомор 🌿

Я здесь, чтобы быть рядом — особенно когда хочется поговорить о том, что по-настоящему важно: о вере, смысле, усталости, надежде.

Просто напиши мне — я слушаю.

*Команды:*
/morning — включить утренние слова (цитата + размышление каждое утро)
/quote — получить цитату прямо сейчас
/pourout — выговориться без масок и осуждения
/new — начать разговор заново
/help — помощь"""

HELP_MESSAGE = """*Сикомор — духовный собеседник*

Просто напиши мне всё, что у тебя на душе — я отвечу.

*Команды:*
/morning — подписаться на утренние слова (или отписаться)
/quote — цитата из Писания или Святых Отцов
/pourout — выговориться без масок и осуждения
/new — очистить историю и начать заново
/help — это сообщение

📖 Канал: https://t.me/sikomornica
💛 Поддержать: https://boosty.to/sikomor/donate"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    subscribe(user_id)
    await update.message.reply_text(WELCOME_MESSAGE, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_MESSAGE, parse_mode="Markdown")


async def morning_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if is_subscribed(user_id):
        unsubscribe(user_id)
        await update.message.reply_text(
            "Ты отписался от утренних слов. Если захочешь вернуться — просто напиши /morning снова."
        )
    else:
        subscribe(user_id)
        await update.message.reply_text(
            "Отлично 🌿 Каждое утро в 8:00 по московскому времени я буду присылать тебе "
            "слово из Писания или Святых Отцов и короткое размышление.\n\n"
            "Можно отписаться командой /morning."
        )


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    quote = get_random_quote()
    text = f"_{quote['text']}_\n\n— {quote['source']}"
    await update.message.reply_text(text, parse_mode="Markdown")


async def pourout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    _pourout_waiting.add(user_id)
    await update.message.reply_text(
        "Здесь можно сказать всё. Без масок, без осуждения. Просто напиши что внутри — я слушаю."
    )


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    clear_history(user_id)
    _pourout_waiting.discard(user_id)
    await update.message.reply_text(
        "Хорошо. Начнём с чистого листа 🌿\n\nО чём хочешь поговорить?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id in _pourout_waiting:
        _pourout_waiting.discard(user_id)
        await update.message.reply_text(random.choice(POUROUT_RESPONSES))
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    history = get_history(user_id)
    add_message(user_id, "user", user_text)

    try:
        reply = await get_reply(history, user_text)
        add_message(user_id, "assistant", reply)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Error getting Claude reply for user {user_id}: {e}")
        await update.message.reply_text(
            "Прости, я не смог ответить прямо сейчас. Попробуй ещё раз через минуту."
        )


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("morning", morning_command))
    app.add_handler(CommandHandler("quote", quote_command))
    app.add_handler(CommandHandler("pourout", pourout_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


BOT_COMMANDS = [
    BotCommand("morning", "Утренние слова — подписаться / отписаться"),
    BotCommand("quote", "Цитата из Писания или Святых Отцов"),
    BotCommand("pourout", "Выговориться — без масок, без осуждения"),
    BotCommand("new", "Начать разговор заново"),
    BotCommand("help", "Помощь"),
]
