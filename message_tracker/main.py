import os
import json

from .shutdown import handle_shutdown
from .logging_config import logger
from .s3_load_last_messages import s3_load_last_messages, init_last_messages
from .get_data import _get_last_messages_path
from datetime import datetime, timezone, timedelta
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_IDS_RAW = os.getenv("SUPPORT_IDS", "")
SUPPORT_IDS = set(int(uid.strip()) for uid in SUPPORT_IDS_RAW.split(",") if uid.strip())

STORAGE_FILE = os.getenv("STORAGE_FILE")
S3_SYNC_INTERVAL_SECONDS = int(os.getenv("S3_SYNC_INTERVAL_MINUTES")) * 60

filepath = _get_last_messages_path()


def load_data() -> dict:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: dict):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_sorted_messages(data: dict) -> list[dict]:
    entries = list(data.values())
    entries.sort(key=lambda x: x["timestamp"], reverse=True)
    return entries


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or not user:
        return

    if chat.type not in ("group", "supergroup"):
        return

    if user.id in SUPPORT_IDS:
        return

    chat_id = str(chat.id)
    tz_utc5 = timezone(timedelta(hours=5))
    msg_time = message.date.astimezone(tz_utc5)

    MONTHS_RU = {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря",
    }
    msg_time_str = f"{msg_time.day} {MONTHS_RU[msg_time.month]} {msg_time.year}, {msg_time.strftime('%H:%M')}"

    data = load_data()
    data[chat_id] = {
        "chat_id": chat.id,
        "chat_title": chat.title or "(unknown group)",
        "user_id": user.id,
        "username": user.username or "",
        "full_name": user.full_name or "",
        "message_id": message.message_id,
        "text": message.text or message.caption or "(без текста)",
        "timestamp": msg_time_str,
        "timestamp_raw": msg_time.isoformat(),
    }
    save_data(data)

    logger.info(
        "Сохранено сообщение от пользователя %s (%s) в группе '%s' в %s",
        user.id,
        user.full_name,
        chat.title,
        msg_time_str,
    )


async def cmd_latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data:
        await update.message.reply_text("Сообщений пока не отслежено.")
        return

    sorted_entries = get_sorted_messages(data)
    lines = ["📋 *Последнее сообщение не от саппорта по каждой группе:*\n"]
    for entry in sorted_entries:
        lines.append(
            f"🗂 *{entry['chat_title']}*\n"
            f"  👤 {entry['full_name']} (@{entry['username'] or 'N/A'})\n"
            f"  🕐 `{entry['timestamp']}`\n"
            f"  💬 {entry['text'][:200]}\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def main():
    init_last_messages()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_group_message)
    )
    app.add_handler(CommandHandler("latest", cmd_latest))
    logger.info("Bot is running — press Ctrl+C to stop.")
    app.job_queue.run_repeating(
        s3_load_last_messages, interval=S3_SYNC_INTERVAL_SECONDS
    )
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        handle_shutdown()


if __name__ == "__main__":
    main()
