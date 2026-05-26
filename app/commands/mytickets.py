import datetime
import os
import queue
from datetime import datetime, timedelta, timezone
from itertools import groupby

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes
from app.utils import escape_md

from app.commands.start import SUPPORT_IDS
from app.ticket_system.send_tickets_group import send_ticket_list
from app.ticket_system.ticket_store import get_tickets, get_tickets_by_date_range

load_dotenv()

SUPPORT_IDS = os.getenv("SUPPORT_IDS").split(",")


def get_role(user_id: int) -> str:
    """Return 'support', 'duty', or 'client'."""
    if str(user_id) in SUPPORT_IDS:
        return "support"
    return "client"


async def mytickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    user_id = update.effective_user.id
    user_username = (
        update.message.from_user.username
        or update.message.from_user.full_name
        or f"user{user_id}"
    )
    if get_role(user_id=user_id) != "support":
        await update.message.reply_text("⚠️ У вас нет доступа к этой команде\\.")
        return
    # print(chat_type, args, user_id, flush=True)
    if args:
        if not context.args:
            await send_ticket_list(update)
            return

        # Parse date range argument
        try:
            raw = context.args[0]  # "ДД.ММ.ГГГГ-ДД.ММ.ГГГГ"
            part_from, part_to = raw.split("-", 1)
            date_from = datetime.strptime(part_from.strip(), "%d.%m.%Y")
            date_to = datetime.strptime(part_to.strip(), "%d.%m.%Y").replace(
                hour=23, minute=59, second=59
            )
        except ValueError:
            await update.message.reply_text(
                "⚠️ Неверный формат даты\\.\n"
                "Используйте: `/tickets ДД\\.ММ\\.ГГГГ\\-ДД\\.ММ\\.ГГГГ`\n"
                "Пример: `/tickets 01\\.03\\.2026\\-29\\.03\\.2026`",
                parse_mode="MarkdownV2",
            )
            return
        tickets = get_tickets_by_date_range(
            date_from=date_from,
            date_to=date_to,
            resolved=False,
            assignee=user_username,
        )

        if not tickets:
            await update.message.reply_text(
                f"📭 Тикетов за период *{escape_md(part_from)} — {escape_md(part_to)}* не найдено\\.",
                parse_mode="MarkdownV2",
            )
            return

        chats = []
        for t in tickets:
            if t["chat_id"] not in chats:
                chats.append(t["chat_id"])

        for chat_id in chats:
            chat_tickets = [t for t in tickets if t["chat_id"] == chat_id]
            await send_ticket_list(update, tickets=chat_tickets)
    else:
        # print(user_username, flush=True)
        tickets = get_tickets(assignee=user_username)
        if not tickets:
            await update.message.reply_text("📭 Тикетов пока нет\\.")
            return
        chats = []
        for t in tickets:
            if t["chat_id"] not in chats:
                chats.append(t["chat_id"])

        for chat_id in chats:
            chat_tickets = [t for t in tickets if t["chat_id"] == chat_id]
            await send_ticket_list(update, tickets=chat_tickets)
