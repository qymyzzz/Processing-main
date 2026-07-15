import re
import phonenumbers
from phonenumbers import PhoneNumberMatcher


def label_phone_numbers(text, region=None, replacement="[НОМЕР ТЕЛЕФОНА]"):
    matcher = list(PhoneNumberMatcher(text, region))
    masked_text = text
    for match in reversed(matcher):
        start = match.start
        end = match.end
        masked_text = masked_text[:start] + replacement + masked_text[end:]

    return masked_text


def sanitize(text: str) -> str:
    # text = re.compile(r"\b(?:0[1-9]|1[0-2])[/\-]\d{2}(?:\d{2})?\b").sub(
    #     "[СРОК_КАРТЫ]", text
    # )
    # text = re.compile(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b").sub("[ВЛАДЕЛЕЦ]", text)
    # EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
    # text = EMAIL_RE.sub("[EMAIL]", text)
    # text = re.sub(
    #     r"(?<!\d)(?:CVV?2?|CVC2?|CVC|CID|security\s+code)[:\s]+(\d{3,4})(?!\d)",
    #     "[CVV]",
    #     text,
    #     flags=re.IGNORECASE,
    # )
    # text = re.sub(
    #     r"(?<!\d)(\d{3,4})(?!\d)[:\s]+(?:CVV?2?|CVC2?|CVC|CID|security\s+code)",
    #     "[CVV]",
    #     text,
    #     flags=re.IGNORECASE,
    # )
    # text = re.sub(
    #     r"4[0-9]{3}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}",
    #     "[VISA PAN]",
    #     text,
    # )
    # text = re.sub(
    #     r"(5[1-5][0-9]{2}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}|2(22[1-9][-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}|2[3-9][0-9]{1}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}|[3-6][0-9]{2}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}|7[0-1][0-9]{1}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}|720[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}[-\s]{0,2}[0-9]{4}))",
    #     "[MASTERCARD PAN]",
    #     text,
    # )
    # text = re.sub(
    #     r"^\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[3-6]\d{4}\d$", "[ИИН]", text
    # )
    # text = re.sub(r"^\d{2}(0[1-9]|1[0-2])[4-6]\d{7}$", "[БИН]", text)
    # text = label_phone_numbers(text, region="KZ", replacement="[НОМЕР ТЕЛЕФОНА]")
    return text
