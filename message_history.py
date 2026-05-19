import threading
from collections import deque
import os
from telegram.ext import Application
import json
from logging_config import logger
import urllib.request
import requests

MAX_MESSAGES = 500
BUCKET_URL = os.getenv("BUCKET_URL")
MESSAGES_META = os.getenv("MESSAGES_META")

_store: dict[int, deque] = {}
_lock = threading.Lock()


def _load_from_s3() -> dict:
    url = f"{BUCKET_URL}/{MESSAGES_META}"
    try:
        urllib.request.urlretrieve(url, MESSAGES_META)
        with open(MESSAGES_META, "r") as f:
            return json.load(f)
    except Exception:
        return {}


async def s3_load_messages(app: Application) -> None:
    with _lock:
        data = {str(chat_id): list(msgs) for chat_id, msgs in _store.items()}
    with open(MESSAGES_META, "w") as f:
        json.dump(data, f)
    with open(MESSAGES_META, "rb") as f:
        raw = f.read()
    requests.put(
        f"{BUCKET_URL}/{MESSAGES_META}",
        data=raw,
        headers={"Content-Type": "application/json"},
    )
    logger.info("Saved message history to S3")


def s3_load_messages_sync():
    with _lock:
        data = {str(chat_id): list(msgs) for chat_id, msgs in _store.items()}
    with open(MESSAGES_META, "w") as f:
        json.dump(data, f)
    with open(MESSAGES_META, "rb") as f:
        raw = f.read()
    requests.put(
        f"{BUCKET_URL}/{MESSAGES_META}",
        data=raw,
        headers={"Content-Type": "application/json"},
    )
    logger.info("Saved message history to S3")


def _init_messages():
    data = _load_from_s3()
    with _lock:
        for chat_id_str, messages in data.items():
            chat_id = int(chat_id_str)
            _store[chat_id] = deque(messages, maxlen=MAX_MESSAGES)
    logger.info(f"Loaded message history for {len(_store)} chats from S3")


def add_message(
    chat_id: int,
    chat_title: str,
    sender: str,
    text: str,
    timestamp: str,
    rule_cat: str,
    ai_cat: str,
    message_id: int,
    final_cat: str,
    reply_to: dict | None = None,
) -> None:
    entry = {
        "message_id": message_id,
        "chat_id": chat_id,
        "chat_title": chat_title,
        "sender": sender,
        "text": text,
        "timestamp": timestamp,
        "rule_cat": rule_cat,
        "ai_cat": ai_cat,
        "final_cat": final_cat,
        "reply_to": reply_to,
    }
    with _lock:
        if chat_id not in _store:
            _store[chat_id] = deque(maxlen=MAX_MESSAGES)
        _store[chat_id].append(entry)


def get_messages(chat_id: int) -> list:
    with _lock:
        return list(_store.get(chat_id, []))


def get_all_chats() -> dict[int, list]:
    with _lock:
        return {chat_id: list(msgs) for chat_id, msgs in _store.items()}
