from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_TEMPLATE = (
    "<b>{title}</b>\n\n"
    "{summary}\n\n"
    "关键词：<code>{matched_keywords}</code>\n"
    "发布时间：<code>{published_at}</code>\n"
    '<a href="{link}">打开原帖</a>\n'
    "<i>{feed_title}</i>"
)


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_owner_ids(value: str | None) -> tuple[int, ...]:
    if not value:
        return tuple()
    result = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        result.append(int(item))
    return tuple(result)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_path: Path
    max_subscriptions_per_user: int
    poll_interval_seconds: int
    http_timeout_seconds: int
    max_entries_per_feed: int
    max_summary_length: int
    default_target_chat_id: int | None
    mark_as_read_on_first_poll: bool
    disable_web_page_preview: bool
    log_level: str
    message_template: str
    bot_owner_ids: tuple[int, ...]

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()

        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError("BOT_TOKEN 未配置，请先复制 .env.example 为 .env 并填写。")

        database_path = Path(os.getenv("DATABASE_PATH", "data/bot.db"))
        database_path.parent.mkdir(parents=True, exist_ok=True)

        default_chat = os.getenv("DEFAULT_TARGET_CHAT_ID", "").strip()
        message_template = os.getenv("MESSAGE_TEMPLATE", DEFAULT_TEMPLATE).replace("\\n", "\n")

        return cls(
            bot_token=bot_token,
            database_path=database_path,
            max_subscriptions_per_user=int(os.getenv("MAX_SUBSCRIPTIONS_PER_USER", "20")),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "180")),
            http_timeout_seconds=int(os.getenv("HTTP_TIMEOUT_SECONDS", "20")),
            max_entries_per_feed=int(os.getenv("MAX_ENTRIES_PER_FEED", "15")),
            max_summary_length=int(os.getenv("MAX_SUMMARY_LENGTH", "280")),
            default_target_chat_id=int(default_chat) if default_chat else None,
            mark_as_read_on_first_poll=_parse_bool(os.getenv("MARK_AS_READ_ON_FIRST_POLL"), True),
            disable_web_page_preview=_parse_bool(os.getenv("DISABLE_WEB_PAGE_PREVIEW"), False),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            message_template=message_template,
            bot_owner_ids=_parse_owner_ids(os.getenv("BOT_OWNER_IDS")),
        )
