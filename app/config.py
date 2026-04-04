from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


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
    rss_url: str
    max_keywords_per_user: int
    max_targets_per_user: int
    history_limit: int
    poll_interval_seconds: int
    http_timeout_seconds: int
    max_entries_per_feed: int
    mark_as_read_on_first_poll: bool
    disable_web_page_preview: bool
    log_level: str
    bot_owner_ids: tuple[int, ...]

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()

        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError("BOT_TOKEN 未配置，请先复制 .env.example 为 .env 并填写。")

        database_path = Path(os.getenv("DATABASE_PATH", "data/bot.db"))
        database_path.parent.mkdir(parents=True, exist_ok=True)

        return cls(
            bot_token=bot_token,
            database_path=database_path,
            rss_url=os.getenv("RSS_URL", "https://rss.nodeseek.com/").strip(),
            max_keywords_per_user=int(
                os.getenv(
                    "MAX_KEYWORDS_PER_USER",
                    os.getenv("MAX_SUBSCRIPTIONS_PER_USER", "50"),
                )
            ),
            max_targets_per_user=int(os.getenv("MAX_TARGETS_PER_USER", "10")),
            history_limit=int(os.getenv("HISTORY_LIMIT", "10")),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "180")),
            http_timeout_seconds=int(os.getenv("HTTP_TIMEOUT_SECONDS", "20")),
            max_entries_per_feed=int(os.getenv("MAX_ENTRIES_PER_FEED", "30")),
            mark_as_read_on_first_poll=_parse_bool(os.getenv("MARK_AS_READ_ON_FIRST_POLL"), True),
            disable_web_page_preview=_parse_bool(os.getenv("DISABLE_WEB_PAGE_PREVIEW"), False),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            bot_owner_ids=_parse_owner_ids(os.getenv("BOT_OWNER_IDS")),
        )
