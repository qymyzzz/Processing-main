import os
import json

from ..logging_config import logger
from .get_data import _get_last_messages_path
from telegram.ext import Application
from dotenv import load_dotenv
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
S3_SYNC_INTERVAL_SECONDS = int(os.getenv("S3_SYNC_INTERVAL_SECONDS", 60))

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
