import json
import os
import threading
import time
from collections import deque

from dotenv import load_dotenv
from google import genai

from .categories import CAT_KEYS, CATEGORIES
from .logging_config import logger
from .message_history import get_messages
from .rules import RULES
from .sanitize import sanitize
from .ticket_store import add_ticket, get_ticket, get_tickets, resolve_ticket

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 15]

_retry_queue: deque = deque()
_retry_queue_lock = threading.Lock()


def _call_gemini(prompt: str) -> tuple:
    response = gemini_client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    raw = response.text.strip()
    parsed = json.loads(raw)
    status = parsed.get("status")
    ticket_id = parsed.get("ticket_id")
    if status not in {0, 1, 2, 3, 4}:
        raise ValueError(f"Unexpected status: {status}")
    return status, ticket_id


def _call_gemini_with_retry(prompt: str) -> tuple:
    for attempt in range(MAX_RETRIES):
        try:
            return _call_gemini(prompt)
        except Exception as e:
            delay = RETRY_DELAYS[attempt]
            logger.warning(
                f"Gemini error (attempt {attempt + 1}/{MAX_RETRIES}), "
                f"retrying in {delay}s: {e}"
            )
            time.sleep(delay)

    logger.error(f"Gemini failed after {MAX_RETRIES} retries, queuing request.")
    return None, None


def flush_retry_queue():
    with _retry_queue_lock:
        items = list(_retry_queue)
        _retry_queue.clear()

    for prompt in items:
        logger.info("Retrying queued Gemini request...")
        _call_gemini_with_retry(prompt)


def generate_new_ticket(
    chat_id: int,
    sender: str,
    text: str,
    timestamp: str,
    rule_cat: str,
    ai_cat: str,
    final_cat: str,
    reply_to: dict | None = None,
) -> str:
    raw_tickets = get_tickets(chat_id=chat_id)
    # print(raw_tickets, flush=True)
    exclude = {"message_id", "chat_id", "chat_title", "created_at", "assignee"}
    cleaned_tickets = []
    for t in raw_tickets:
        ticket = {k: v for k, v in t.items() if k not in exclude}
        if "text" in ticket:
            ticket["text"] = sanitize(ticket["text"])
        if ticket.get("reply_to") and "text" in ticket["reply_to"]:
            ticket["reply_to"]["text"] = sanitize(ticket["reply_to"]["text"])
            if "message_id" in ticket["reply_to"]:
                del ticket["reply_to"]["message_id"]
        cleaned_tickets.append(ticket)

    tickets_json = json.dumps(cleaned_tickets, ensure_ascii=False, indent=2)

    history_not_cleared = get_messages(chat_id)
    exclude1 = {"message_id", "chat_id", "chat_title"}

    history = [
        {k: v for k, v in msg.items() if k not in exclude1}
        for msg in history_not_cleared
    ]
    history = history[-100:]
    cleaned_list = []
    for msg in history:
        new_msg = {k: v for k, v in msg.items() if k not in exclude1}
        if "text" in new_msg:
            new_msg["text"] = sanitize(new_msg["text"])
        if new_msg.get("reply_to") and "text" in new_msg["reply_to"]:
            new_msg["reply_to"]["text"] = sanitize(new_msg["reply_to"]["text"])
            if "message_id" in new_msg["reply_to"]:
                del new_msg["reply_to"]["message_id"]
        cleaned_list.append(new_msg)
    history_json = json.dumps(cleaned_list, ensure_ascii=False, indent=2)
    SYSTEM_PROMPT = """Ты — классификатор сообщений в чате между мерчантами и техподдержкой.

    Тебе будет передано:
    - Список существующих тикетов (обращений) из этого чата: ticket_id, sender, text, timestamp, rule_cat, ai_cat, final_cat, reply_to, resolved
    - История последних 100 сообщений чата: sender, text, timestamp, rule_cat, ai_cat, final_cat, reply_to
    - Новое сообщение, которое только что поступило

    Используй строго следующую логику:

    **Шаг 1. Является ли это рабочим сообщением?**
    Рабочим сообщением НЕ являются: приветствия, прощания, пустой small talk.
    Если нет → status=0, ticket_id=null

    **Шаг 2. Является ли это решением существующего тикета?**
    Решение — это ответ техподдержки или мерчанта, который явно закрывает проблему (например: "спасибо", "починили", "всё работает", "проблема решена").
    Если да → status=3, ticket_id=<id тикета который решается>

    **Шаг 3. Является ли это повторным открытием закрытого тикета?**
    Повторное открытие — это когда тикет уже закрыт (resolved=true), но новое сообщение возвращается к той же проблеме или теме.
    Признаки: та же проблема что в закрытом тикете, возможно тот же или другой человек, тема узнаваема даже если сформулирована иначе.
    Если да → status=4, ticket_id=<id закрытого тикета который переоткрывается>

    **Шаг 4. Является ли это продолжением открытого тикета?**
    Продолжение — новое сообщение развивает или уточняет проблему из ещё открытого тикета.
    Правила поиска связи:
    - Тикет не обязательно от того же человека
    - Связь определяется по смыслу и теме, а не по точному совпадению текста
    - Поиск ведётся в глубину последних 100 сообщений чата — если между тикетом и новым сообщением 100+ сообщений флуда без связи, это НЕ продолжение
    Если да → status=1, ticket_id=<id найденного тикета>

    **Шаг 5. Новое обращение**
    Если ни один из шагов выше не сработал → это новый тикет.
    Если да → status=2, ticket_id=null

    Примеры:
    ✅ Продолжение (1): открытый тикет, другой человек пишет о той же проблеме
    ✅ Решение (3): "всё заработало", "спасибо, починили" в ответ на существующий тикет
    ✅ Переоткрытие (4): тикет закрыт, но человек снова пишет по той же теме
    ❌ Новое (2): тема другая, даже если тот же отправитель
    ❌ Новое (2): тема совпадает, но между тикетом и новым сообщением 100+ сообщений флуда

    Отвечай ТОЛЬКО в формате JSON, без какого-либо другого текста:
    {"status": <0|1|2|3|4>, "ticket_id": <id или null>}"""

    reply_to_json = (
        json.dumps(
            {"sender": reply_to.get("sender"), "text": sanitize(reply_to["text"])},
            ensure_ascii=False,
        )
        if reply_to
        else "null"
    )

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Список тикетов: {tickets_json if cleaned_tickets else 'Тикетов нет'}\n\n"
        f"История чата: {history_json if cleaned_list else 'История чата пуста'}\n\n"
        f"Новое сообщение: {{\n"
        f"  sender: {sender},\n"
        f"  text: {sanitize(text)},\n"
        f"  timestamp: {timestamp},\n"
        f"  rule_cat: {rule_cat},\n"
        f"  ai_cat: {ai_cat},\n"
        f"  final_cat: {final_cat}\n"
        f"  reply_to: {reply_to_json if reply_to and reply_to['text'] is not None else 'null'}\n"
        f"}}"
    )
    # print(tickets_json, flush=True)
    # print(history_json, flush=True)
    return _call_gemini_with_retry(prompt)
