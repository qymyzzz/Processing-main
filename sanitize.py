import re

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
