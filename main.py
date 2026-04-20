import io
import logging
import os
import queue
import signal
import threading
from datetime import datetime, timedelta, timezone

import pandas as pd
import xlwings as xw
from dotenv import load_dotenv
from google import genai
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from categories import CAT_KEYS, CATEGORIES
from classifier import classify_gemini, classify_rule_based
from commands.close import close
from commands.duty import duty
from commands.mytickets import mytickets
from commands.report import _build_excel, report
from commands.start import start
from commands.tickets import tickets
from logging_config import logger
from message_history import add_message, get_messages
from reminder import send_unresolved_reminder
from send_tickets_group import send_ticket_list
from shutdown import handle_shutdown
from ticket_store import (
    add_assignee,
    add_ticket,
    cleanup_tickets,
    get_ticket,
    get_tickets,
    get_tickets_by_date_range,
    resolve_ticket,
    s3_load_tickets,
    unresolve_ticket,
)
from tickets import flush_retry_queue, generate_new_ticket

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_IDS = os.getenv("SUPPORT_IDS").split(",")
REMINDER_INTERVAL = os.getenv("REMINDER_INTERVAL")  # in seconds, e.g. 18000 for 5 hours
S3_SYNC_INTERVAL_SECONDS = int(os.getenv("S3_SYNC_INTERVAL_MINUTES")) * 60

SEPARATOR = "─" * 60
SEPARATOR2 = "═" * 60
utc_plus_5 = timezone(timedelta(hours=5))

confirm_queue: queue.Queue = queue.Queue()


def get_role(user_id: int) -> str:
    """Return 'support', 'duty', or 'client'."""
    if str(user_id) in SUPPORT_IDS:
        return "support"
    return "client"


# ---------------------------------------------------------------------------
# Форматирование лога
# ---------------------------------------------------------------------------


def format_incoming(chat_title, sender, text, timestamp, rule_cat, ai_cat):
    time_str = timestamp.astimezone(utc_plus_5).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"\n{SEPARATOR}\n"
        f"Чат:        {chat_title}\n"
        f"От:         {sender}\n"
        f"Время:      {time_str}\n"
        f"Сообщение:  {text}\n"
        f"Rule-based: {CATEGORIES[rule_cat]} {rule_cat}\n"
        f"Gemini:     {CATEGORIES.get(ai_cat, '❓')} {ai_cat or '—'}\n"
        f"{SEPARATOR}\n"
        f"  Категория: 1=Операционная  2=Инциденты  3=Интеграции"
    )


def format_confirmed(chat_title, sender, text, timestamp, rule_cat, ai_cat, final):
    time_str = timestamp.astimezone(utc_plus_5).strftime("%Y-%m-%d %H:%M:%S")
    both_match = rule_cat == ai_cat == final
    lines = [
        f"\n{SEPARATOR2}",
        f"Чат:        {chat_title}",
        f"От:         {sender}",
        f"Время:      {time_str}",
        f"Сообщение:  {text}",
        f"Итог:       {CATEGORIES[final]} {final}",
    ]
    if both_match:
        lines.append("✅ оба классификатора верны")
    else:
        lines.append(f"⚠️  Rule-based: {CATEGORIES[rule_cat]} {rule_cat}")
        lines.append(f"⚠️  Gemini:     {CATEGORIES.get(ai_cat, '❓')} {ai_cat or '—'}")
    lines.append(SEPARATOR2)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Консольный поток — читает очередь и ждёт ввода
# ---------------------------------------------------------------------------


