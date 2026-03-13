import logging
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from google import genai
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SEPARATOR = "─" * 60
utc_plus_5 = timezone(timedelta(hours=5))


def classify_topic(text: str) -> str:
    prompt = (
        "Ты классификатор тем. По сообщению ниже ответь ТОЛЬКО коротким названием темы на РУССКОМ языке"
        "(1-4 слова, например: 'Спорт', 'Политика', 'Еда', 'Технологии', 'Финансы' и т.д.)."
        "Без объяснений, без знаков препинания в конце, только название темы.\n\n"
        f"Сообщение: {text}"
    )
    response = gemini_client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text.strip()


def format_message(chat_title: str, sender: str, text: str, timestamp: datetime) -> str:
    time_str = timestamp.astimezone(utc_plus_5).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"\n{SEPARATOR}\n"
        f"Чат:      {chat_title}\n"
        f"От:       {sender}\n"
        f"Время:    {time_str}\n"
        f"Сообщение: {text}\n"
        f"{SEPARATOR}"
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # message = update.effective_message
    # chat = update.effective_chat
    # if chat.type not in ("group", "supergroup"):
    #     return

    # if not (message and message.text):
    #     return

    # logger.info(
    #     "Received message in '%s' from '%s'",
    #     chat.title,
    #     update.effective_user.full_name if update.effective_user else "unknown",
    # )

    # try:
    #     topic = classify_topic(message.text)
    # except Exception as e:
    #     logger.error("Classification failed: %s", e)
    #     topic = "Неизвестная тема"

    # reply = f"{message.text}\n\n Тема: {topic}"
    # await message.reply_text(reply)
    message = update.message or update.channel_post
    if not message:
        return

    bot_id = context.bot.id
    if message.from_user and message.from_user.id == bot_id:
        return

    chat = message.chat
    chat_title = chat.title or chat.full_name or f"Chat {chat.id}"

    if message.from_user:
        user = message.from_user
        sender = user.full_name or user.username or f"User {user.id}"
    elif message.sender_chat:
        sender = message.sender_chat.title or f"Chat {message.sender_chat.id}"
    else:
        sender = "Неизвестный"

    text = message.text or message.caption or "[медиа без текста]"
    timestamp = message.date
    output = format_message(chat_title, sender, text, timestamp)
    print(output, flush=True)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, echo))
    logger.info("Bot is running — press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
