import threading
from collections import deque

MAX_MESSAGES = 500

_store: dict[int, deque] = {}
_lock = threading.Lock()


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
