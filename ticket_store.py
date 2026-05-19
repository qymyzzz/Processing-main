import io
import json
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
TICKETS_META = os.getenv("TICKETS_META")

_tickets: list[dict] = []

_lock = threading.Lock()


def load_meta():
    url = f"{BUCKET_URL}/{TICKETS_META}"
    try:
        urllib.request.urlretrieve(url, TICKETS_META)
        with open(TICKETS_META, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _init_excel():
    url = f"{BUCKET_URL}/{S3_KEY}"
    try:
        data = load_meta()
        if data:
            with _lock:
                global _tickets
                _tickets = [
                    {
                        "ticket_id": row["ticket_id"],
                        "message_id": row["message_id"],
                        "chat_id": row["chat_id"],
                        "chat_title": row["chat_title"],
                        "sender": row["sender"],
                        "text": row["text"],
                        "timestamp": row["timestamp"],
                        "rule_cat": row["rule_cat"],
                        "ai_cat": row["ai_cat"],
                        "final_cat": row["final_cat"],
                        "created_at": row["created_at"],
                        "reply_to": row["reply_to"],
                        "resolved": row["resolved"],
                        "assignee": row["assignee"],
                    }
                    for row in data
                ]
                print(f"Loaded {_tickets} tickets from meta", flush=True)
            logger.info(f"Loaded {len(_tickets)} tickets from meta")
        urllib.request.urlretrieve(url, S3_KEY)
        logger.info(f"{S3_KEY} downloaded from S3")
    except Exception as e:
        logger.error(f"Failed to load {S3_KEY}: {e}")
        raise


async def s3_load_tickets(app: Application) -> None:
    try:
        with _lock:
            data = _tickets.copy()
        with open(TICKETS_META, "w") as f:
            json.dump(data, f, default=str)
        with open(TICKETS_META, "rb") as f:
            raw = f.read()
        requests.put(
            f"{BUCKET_URL}/{TICKETS_META}",
            data=raw,
            headers={"Content-Type": "application/json"},
        )
        logger.info("Saved tickets meta to S3")

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
        with _lock:
            data = _tickets.copy()
        with open(TICKETS_META, "w") as f:
            json.dump(data, f, default=str)
        with open(TICKETS_META, "rb") as f:
            raw = f.read()
        requests.put(
            f"{BUCKET_URL}/{TICKETS_META}",
            data=raw,
            headers={"Content-Type": "application/json"},
        )
        logger.info("Saved tickets meta to S3")

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
    with _lock:
        id = max(t["ticket_id"] for t in _tickets) + 1 if _tickets else 1
        ticket = {
            "ticket_id": id,
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
                    "Ответственный": "Никто",
                    "Статус": "Открыт",
                }
            ]
        )
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel("tickets.xlsx", sheet_name="tickets", index=False)
        _tickets.append(ticket)
    return ticket


def add_assignee(ticket_id: int, assignee: str) -> bool:
    """Add an assignee to a ticket. Returns True if found, False otherwise."""
    with _lock:
        df = pd.read_excel("tickets.xlsx", sheet_name="tickets")
        df.loc[df["Тикет"] == ticket_id, "Ответственный"] = assignee
        df.to_excel("tickets.xlsx", sheet_name="tickets", index=False)
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
    with _lock:
        df = pd.read_excel("tickets.xlsx", sheet_name="tickets")
        df.loc[df["Тикет"] == ticket_id, "Статус"] = "Закрыт"
        df.to_excel("tickets.xlsx", sheet_name="tickets", index=False)
        for ticket in _tickets:
            if ticket["ticket_id"] == ticket_id:
                ticket["resolved"] = True
                return True
    return False


def unresolve_ticket(ticket_id: int) -> bool:
    """Unmark a ticket as resolved. Returns False if found, True otherwise."""
    with _lock:
        df = pd.read_excel("tickets.xlsx", sheet_name="tickets")
        df.loc[df["Тикет"] == ticket_id, "Статус"] = "Открыт"
        df.to_excel("tickets.xlsx", sheet_name="tickets", index=False)
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
