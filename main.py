import logging
import os
import queue
import re
import threading
from datetime import datetime, timedelta, timezone
 
from dotenv import load_dotenv
from google import genai
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)
 
load_dotenv()
 
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
 
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
 
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
 
SEPARATOR  = "─" * 60
SEPARATOR2 = "═" * 60
utc_plus_5 = timezone(timedelta(hours=5))
 
# ---------------------------------------------------------------------------
# Категории
# ---------------------------------------------------------------------------
 
CATEGORIES = {
    "Операционная работа": "⚙️",
    "Инциденты":           "🔥",
    "Интеграции":          "🔗",
}
CAT_KEYS = list(CATEGORIES.keys())
 
RULES: dict[str, list[str]] = {
    "Интеграции": [
        "интеграц", "webhook", "веб-хук", "api", "апи",
        "1с", "синхрониз", "коннект", "обмен данн",
        "не тянет", "не выгружа", "не загружа",
        "rest", "soap", "kafka", "rabbitmq", "sftp", "ftp",
        "токен", "ssl", "сертификат", "endpoint", "эндпоинт",
        "данные не приход", "не приходят данные",
    ],
    "Инциденты": [
        "не работает", "не работал", "упало", "упал",
        "недоступ", "ошибка", "error", "exception", "критич",
        "сломал", "сбой", "зависл", "зависан",
        "не открывает", "не запускает", "вылетает",
        "500", "404", "503", "502", "таймаут", "timeout",
        "аварий", "инцидент", "срочно", "горит",
        "пользователи не могут", "клиенты не могут",
        "встало", "всё упало", "все упало",
    ],
    "Операционная работа": [
        "как настро", "помогите настро", "настройк",
        "доступ", "предоставить доступ", "выдать доступ",
        "отчёт", "отчет", "выгрузка", "выгрузить",
        "инструкц", "подскажите", "как работает",
        "как пользоваться", "обновить", "изменить",
        "добавить пользователя", "удалить пользователя",
        "консультац", "вопрос", "уточни", "тест", "проверка",
    ],
}
 
PII_PATTERNS = [
    (re.compile(r"\+?\d[\d\s\-\(\)]{7,}\d"), "[ТЕЛЕФОН]"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b(?:ИИН|БИН|ИНН|КПП|ОГРН)\s*:?\s*\d{9,14}\b", re.IGNORECASE), "[ИД_НОМЕР]"),
    (re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"), "[КАРТА]"),
    (re.compile(r"(?:транзакц|платёж|invoice|счёт)\s*(?:№|#|N)?\s*\d+", re.IGNORECASE), "[ТРАНЗАКЦИЯ]"),
]
 
# Очередь: сюда echo() кладёт данные, консольный поток читает
confirm_queue: queue.Queue = queue.Queue()
 
 
def sanitize(text: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
 
 
# ---------------------------------------------------------------------------
# Классификаторы
# ---------------------------------------------------------------------------
 
def classify_rule_based(text: str) -> str:
    lower = text.lower()
    scores = {cat: 0 for cat in RULES}
    for cat, keywords in RULES.items():
        for kw in keywords:
            if kw in lower:
                scores[cat] += 1
    best = max(scores, key=lambda c: scores[c])
    return best if scores[best] > 0 else "Операционная работа"


def classify_gemini(text: str) -> str:
    SYSTEM_PROMPT = """Ты — система классификации обращений в техподдержку.
    Определи категорию обращения. Отвечай ТОЛЬКО одним из трёх значений (без кавычек):
    - Операционная работа — рутинные запросы: настройки, доступы, отчёты, консультации, вопросы о работе системы
    - Инциденты — сбои, ошибки, недоступность систем, критические проблемы
    - Интеграции — проблемы с API, webhook, обменом данных между системами, коннекторами

    Ответь строго одним из трёх значений выше."""
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Обращение: {sanitize(text)}"
    )
    try:
        response = gemini_client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )
        raw = response.text.strip()
        if raw in CATEGORIES:
            return raw
        for cat in CATEGORIES:
            if cat.lower() in raw.lower():
                return cat
        return ""
    except Exception as e:
        logger.warning(f"Gemini error: {e}")
        return ""


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
    both_match = (rule_cat == ai_cat == final)
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
        item = confirm_queue.get()  # блокируется до появления нового сообщения
        if item is None:
            break
 
        chat_title = item["chat_title"]
        sender     = item["sender"]
        text       = item["text"]
        ts         = item["ts"]
        rule_cat   = item["rule_cat"]
        ai_cat     = item["ai_cat"]
 
        print(format_incoming(chat_title, sender, text, ts, rule_cat, ai_cat), flush=True)
 
        # Ждём ввода (блокирующий — ок, т.к. это отдельный поток)
        try:
            raw = input("\n> ").strip()
        except EOFError:
            raw = ""
 
        if raw in ("1", "2", "3"):
            final = CAT_KEYS[int(raw) - 1]
        else:
            print("  Неверный ввод, введите 1, 2 или 3.", flush=True)
            continue
 
        print(format_confirmed(chat_title, sender, text, ts, rule_cat, ai_cat, final), flush=True)
 
 
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
 
    if message.from_user:
        user = message.from_user
        sender = user.full_name or user.username or f"User {user.id}"
    elif message.sender_chat:
        sender = message.sender_chat.title or f"Chat {message.sender_chat.id}"
    else:
        sender = "Неизвестный"
 
    text      = message.text or message.caption or "[медиа без текста]"
    timestamp = message.date
 
    rule_cat = classify_rule_based(text)
    ai_cat   = classify_gemini(text)
 
    confirm_queue.put({
        "chat_title": chat_title,
        "sender":     sender,
        "text":       text,
        "ts":         timestamp,
        "rule_cat":   rule_cat,
        "ai_cat":     ai_cat,
    })
 
 
# ---------------------------------------------------------------------------
# Запуск
# ---------------------------------------------------------------------------
 
def main():
    # Запускаем консольный поток
    worker = threading.Thread(target=console_worker, daemon=True)
    worker.start()
 
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, echo))
    logger.info("Bot is running — press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
 
 
if __name__ == "__main__":
    main()