def console_worker():
    while True:
        item = confirm_queue.get()
        if item is None:
            break

        flush_retry_queue()

        user_id = item["user_id"]
        chat_id = item["chat_id"]
        chat_title = item["chat_title"]
        sender = item["sender"]
        text = item["text"]
        ts = item["ts"]
        rule_cat = item["rule_cat"]
        ai_cat = item["ai_cat"]
        message_id = item["message_id"]
        reply_to = item["reply_to"]
        print(
            format_incoming(chat_title, sender, text, ts, rule_cat, ai_cat), flush=True
        )

        # try:
        #     raw = input("\n> ").strip()
        # except EOFError:
        #     raw = ""

        # if raw in ("1", "2", "3"):
        #     final = CAT_KEYS[int(raw) - 1]
        # else:
        #     print("  Неверный ввод, введите 1, 2 или 3.", flush=True)
        #     continue
        final = rule_cat
        time_str = ts.astimezone(utc_plus_5).strftime("%Y-%m-%d %H:%M:%S")
        if (
            not text.startswith("/tickets")
            and not text.startswith("/close")
            and not text.startswith("/report")
        ):
            # if get_role(sender) == "client":
            status, ticket_id = generate_new_ticket(
                chat_id,
                sender,
                text,
                time_str,
                rule_cat,
                ai_cat,
                final,
                reply_to=reply_to,
            )
            # status = 2
            # ticket_id = None
            # else:
            #     status = 0
            #     ticket_id = None
            if status == 0 or status is None:
                print("не обращение", flush=True)
            if status == 2:
                print("новое обращение", flush=True)
                add_ticket(
                    chat_id=chat_id,
                    chat_title=chat_title,
                    sender=sender,
                    text=text,
                    timestamp=time_str,
                    rule_cat=rule_cat,
                    ai_cat=ai_cat,
                    final_cat=final,
                    message_id=message_id,
                    reply_to=reply_to,
                )
            if status == 1:
                if get_role(user_id=user_id) == "support":
                    add_assignee(ticket_id, sender)
                print(f"продолжение существующего тикета {ticket_id}", flush=True)
            if status == 3:
                print(f"решение существующего тикета {ticket_id}", flush=True)
                resolve_ticket(int(ticket_id))
            if status == 4:
                print(f"переоткрытие тикета {ticket_id}", flush=True)
                unresolve_ticket(int(ticket_id))
        # print("Текущие тикеты:", flush=True)
        # print(get_tickets(chat_id=chat_id))
        add_message(
            chat_id=chat_id,
            chat_title=chat_title,
            sender=sender,
            text=text,
            timestamp=time_str,
            rule_cat=rule_cat,
            ai_cat=ai_cat,
            message_id=message_id,
            final_cat=final,
            reply_to=reply_to,
        )
        cleanup_tickets(chat_id)
        print(
            format_confirmed(chat_title, sender, text, ts, rule_cat, ai_cat, final),
            flush=True,
        )


