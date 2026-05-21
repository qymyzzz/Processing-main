import os

from dotenv import load_dotenv
from google import genai

from .categories import CAT_KEYS, CATEGORIES
from .logging_config import logger
from .rules import RULES
from .sanitize import sanitize

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


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
