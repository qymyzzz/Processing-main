import datetime
import os
import queue
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes

from app.ticket_system.send_tickets_group import send_ticket_list
from app.ticket_system.ticket_store import get_ticket, resolve_ticket

load_dotenv()

DUTY_IDS = os.getenv("DUTY_IDS").split(",")
SUPPORT_IDS = os.getenv("SUPPORT_IDS").split(",")


async def duty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Список дежурных:\n" + "\n".join(DUTY_IDS))