# ---------------------------------------------------------------------------
# Telegram обработчик
# ---------------------------------------------------------------------------


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message or update.channel_post
    if not message:
        return

    bot_id = context.bot.id
    if message.from_user and message.from_user.id == bot_id:
        return

    user_id = update.effective_user.id if update.effective_user else None
    chat = message.chat
    chat_title = chat.title or chat.full_name or f"Chat {chat.id}"
    chat_id = chat.id

    if message.from_user:
        user = message.from_user
        sender = user.username or user.full_name or f"User {user.id}"
    elif message.sender_chat:
        sender = message.sender_chat.title or f"Chat {message.sender_chat.id}"
    else:
        sender = "Неизвестный"

    text = message.text or message.caption or "[медиа без текста]"
    timestamp = message.date

    rule_cat = classify_rule_based(text)
    ai_cat = None  # classify_gemini(text)
    message_id = message.message_id

    reply_to = None
    if message.reply_to_message:
        replied = message.reply_to_message
        if replied.from_user:
            reply_sender = (
                replied.from_user.full_name
                or replied.from_user.username
                or f"User {replied.from_user.id}"
            )
        elif replied.sender_chat:
            reply_sender = replied.sender_chat.title or f"Chat {replied.sender_chat.id}"
        else:
            reply_sender = "Неизвестный"

        reply_to = {
            "message_id": replied.message_id,
            "sender": reply_sender,
            "text": replied.text or replied.caption or "[медиа без текста]",
        }
    confirm_queue.put(
        {
            "user_id": user_id,
            "chat_id": chat_id,
            "chat_title": chat_title,
            "sender": sender,
            "text": text,
            "ts": timestamp,
            "rule_cat": rule_cat,
            "ai_cat": ai_cat,
            "message_id": message_id,
            "reply_to": reply_to,
        }
    )
    if text == "/tickets":
        tickets = get_tickets(chat_id=chat_id)
        await send_ticket_list(update, tickets)
    elif text.startswith("/tickets "):
        raw = text[len("/tickets ") :].strip()
        try:
            part_from, part_to = raw.split("-", 1)
            date_from = datetime.strptime(part_from.strip(), "%d.%m.%Y")
            date_to = datetime.strptime(part_to.strip(), "%d.%m.%Y").replace(
                hour=23, minute=59, second=59
            )
        except ValueError:
            await update.message.reply_text(
                "⚠️ Неверный формат даты.\n"
                "Используйте: `/tickets ДД.ММ.ГГГГ-ДД.ММ.ГГГГ`\n"
                "Пример: `/tickets 01.03.2026-29.03.2026`",
                parse_mode="Markdown",
            )
            return
        tickets = get_tickets_by_date_range(
            date_from=date_from, date_to=date_to, chat_id=chat_id
        )
        if not tickets:
            await update.message.reply_text(
                f"📭 Тикетов за период *{part_from} — {part_to}* не найдено.",
                parse_mode="Markdown",
            )
            return
        await send_ticket_list(update, tickets)
    elif text.startswith("/close "):
        arg = text[len("/close ") :].strip()
        if not arg.isdigit():
            await update.message.reply_text(
                "⚠️ Неверный ID. Используйте: `/close <id>`\nПример: `/close 42`",
                parse_mode="Markdown",
            )
            return
        ticket_id = int(arg)
        if resolve_ticket(ticket_id):
            await update.message.reply_text(f"✅ Тикет {ticket_id} закрыт.")
        else:
            await update.message.reply_text(f"⚠️ Тикет {ticket_id} не найден.")
    elif text.startswith("/report"):
        if get_role(update.effective_user.id) != "support":
            await update.message.reply_text("⚠️ У вас нет доступа к этой команде.")
            return
        tickets = get_tickets(chat_id=chat_id)

        if not tickets:
            await update.message.reply_text("📭 Тикетов пока нет — отчёт пуст.")
            return

        await update.message.reply_text("⏳ Формирую отчёт...")

        excel_bytes = _build_excel(tickets)
        filename = (
            f"{chat_title}_tickets_{datetime.now().strftime('%d-%m-%Y_%H-%M')}.xlsx"
        )

        await update.message.reply_document(
            document=io.BytesIO(excel_bytes),
            filename=filename,
            caption=(
                f"📊 *Отчёт по тикетам*\n"
                f"Всего: *{len(tickets)}* · "
                f"Открытых: *{sum(1 for t in tickets if not t['resolved'])}* · "
                f"Закрытых: *{sum(1 for t in tickets if t['resolved'])}*"
            ),
            parse_mode="Markdown",
        )


# ---------------------------------------------------------------------------
# Запуск
# ---------------------------------------------------------------------------


def main():
    worker = threading.Thread(target=console_worker, daemon=True)
    worker.start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, echo))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tickets", tickets))
    app.add_handler(CommandHandler("close", close))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("duty", duty))
    app.add_handler(CommandHandler("mytickets", mytickets))
    logger.info("Bot is running — press Ctrl+C to stop.")
    app.job_queue.run_repeating(send_unresolved_reminder, interval=30000)
    app.job_queue.run_repeating(s3_load_tickets, interval=S3_SYNC_INTERVAL_SECONDS)
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        handle_shutdown()


if __name__ == "__main__":
    main()
