import io
import logging
import os
import queue
import signal
import asyncio
from .health_check import run_health_server

import threading
from datetime import datetime, timedelta, timezone
import time

import pandas as pd
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

from .ticket_system.categories import CAT_KEYS, CATEGORIES
from .ticket_system.classifier import classify_gemini, classify_rule_based
from .message_tracker.methods import (
    init_last_messages,
    s3_load_last_messages,
    cmd_latest,
    load_data,
    save_data,
    get_sorted_messages,
)
from app.commands.close import close
from app.commands.duty import duty
from app.commands.mytickets import mytickets
from app.commands.report import _build_excel, report
from app.commands.start import start
from app.commands.tickets import tickets
from .logging_config import logger
from .ticket_system.message_history import (
    _init_messages,
    add_message,
    get_messages,
    s3_load_messages,
)
from .ticket_system.reminder import send_unresolved_reminder
from .sanitize import sanitize
from .utils import escape_md
from .ticket_system.send_tickets_group import send_ticket_list
from .s3_sync import s3_load_everything
from .shutdown import handle_shutdown
from .ticket_system.ticket_store import (
    _init_excel,
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
from .ticket_system.tickets import flush_retry_queue, generate_new_ticket

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_IDS = os.getenv("SUPPORT_IDS").split(",")
REMINDER_INTERVAL = int(
    os.getenv("REMINDER_INTERVAL")
)  # in seconds, e.g. 18000 for 5 hours
S3_SYNC_INTERVAL_SECONDS = int(os.getenv("S3_SYNC_INTERVAL_MINUTES")) * 60

# Webhook settings — devops will provide these values
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://yourbot.company.com
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")

# Optional SSL cert paths (if devops uses self-signed certs)
WEBHOOK_SSL_CERT = os.getenv("WEBHOOK_SSL_CERT", None)  # path to cert.pem
WEBHOOK_SSL_KEY = os.getenv("WEBHOOK_SSL_KEY", None)  # path to key.pem

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
        f"Сообщение):  {text}\n"
        f"Сообщение (защищеннное):  {sanitize(text)}\n"
        f"Rule-based: {CATEGORIES[rule_cat]} {rule_cat}\n"
    )


def retry_worker():
    while True:
        time.sleep(60)
        flush_retry_queue()


# ---------------------------------------------------------------------------
# Консольный поток — читает очередь и ждёт ввода
# ---------------------------------------------------------------------------


def console_worker():
    while True:
        try:
            item = confirm_queue.get()
            if item is None:
                break

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
            logger.info(format_incoming(chat_title, sender, text, ts, rule_cat, ai_cat))
            final = rule_cat
            time_str = ts.astimezone(utc_plus_5).strftime("%Y-%m-%d %H:%M:%S")
            if (
                not text.startswith("/tickets")
                and not text.startswith("/close")
                and not text.startswith("/report")
            ):
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
                if status == 0 or status is None:
                    logger.info("не обращение")
                if status == 2:
                    logger.info("новое обращение")
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
                    logger.info(f"продолжение существующего тикета {ticket_id}")
                if status == 3:
                    logger.info(f"решение существующего тикета {ticket_id}")
                    resolve_ticket(int(ticket_id))
                if status == 4:
                    logger.info(f"переоткрытие тикета {ticket_id}")
                    unresolve_ticket(int(ticket_id))
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
        except Exception as e:
            logger.error(f"Error in console_worker: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Telegram обработчик
# ---------------------------------------------------------------------------


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
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
                reply_sender = (
                    replied.sender_chat.title or f"Chat {replied.sender_chat.id}"
                )
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
        data = load_data()
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
        data[chat_id] = {
            "chat_id": chat_id,
            "chat_title": chat_title or "(unknown group)",
            "user_id": user_id,
            "username": user.username or "",
            "full_name": user.full_name or "",
            "message_id": message_id,
            "text": text,
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
                    "⚠️ Неверный формат даты\\.\n"
                    "Используйте: `/tickets ДД\\.ММ\\.ГГГГ\\-ДД\\.ММ\\.ГГГГ`\n"
                    "Пример: `/tickets 01\\.03\\.2026\\-29\\.03\\.2026`",
                    parse_mode="MarkdownV2",
                )
                return
            tickets = get_tickets_by_date_range(
                date_from=date_from, date_to=date_to, chat_id=chat_id
            )
            if not tickets:
                await update.message.reply_text(
                    f"📭 Тикетов за период *{escape_md(part_from)} — {escape_md(part_to)}* не найдено\\.",
                    parse_mode="MarkdownV2",
                )
                return
            await send_ticket_list(update, tickets)
        elif text.startswith("/close"):
            arg = text[len("/close") :].strip()
            if not arg or not arg.isdigit():
                await update.message.reply_text(
                    "⚠️ Неверный ID\\. Используйте: `/close <id>`\nПример: `/close 42`",
                    parse_mode="MarkdownV2",
                )
                return
            ticket_id = int(arg)
            if resolve_ticket(ticket_id):
                await update.message.reply_text(
                    f"✅ Тикет {escape_md(str(ticket_id))} закрыт\\."
                )
            else:
                await update.message.reply_text(
                    f"⚠️ Тикет {escape_md(str(ticket_id))} не найден\\."
                )
        elif text.startswith("/report"):
            if get_role(update.effective_user.id) != "support":
                await update.message.reply_text(
                    "⚠️ У вас нет доступа к этой команде\\."
                )
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
                    f"📊 Отчёт по тикетам\n"
                    f"Всего: {escape_md(str(len(tickets)))} "
                    f"Открытых: {escape_md(str(sum(1 for t in tickets if not t['resolved'])))} "
                    f"Закрытых: {escape_md(str(sum(1 for t in tickets if t['resolved'])))}"
                ),
                parse_mode="MarkdownV2",
            )
    except Exception as e:
        logger.error(f"Error in echo handler: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Запуск
# ---------------------------------------------------------------------------


def main():
    _init_excel()
    _init_messages()
    init_last_messages()
    retry = threading.Thread(target=retry_worker, daemon=True)
    retry.start()
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
    app.add_handler(CommandHandler("latest", cmd_latest))
    logger.info("Bot is running — press Ctrl+C to stop.")
    app.job_queue.run_repeating(send_unresolved_reminder, interval=REMINDER_INTERVAL)
    app.job_queue.run_repeating(s3_load_everything, interval=S3_SYNC_INTERVAL_SECONDS)

    use_webhook = int(os.getenv("USE_WEBHOOK", 0))
    # print(f"Using webhook: {use_webhook}")
    if use_webhook == 1:
        # print("here")
        loop = asyncio.new_event_loop()
        health_thread = threading.Thread(
            target=lambda: loop.run_until_complete(run_health_server()), daemon=True
        )
        health_thread.start()
        logger.info(
            f"Bot is running via webhook on {WEBHOOK_HOST}:{WEBHOOK_PORT}{WEBHOOK_PATH}"
        )

        try:
            # print(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
            app.run_webhook(
                listen=WEBHOOK_HOST,
                port=WEBHOOK_PORT,
                url_path=WEBHOOK_PATH,
                webhook_url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
                cert=WEBHOOK_SSL_CERT or None,
                key=WEBHOOK_SSL_KEY or None,
            )
        finally:
            handle_shutdown()
    else:
        try:
            app.run_polling(allowed_updates=Update.ALL_TYPES)
        finally:
            handle_shutdown()


if __name__ == "__main__":
    main()
