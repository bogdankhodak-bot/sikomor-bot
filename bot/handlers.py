"""Telegram command and message handlers."""
import logging
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
from .quotes import get_random_quote, get_random_question
from .scheduler import subscribe, unsubscribe, is_subscribed

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = """Привет. Я — Сикомор 🌿

Я здесь, чтобы быть рядом — особенно когда далеко от дома и хочется поговорить о том, что по-настоящему важно: о вере, смысле, одиночестве, надежде.

Просто напиши мне — я слушаю.

*Команды:*
/morning — включить утренние слова (цитата + размышление каждое утро)
/quote — получить цитату прямо сейчас
/question — вопрос для размышления
/new — начать разговор заново
/help — помощь"""

HELP_MESSAGE = """*Сикомор — духовный собеседник*

Просто напиши мне всё, что у тебя на душе — я отвечу.

*Команды:*
/morning — подписаться на утренние слова (или отписаться)
/quote — цитата из Писания или Святых Отцов
/question — вопрос для вечернего размышления
/new — очистить историю и начать заново
/help — это сообщение"""


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


async def question_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = get_random_question()
    await update.message.reply_text(f"💭 {question}")


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    clear_history(user_id)
    await update.message.reply_text(
        "Хорошо. Начнём с чистого листа 🌿\n\nО чём хочешь поговорить?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_text = update.message.text

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
        logger.error(f"Error getting Gemini reply for user {user_id}: {e}")
        await update.message.reply_text(
            "Прости, я не смог ответить прямо сейчас. Попробуй ещё раз через минуту."
        )


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("morning", morning_command))
    app.add_handler(CommandHandler("quote", quote_command))
    app.add_handler(CommandHandler("question", question_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


BOT_COMMANDS = [
    BotCommand("morning", "Утренние слова — подписаться / отписаться"),
    BotCommand("quote", "Цитата из Писания или Святых Отцов"),
    BotCommand("question", "Вопрос для размышления"),
    BotCommand("new", "Начать разговор заново"),
    BotCommand("help", "Помощь"),
]
