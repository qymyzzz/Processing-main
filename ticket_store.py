import io
import logging
import os
import threading
import urllib
from datetime import datetime

import dotenv
import pandas as pd
import requests
from telegram.ext import Application

from logging_config import logger
from message_history import get_messages

dotenv.load_dotenv()

BUCKET_URL = os.getenv("BUCKET_URL")
S3_KEY = os.getenv("S3_KEY")

_tickets: list[dict] = []

_lock = threading.Lock()


# Initialize Excel on first access
def _init_excel():
    url = f"{BUCKET_URL}/{S3_KEY}"
    try:
        urllib.request.urlretrieve(url, "tickets.xlsx")
        logger.info("tickets.xlsx downloaded from S3")
    except Exception as e:
        logger.error(f"Failed to load tickets.xlsx: {e}")
        raise


async def s3_load_tickets(app: Application) -> None:
    try:
        with open("tickets.xlsx", "rb") as f:
            data = f.read()
        resp = requests.put(
            f"{BUCKET_URL}/{S3_KEY}",
            data=data,
            headers={
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
        )
        if resp.status_code == 200:
            logger.info("tickets.xlsx synced to S3")
        else:
            logger.warning(f"S3 upload failed: {resp.status_code}")
    except Exception as e:
        print(f"Failed to upload to S3: {e}")


def s3_load_tickets_sync():
    try:
        with open("tickets.xlsx", "rb") as f:
            data = f.read()
        resp = requests.put(
            f"{BUCKET_URL}/{S3_KEY}",
            data=data,
            headers={
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
        )
        if resp.status_code == 200:
            logger.info("tickets.xlsx synced to S3")
        else:
            logger.warning(f"S3 upload failed: {resp.status_code}")
    except Exception as e:
        print(f"Failed to upload to S3: {e}")


def add_ticket(
    chat_id: int,
    chat_title: str,
    sender: str,
    text: str,
    timestamp,
    rule_cat: str,
    ai_cat: str | None,
    final_cat: str | None,
    message_id: int | None = None,
    reply_to: dict | None = None,
    assignee: list | None = None,
) -> dict:
    """Add a new ticket and return it."""
    ticket = {
        "ticket_id": len(_tickets) + 1,
        "message_id": message_id,
        "chat_id": chat_id,
        "chat_title": chat_title,
        "sender": sender,
        "text": text,
        "timestamp": timestamp,
        "rule_cat": rule_cat,
        "ai_cat": ai_cat,
        "final_cat": final_cat,
        "created_at": datetime.now(),
        "reply_to": reply_to,
        "resolved": False,
        "assignee": assignee or [],
    }
    id = len(get_tickets()) + 1
    df = pd.read_excel("tickets.xlsx", sheet_name="tickets")
    new_row = pd.DataFrame(
        [
            {
                "Тикет": id,
                "Чат": chat_title,
                "Отправитель": sender,
                "Сообщение": text,
                "Категория": rule_cat,
                "Дата": timestamp,
                "Ответсвтенный": "Никто",
                "Статус": "Открыт",
            }
        ]
    )
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_excel("tickets.xlsx", sheet_name="tickets", index=False)
    with _lock:
        _tickets.append(ticket)
    return ticket


def add_assignee(ticket_id: int, assignee: str) -> bool:
    """Add an assignee to a ticket. Returns True if found, False otherwise."""
    df = pd.read_excel("tickets.xlsx", sheet_name="tickets")
    df.loc[df["Тикет"] == ticket_id, "Ответсвтенный"] = assignee
    df.to_excel("tickets.xlsx", sheet_name="tickets", index=False)
    with _lock:
        for ticket in _tickets:
            if ticket["ticket_id"] == ticket_id:
                if ticket.get("assignee") is None:
                    ticket["assignee"] = [assignee]
                if assignee not in ticket["assignee"]:
                    ticket["assignee"].append(assignee)
                return True
    return False


def get_tickets(
    chat_id: int | None = None,
    resolved: bool | None = None,
    sender: str | None = None,
    assignee: str | None = None,
) -> list[dict]:
    """
    Return a snapshot of tickets.
    - chat_id:  filter by chat, or None for all chats
    - resolved: filter by resolved status, or None for all
    - sender: filter by sender, or None for all senders
    """
    with _lock:
        result = list(_tickets)

    if chat_id is not None:
        result = [t for t in result if t["chat_id"] == chat_id]
    if resolved is not None:
        result = [t for t in result if t["resolved"] == resolved]
    if sender is not None:
        result = [t for t in result if t["sender"] == sender]
    if assignee is not None:
        result = [t for t in result if assignee in t["assignee"]]
    return result


def resolve_ticket(ticket_id: int) -> bool:
    """Mark a ticket as resolved. Returns True if found, False otherwise."""
    df = pd.read_excel("tickets.xlsx", sheet_name="tickets")
    df.loc[df["Тикет"] == ticket_id, "Статус"] = "Закрыт"
    df.to_excel("tickets.xlsx", sheet_name="tickets", index=False)
    with _lock:
        for ticket in _tickets:
            if ticket["ticket_id"] == ticket_id:
                ticket["resolved"] = True
                return True
    return False


def unresolve_ticket(ticket_id: int) -> bool:
    """Unmark a ticket as resolved. Returns False if found, True otherwise."""
    df = pd.read_excel("tickets.xlsx", sheet_name="tickets")
    df.loc[df["Тикет"] == ticket_id, "Статус"] = "Открыт"
    df.to_excel("tickets.xlsx", sheet_name="tickets", index=False)
    with _lock:
        for ticket in _tickets:
            if ticket["ticket_id"] == ticket_id:
                ticket["resolved"] = False
                return True
    return False


def get_ticket(ticket_id: int) -> dict | None:
    """Return a single ticket by ID, or None if not found."""
    with _lock:
        for ticket in _tickets:
            if ticket["ticket_id"] == ticket_id:
                return dict(ticket)
    return None


def cleanup_tickets(chat_id: int) -> None:
    """Remove tickets whose message_id is no longer in chat history."""
    current_messages = get_messages(chat_id)
    current_ids = {m["message_id"] for m in current_messages}

    with _lock:
        _tickets[:] = [
            t
            for t in _tickets
            if t["chat_id"] != chat_id or t["message_id"] in current_ids
        ]


def get_tickets_by_date_range(
    date_from: datetime,
    date_to: datetime,
    resolved: bool | None = None,
    sender: str | None = None,
    chat_id: int | None = None,
    assignee: list | None = None,
) -> list[dict]:
    """Return tickets for a chat between date_from and date_to (inclusive)."""
    with _lock:
        return [
            t
            for t in _tickets
            if date_from
            <= datetime.strptime(t["timestamp"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=date_from.tzinfo
            )
            <= date_to
            and (resolved is None or t["resolved"] == resolved)
            and (sender is None or t["sender"] == sender)
            and (chat_id is None or t["chat_id"] == chat_id)
            and (assignee is None or assignee in t["assignee"])
        ]
