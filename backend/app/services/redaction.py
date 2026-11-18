"""
Sensitive Data Redaction Service (Module 3)
Sanitizes raw log inputs to prevent PCI-DSS and PII violations before storage and LLM consumption.
"""
import re
from typing import Tuple

# Regex Patterns for Sensitive Data Detection
CARD_PAN_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,19}\b')
CVV_PATTERN = re.compile(r'(?i)\b(?:cvv|cvc|security[_-]?code)[\s:=]+([0-9]{3,4})\b')
AUTH_HEADER_PATTERN = re.compile(r'(?i)(Authorization|Bearer|token|apiKey|api_key|client_secret)[\s:=]+([a-zA-Z0-9_\-\.]{16,})')
PASSWORD_PATTERN = re.compile(r'(?i)(password|passwd|pwd|secret)[\s:=]+(["\']?[^"\'\s,;]{4,}["\']?)')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
PHONE_PATTERN = re.compile(r'(?:\+91[\-\s]?)?[6-9]\d{9}\b')


def _mask_card(match: re.Match) -> str:
    raw = match.group(0).replace(" ", "").replace("-", "")
    # Check simple length for credit card simulation
    if 13 <= len(raw) <= 19 and raw.isdigit():
        last_4 = raw[-4:]
        return f"[REDACTED_CARD_PAN_************{last_4}]"
    return match.group(0)


def redact_text(text: str) -> Tuple[str, bool]:
    """
    Scans and redacts sensitive tokens from log messages.
    Returns: (redacted_text, was_redacted)
    """
    if not text:
        return text, False

    original = text
    redacted = text

    # Redact Authorization / Bearer tokens
    redacted = AUTH_HEADER_PATTERN.sub(r'\1: [REDACTED_API_TOKEN]', redacted)

    # Redact Passwords
    redacted = PASSWORD_PATTERN.sub(r'\1="[REDACTED_SECRET]"', redacted)

    # Redact CVVs
    redacted = CVV_PATTERN.sub(r'cvv: [REDACTED_CVV]', redacted)

    # Redact Credit Cards
    redacted = CARD_PAN_PATTERN.sub(_mask_card, redacted)

    # Redact Emails
    redacted = EMAIL_PATTERN.sub(r'[REDACTED_EMAIL]', redacted)

    # Redact Phone Numbers
    redacted = PHONE_PATTERN.sub(r'[REDACTED_PHONE]', redacted)

    was_redacted = (redacted != original)
    return redacted, was_redacted
