import re

PII_PATTERNS = [
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"https?://[^\s\"']+"), "[URL]"),
    (re.compile(r"\b(?:0[1-9]|1[0-2])[/\-]\d{2}(?:\d{2})?\b"), "[СРОК_КАРТЫ]"),
    (re.compile(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b"), "[ВЛАДЕЛЕЦ]"),
    (
        re.compile(
            r"\b\d[\d\s]*(?:\.\d{1,2})?\s*(?:тенге|тнг|kzt|руб(?:лей)?|₽|usd|\$|eur|€)\b",
            re.IGNORECASE,
        ),
        "[СУММА]",
    ),
    (re.compile(r"\d{3,}"), "[НОМЕР]"),
]


def sanitize(text: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
