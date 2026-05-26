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


async def tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Поведение (будет реализовано):
      Групповой чат, без аргументов → открытые тикеты по этому чату (любая роль)
      Личный чат, без аргументов   → открытые тикеты пользователя
                                      для поддержки: ВСЕ открытые тикеты по всем чатам
      С аргументом-периодом        → тикеты за период, все статусы (любая роль)
    """
    chat_type = update.effective_chat.type  # 'private' | 'group' | 'supergroup'
    args = context.args or []
    user_id = update.effective_user.id
    user_username = update.message.from_user.username

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
        if get_role(user_id) == "support":
            tickets = get_tickets_by_date_range(
                date_from=date_from, date_to=date_to, resolved=None
            )
        else:
            tickets = get_tickets_by_date_range(
                date_from=date_from,
                date_to=date_to,
                resolved=None,
                sender=user_username,
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
    elif get_role(user_id) == "support":
        tickets = get_tickets()
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
    else:
        tickets = get_tickets(sender=user_username)
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
