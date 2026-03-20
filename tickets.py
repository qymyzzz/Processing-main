import json
import os

from dotenv import load_dotenv
from google import genai

from categories import CAT_KEYS, CATEGORIES
from logging_config import logger
from message_history import get_messages
from rules import RULES
from sanitize import sanitize
from ticket_store import add_ticket, get_ticket, get_tickets, resolve_ticket

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def generate_new_ticket(
    chat_id: int,
    sender: str,
    text: str,
    timestamp: str,
    rule_cat: str,
    ai_cat: str,
    final_cat: str,
) -> str:
    raw_tickets = get_tickets(chat_id=chat_id, resolved=False)

    exclude = {"message_id", "chat_id", "chat_title", "created_at", "resolved"}
    cleaned_tickets = []
    for t in raw_tickets:
        ticket = {k: v for k, v in t.items() if k not in exclude}
        if "text" in ticket:
            ticket["text"] = sanitize(ticket["text"])
        cleaned_tickets.append(ticket)

    # print(cleaned_tickets, flush=True)
    tickets_json = json.dumps(cleaned_tickets, ensure_ascii=False, indent=2)

    history_not_cleared = get_messages(chat_id)
    exclude1 = {
        "message_id",
        "chat_id",
        "chat_title",
    }

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

        cleaned_list.append(new_msg)
    history_json = json.dumps(cleaned_list, ensure_ascii=False, indent=2)

    SYSTEM_PROMPT = """Ты — классификатор сообщений в чате между мерчантами и техподдержкой.

    Тебе будет передано:
    - Список существующих тикетов (обращений) из этого чата: ticket_id, sender, text, timestamp, rule_cat, ai_cat, final_cat
    - История последних 100 сообщений чата: sender, text, timestamp, rule_cat, ai_cat, final_cat
    - Новое сообщение, которое только что поступило

    Используй строго следующую логику:

    **Шаг 1. Является ли это рабочим сообщением?**
    Рабочим сообщением НЕ являются: приветствия, прощания, подтверждения ("ок", "понял"), пустой small talk.
    Если нет → status=0, ticket_id=null

    **Шаг 2. Является ли это решением существующего тикета?**
    Решение — это ответ техподдержки или мерчанта, который закрывает проблему из тикета (например: "починили", "всё работает", "проблема решена").
    Если да → status=3, ticket_id=<id тикета который решается>

    **Шаг 3. Является ли это продолжением существующего тикета?**
    Просмотри список тикетов и определи, связано ли новое сообщение с одним из них.

    Правила поиска связи:
    - Тикет должен быть из того же чата
    - Тикет не обязательно от того же человека
    - Тикет может быть закрыт — если человек обращается по той же теме повторно, это считается продолжением
    - Связь определяется по смыслу и теме, а не по точному совпадению текста
    - Поиск ведётся в глубину последних 100 сообщений чата

    Если связанный тикет найден → status=1, ticket_id=<id найденного тикета>
    Если связанного тикета нет → status=2, ticket_id=null

    Примеры:
    Продолжение (1): тикет закрыт, но человек пишет снова по той же проблеме
    Продолжение (1): другой человек пишет о той же проблеме что и в существующем тикете
    Решение (3): "всё заработало", "спасибо, починили" в ответ на существующий тикет
    Новое (2): тема другая, даже если тот же отправитель
    Новое (2): тема совпадает, но между тикетом и новым сообщением прошло 100+ сообщений флуда без связи

    Отвечай ТОЛЬКО в формате JSON, без какого-либо другого текста:
    {"status": <0|1|2|3>, "ticket_id": <id или null>}"""

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
        f"}}"
    )
    try:
        response = gemini_client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )
        raw = response.text.strip()
        parsed = json.loads(raw)

        status = parsed.get("status")
        ticket_id = parsed.get("ticket_id")

        if status not in {0, 1, 2, 3}:
            logger.warning(f"Unexpected Gemini status: {status}")
            return None, None

        return status, ticket_id
    except Exception as e:
        logger.warning(f"Gemini error: {e}")
        return None, None
