from __future__ import annotations

import re

from app.utils import escape_html


def _highlight_title(title: str, matched_keywords: list[str]) -> str:
    if not matched_keywords:
        return escape_html(title)

    escaped_keywords = [re.escape(keyword) for keyword in matched_keywords if keyword]
    if not escaped_keywords:
        return escape_html(title)

    pattern = re.compile("|".join(sorted(escaped_keywords, key=len, reverse=True)), re.IGNORECASE)
    last_end = 0
    parts: list[str] = []
    for match in pattern.finditer(title):
        start, end = match.span()
        if start < last_end:
            continue
        parts.append(escape_html(title[last_end:start]))
        parts.append(f"<u>{escape_html(title[start:end])}</u>")
        last_end = end
    parts.append(escape_html(title[last_end:]))
    return "".join(parts)


class MessageFormatter:
    def render(
        self,
        *,
        title: str,
        link: str,
        matched_keywords: list[str],
        category_name: str,
    ) -> str:
        highlighted_title = _highlight_title(title, matched_keywords)
        keywords_text = escape_html(",".join(matched_keywords) if matched_keywords else "未命中")
        category_text = escape_html(category_name)
        link_text = escape_html(link)
        return (
            f"<b>{highlighted_title}</b>\n\n"
            f"⚡️关键词：<code>{keywords_text}</code>\n"
            f"🏷️板块：<code>{category_text}</code>\n"
            f'🔗 <a href="{link_text}">查看原帖</a>'
        ).strip()
