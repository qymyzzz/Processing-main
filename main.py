import logging
import os

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


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    if not (message and message.text):
        return

    logger.info(
        "Received message in '%s' from '%s'",
        chat.title,
        update.effective_user.full_name if update.effective_user else "unknown",
    )

    try:
        topic = classify_topic(message.text)
    except Exception as e:
        logger.error("Classification failed: %s", e)
        topic = "Неизвестная тема"

    reply = f"{message.text}\n\n Тема: {topic}"
    await message.reply_text(reply)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, echo))
    logger.info("Bot is running — press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
