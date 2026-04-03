from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    plain = TAG_RE.sub(" ", html.unescape(value))
    return SPACE_RE.sub(" ", plain).strip()


def normalize_keywords(raw_keywords: str | None) -> list[str]:
    if not raw_keywords:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for keyword in raw_keywords.split(","):
        cleaned = keyword.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def format_datetime(value: str | None) -> str:
    if not value:
        return "未知"
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def truncate_text(value: str, max_length: int) -> str:
    value = value.strip()
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def escape_html(value: str) -> str:
    return html.escape(value, quote=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
