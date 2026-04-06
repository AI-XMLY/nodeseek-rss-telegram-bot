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
        parts.append(f"{escape_html(title[start:end])}")
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
        keywords_text = escape_html("  ".join(matched_keywords) if matched_keywords else "未命中")
        category_text = escape_html(category_name)
        link_text = escape_html(link)
        return (
            f'<a href="{link_text}"><b>{highlighted_title}</b></a>\n'
            f"⚡️⚡️⚡️ 关键词： {keywords_text}\n"
            f"🏷️🏷️🏷️ 板   块： <u>{category_text}</u>"
        ).strip()
