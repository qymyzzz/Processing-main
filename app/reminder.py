import logging
import os

from dotenv import load_dotenv
from telegram.ext import Application

from .utils import escape_md
from .ticket_store import get_tickets

logger = logging.getLogger(__name__)

load_dotenv()

SUPPORT_IDS = os.getenv("SUPPORT_IDS").split(",")


async def send_unresolved_reminder(app: Application) -> None:
    """
    Отправляет всем пользователям поддержки список открытых тикетов.
    Запускается по расписанию из config.py (REMINDER_INTERVAL_HOURS).
    """

    tickets = get_tickets(resolved=False)

    if not tickets:
        return

    lines = [
        "🔔 *Напоминание об открытых тикетах*",
        f"Всего не закрыто: *{escape_md(str(len(tickets)))}*",
        "",
    ]

    for t in tickets:
        ts = (
            t["timestamp"].strftime("%d.%m.%Y %H:%M")
            if hasattr(t["timestamp"], "strftime")
            else str(t["timestamp"])
        )
        category = t.get("final_cat") or t.get("ai_cat") or t.get("rule_cat") or "—"
        preview = t["text"][:120] + ("…" if len(t["text"]) > 120 else "")

        lines += [
            f"🎫 *Тикет #{escape_md(str(t['ticket_id']))}*",
            f"👤 {escape_md(t['sender'])}  |  🏷 {escape_md(category)}  |  🕐 {escape_md(ts)}",
            f"💬 _{escape_md(preview)}_",
            f"📌 Чат: {escape_md(t['chat_title'])}",
            "",
        ]

    text = "\n".join(lines)

    for user_id in SUPPORT_IDS:
        try:
            await app.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="MarkdownV2",
            )
        except Exception as e:
            logger.warning(
                "Не удалось отправить напоминание пользователю %s: %s", user_id, e
            )
