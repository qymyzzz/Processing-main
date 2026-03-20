import logging
import os
import queue
import threading
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from google import genai
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from categories import CAT_KEYS, CATEGORIES
from classifier import classify_gemini, classify_rule_based
from logging_config import logger
from message_history import add_message, get_messages
from ticket_store import (
    add_ticket,
    get_ticket,
    get_tickets,
    resolve_ticket,
    unresolve_ticket,
)
from tickets import generate_new_ticket

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

SEPARATOR = "─" * 60
SEPARATOR2 = "═" * 60
utc_plus_5 = timezone(timedelta(hours=5))

confirm_queue: queue.Queue = queue.Queue()


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

        chat_id = item["chat_id"]
        chat_title = item["chat_title"]
        sender = item["sender"]
        text = item["text"]
        ts = item["ts"]
        rule_cat = item["rule_cat"]
        ai_cat = item["ai_cat"]
        message_id = item["message_id"]
        print(
            format_incoming(chat_title, sender, text, ts, rule_cat, ai_cat), flush=True
        )

        try:
            raw = input("\n> ").strip()
        except EOFError:
            raw = ""

        if raw in ("1", "2", "3"):
            final = CAT_KEYS[int(raw) - 1]
        else:
            print("  Неверный ввод, введите 1, 2 или 3.", flush=True)
            continue

        time_str = ts.astimezone(utc_plus_5).strftime("%Y-%m-%d %H:%M:%S")
        if sender != "Sagyn":
            status, ticket_id = generate_new_ticket(
                chat_id, sender, text, time_str, rule_cat, ai_cat, final
            )
        else:
            status = 0
            ticket_id = None
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
            )
        if status == 1:
            print("продолжение существующего тикета", flush=True)
            unresolve_ticket(int(ticket_id))
        if status == 3:
            print("решение существующего тикета", flush=True)
            resolve_ticket(int(ticket_id))
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
        )

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

    chat = message.chat
    chat_title = chat.title or chat.full_name or f"Chat {chat.id}"
    chat_id = chat.id

    if message.from_user:
        user = message.from_user
        sender = user.full_name or user.username or f"User {user.id}"
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


# ---------------------------------------------------------------------------
# Запуск
# ---------------------------------------------------------------------------


def main():
    worker = threading.Thread(target=console_worker, daemon=True)
    worker.start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, echo))
    logger.info("Bot is running — press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
