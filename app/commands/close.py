import datetime
import os
import queue
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes
from app.utils import escape_md

from app.ticket_system.send_tickets_group import send_ticket_list
from app.ticket_system.ticket_store import get_ticket, resolve_ticket

load_dotenv()

SUPPORT_IDS = os.getenv("SUPPORT_IDS").split(",")


async def close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    user_username = update.effective_user.username

    if len(args) != 1:
        await update.message.reply_text(
            "⚠️ Неверное количество аргументов\\. Используйте: `/close <id>`\nПример: `/close 42`",
            parse_mode="MarkdownV2",
        )
        return
    arg = args[0]
    if not arg.isdigit():
        await update.message.reply_text(
            "⚠️ Неверный ID\\. Используйте: `/close <id>`\nПример: `/close 42`",
            parse_mode="MarkdownV2",
        )
        return
    ticket_id = int(arg)
    ticket = get_ticket(ticket_id)
    if not ticket:
        await update.message.reply_text(
            f"⚠️ Тикет {escape_md(str(ticket_id))} не найден\\."
        )
        return
    if (
        ticket["sender"] != user_username
        and str(update.effective_user.id) not in SUPPORT_IDS
    ):
        await update.message.reply_text(
            "⚠️ Вы можете закрывать только свои тикеты\\.",
            parse_mode="MarkdownV2",
        )
        return
    if resolve_ticket(ticket_id):
        await update.message.reply_text(f"✅ Тикет {escape_md(str(ticket_id))} закрыт.")
    else:
        await update.message.reply_text(
            f"⚠️ Тикет {escape_md(str(ticket_id))} не найден\\."
        )
