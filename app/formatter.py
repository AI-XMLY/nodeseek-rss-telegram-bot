from __future__ import annotations

from app.config import Settings
from app.utils import escape_html


class MessageFormatter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def render(
        self,
        *,
        title: str,
        summary: str,
        link: str,
        feed_title: str,
        matched_keywords: list[str],
        published_at: str,
    ) -> str:
        values = {
            "title": escape_html(title),
            "summary": escape_html(summary),
            "link": escape_html(link),
            "feed_title": escape_html(feed_title),
            "matched_keywords": escape_html(", ".join(matched_keywords) if matched_keywords else "未设置"),
            "published_at": escape_html(published_at),
        }
        return self.settings.message_template.format(**values).strip()

