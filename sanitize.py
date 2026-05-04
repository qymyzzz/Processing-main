import re


def sanitize(text: str) -> str:
    def mask_PANs(m):
        s = m.group()
        digits_only = re.sub(r"[\s-]", "", s)
        if len(digits_only) < 13 or len(digits_only) > 19:
            return s

        digits_seen = 0
        result = []
        for char in reversed(s):
            if char.isdigit():
                digits_seen += 1
                result.append(char if digits_seen <= 4 else "*")
            else:
                result.append(char)
        return "".join(reversed(result))

    text = re.compile(r"\b(?:0[1-9]|1[0-2])[/\-]\d{2}(?:\d{2})?\b").sub(
        "[СРОК_КАРТЫ]", text
    )
    text = re.compile(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b").sub("[ВЛАДЕЛЕЦ]", text)
    EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
    text = EMAIL_RE.sub("[EMAIL]", text)
    PHONE_RE1 = re.compile(
        r"(?<![.\d])"
        r"\+[1-9]\d{0,3}"
        r"[\s.\-]?"
        r"\(?\d{1,4}\)?"
        r"[\s.\-]?"
        r"\d{1,4}"
        r"[\s.\-]?"
        r"\d{1,4}"
        r"(?:[\s.\-]?\d{1,4})"
        r"(?!\d)"
    )

    PHONE_RE2 = re.compile(
        r"(?<![.\d])"
        r"[1-9]\d{0,3}"
        r"[\s.\-]?"
        r"\(?\d{1,4}\)?"
        r"[\s.\-]?"
        r"\d{1,4}"
        r"[\s.\-]?"
        r"\d{1,4}"
        r"(?:[\s.\-]?\d{1,4})"
        r"(?!\d)"
    )
    text = PHONE_RE1.sub("[НОМЕР ТЕЛЕФОНА]", text)
    text = re.sub(
        r"(?<!\d)(?:CVV?2?|CVC2?|CVC|CID|security\s+code)[:\s]+(\d{3,4})(?!\d)",
        "[CVV]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?<!\d)(\d{3,4})(?!\d)[:\s]+(?:CVV?2?|CVC2?|CVC|CID|security\s+code)",
        "[CVV]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\d[\d\s-]{11,17}\d", mask_PANs, text)
    text = re.sub(r"(?<!\d)\d{12}(?!\d)", "[ИИН или БИН]", text)
    text = PHONE_RE2.sub("[НОМЕР ТЕЛЕФОНА]", text)
    return text
