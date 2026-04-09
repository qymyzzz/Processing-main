import io
import logging
import os
import threading
from datetime import datetime

import dotenv
import pandas as pd
import requests
import xlwings as xw

from logging_config import logger
from message_history import get_messages

_tickets: list[dict] = [
    # {
    #     "ticket_id": 1,
    #     "message_id": 430,
    #     "chat_id": -1003704201117,
    #     "chat_title": "test5",
    #     "sender": "qymyzzz",
    #     "text": "не работает API",
    #     "timestamp": "2026-04-02 15:34:33",
    #     "rule_cat": "Интеграции",
    #     "ai_cat": None,
    #     "final_cat": "Интеграции",
    #     "created_at": datetime(2026, 4, 2, 15, 34, 41, 996135),
    #     "reply_to": None,
    #     "resolved": False,
    # },
    # {
    #     "ticket_id": 2,
    #     "message_id": 578,
    #     "chat_id": -1003704201117,
    #     "chat_title": "test5",
    #     "sender": "qymyzzz",
    #     "text": "asdfoiasdfasd",
    #     "timestamp": "2026-03-25 15:34:33",
    #     "rule_cat": "Интеграции",
    #     "ai_cat": None,
    #     "final_cat": "Интеграции",
    #     "created_at": datetime(2026, 3, 25, 15, 34, 41, 996135),
    #     "reply_to": None,
    #     "resolved": False,
    # },
    # {
    #     "ticket_id": 3,
    #     "message_id": 124,
    #     "chat_id": -1003704201117,
    #     "chat_title": "test5",
    #     "sender": "qymyzzz",
    #     "text": "asfioasfdjsd",
    #     "timestamp": "2026-03-02 15:34:33",
    #     "rule_cat": "Интеграции",
    #     "ai_cat": None,
    #     "final_cat": "Интеграции",
    #     "created_at": datetime(2026, 3, 2, 15, 34, 41, 996135),
    #     "reply_to": None,
    #     "resolved": False,
    # },
]
_lock = threading.Lock()
wb = xw.Book("tickets.xlsx")
sht = wb.sheets["tickets"]

dotenv.load_dotenv()

BUCKET_URL = os.getenv("BUCKET_URL")
S3_KEY = os.getenv("S3_KEY")


def _sync_to_s3():
    """Save workbook to a buffer and upload to S3."""
    try:
        buf = io.BytesIO()
        wb.save(buf)  # xlwings can save to a file-like object
        buf.seek(0)
        resp = requests.put(
            f"{BUCKET_URL}/{S3_KEY}",
            data=buf,
            headers={
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
        )
        if resp.status_code == 200:
            logger.info("tickets.xlsx synced to S3")
        else:
            logger.warning(f"S3 upload failed: {resp.status_code}")
    except Exception as e:
        logger.error(f"S3 sync error: {e}")


def _sync_to_s3():
    try:
        wb.save("tickets.xlsx")  # flush xlwings changes to disk
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
        logger.error(f"S3 sync error: {e}")


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
        "ticket_id": len(_tickets) + 1,  # simple incrementing ID
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
    df = sht.range("A1").expand().options(pd.DataFrame, index=False).value
    df.loc[len(df)] = [
        id,
        chat_title,
        sender,
        text,
        rule_cat,
        timestamp,
        "Никто",
        "Открыт",
    ]
    sht.range("A1").expand().clear_contents()
    sht.range("A1").options(index=False).value = df
    _sync_to_s3()
    with _lock:
        _tickets.append(ticket)
    return ticket


def add_assignee(ticket_id: int, assignee: str) -> bool:
    """Add an assignee to a ticket. Returns True if found, False otherwise."""
    df = sht.range("A1").expand().options(pd.DataFrame, index=False).value
    df.loc[df["Тикет"] == ticket_id, "Ответсвтенный"] = assignee
    sht.range("A1").expand().clear_contents()
    sht.range("A1").options(index=False).value = df
    _sync_to_s3()
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
    df = sht.range("A1").expand().options(pd.DataFrame, index=False).value
    df.loc[df["Тикет"] == ticket_id, "Статус"] = "Закрыт"
    sht.range("A1").expand().clear_contents()
    sht.range("A1").options(index=False).value = df
    _sync_to_s3()
    with _lock:
        for ticket in _tickets:
            if ticket["ticket_id"] == ticket_id:
                ticket["resolved"] = True
                return True
    return False


def unresolve_ticket(ticket_id: int) -> bool:
    """Unmark a ticket as resolved. Returns False if found, True otherwise."""
    df = sht.range("A1").expand().options(pd.DataFrame, index=False).value
    df.loc[df["Тикет"] == ticket_id, "Статус"] = "Открыт"
    sht.range("A1").expand().clear_contents()
    sht.range("A1").options(index=False).value = df
    _sync_to_s3()
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
    current_messages = get_messages(chat_id)  # последние 500
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
    # print("these dates:", date_from, date_to)
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
