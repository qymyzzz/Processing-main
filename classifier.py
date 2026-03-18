import os
import re

from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# Категории
# ---------------------------------------------------------------------------

CATEGORIES = {
    "Операционная работа": "⚙️",
    "Инциденты": "🔥",
    "Интеграции": "🔗",
}
CAT_KEYS = list(CATEGORIES.keys())

RULES: dict[str, list[str]] = {
    "Интеграции": [
        "интеграц",
        "webhook",
        "веб-хук",
        "api",
        "апи",
        "1с",
        "синхрониз",
        "коннект",
        "обмен данн",
        "не тянет",
        "не выгружа",
        "не загружа",
        "rest",
        "soap",
        "kafka",
        "rabbitmq",
        "sftp",
        "ftp",
        "токен",
        "ssl",
        "сертификат",
        "endpoint",
        "эндпоинт",
        "данные не приход",
        "не приходят данные",
    ],
    "Инциденты": [
        "не работает",
        "не работал",
        "упало",
        "упал",
        "недоступ",
        "ошибка",
        "error",
        "exception",
        "критич",
        "сломал",
        "сбой",
        "зависл",
        "зависан",
        "не открывает",
        "не запускает",
        "вылетает",
        "500",
        "404",
        "503",
        "502",
        "таймаут",
        "timeout",
        "аварий",
        "инцидент",
        "срочно",
        "горит",
        "пользователи не могут",
        "клиенты не могут",
        "встало",
        "всё упало",
        "все упало",
    ],
    "Операционная работа": [
        "как настро",
        "помогите настро",
        "настройк",
        "доступ",
        "предоставить доступ",
        "выдать доступ",
        "отчёт",
        "отчет",
        "выгрузка",
        "выгрузить",
        "инструкц",
        "подскажите",
        "как работает",
        "как пользоваться",
        "обновить",
        "изменить",
        "добавить пользователя",
        "удалить пользователя",
        "консультац",
        "вопрос",
        "уточни",
        "тест",
        "проверка",
    ],
}

PII_PATTERNS = [
    (re.compile(r"\+?\d[\d\s\-\(\)]{7,}\d"), "[ТЕЛЕФОН]"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (
        re.compile(r"\b(?:ИИН|БИН|ИНН|КПП|ОГРН)\s*:?\s*\d{9,14}\b", re.IGNORECASE),
        "[ИД_НОМЕР]",
    ),
    (re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"), "[КАРТА]"),
    (
        re.compile(
            r"(?:транзакц|платёж|invoice|счёт)\s*(?:№|#|N)?\s*\d+", re.IGNORECASE
        ),
        "[ТРАНЗАКЦИЯ]",
    ),
]


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
    prompt = f"{SYSTEM_PROMPT}\n\n" f"Обращение: {sanitize(text)}"
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
