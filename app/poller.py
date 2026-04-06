from __future__ import annotations

import asyncio
import logging

from telegram import Bot, LinkPreviewOptions

from app.config import Settings
from app.db import Database, PollingUserRecord
from app.formatter import MessageFormatter
from app.rss import FeedClient, match_keywords

logger = logging.getLogger(__name__)


class FeedPoller:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db
        self.feed_client = FeedClient(
            timeout_seconds=settings.http_timeout_seconds,
            max_entries_per_feed=settings.max_entries_per_feed,
        )
        self.formatter = MessageFormatter()
        self._stopped = asyncio.Event()

    async def run_forever(self, bot: Bot) -> None:
        logger.info("Feed poller started with %s second interval", self.settings.poll_interval_seconds)
        while not self._stopped.is_set():
            try:
                await self.run_once(bot)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected error while polling feeds")

            try:
                await asyncio.wait_for(
                    self._stopped.wait(),
                    timeout=self.settings.poll_interval_seconds,
                )
            except asyncio.TimeoutError:
                continue

    async def stop(self) -> None:
        self._stopped.set()

    async def run_once(self, bot: Bot) -> None:
        users = await self.db.get_polling_users()
        if not users:
            return

        try:
            result = await self.feed_client.fetch(self.settings.rss_url)
        except Exception:
            logger.exception("Failed to fetch NodeSeek RSS")
            return

        entries = list(reversed(result.entries))
        for user_record in users:
            await self._handle_user(bot, user_record, entries)

    async def _handle_user(self, bot: Bot, user_record: PollingUserRecord, entries) -> None:
        enabled_keywords = [item.keyword for item in user_record.keywords if item.enabled]
        if not enabled_keywords:
            return

        category_filter = {
            slug.strip()
            for slug in user_record.settings.category_slugs.split(",")
            if slug.strip()
        }

        if not user_record.settings.initialized and self.settings.mark_as_read_on_first_poll:
            for entry in entries:
                await self.db.mark_delivered(
                    user_record.user.id,
                    entry.item_key,
                    title=entry.title,
                    link=entry.link,
                    category_slug=entry.category_slug,
                    matched_keywords=[],
                )
            await self.db.set_user_initialized(user_record.user.id)
            logger.info("User %s initialized without backfill", user_record.user.tg_user_id)
            return

        for entry in entries:
            if category_filter and entry.category_slug not in category_filter:
                continue
            if await self.db.is_delivered(user_record.user.id, entry.item_key):
                continue

            matched_keywords = match_keywords(entry.source_text, enabled_keywords)
            if not matched_keywords:
                continue

            message = self.formatter.render(
                title=entry.title,
                link=entry.link,
                matched_keywords=matched_keywords,
                category_name=entry.category_name,
            )

            delivered = False
            for target in user_record.targets:
                try:
                    await bot.send_message(
                        chat_id=target.chat_id,
                        text=message,
                        parse_mode="HTML",
                        link_preview_options=LinkPreviewOptions(
                            is_disabled=self.settings.disable_web_page_preview,
                            url=entry.link or None,
                        ),
                    )
                    delivered = True
                except Exception:
                    logger.exception(
                        "Failed to send item %s to user %s target %s",
                        entry.item_key,
                        user_record.user.tg_user_id,
                        target.chat_id,
                    )

            if delivered:
                await self.db.mark_delivered(
                    user_record.user.id,
                    entry.item_key,
                    title=entry.title,
                    link=entry.link,
                    category_slug=entry.category_slug,
                    matched_keywords=matched_keywords,
                )
                await self.db.bump_keyword_hits(user_record.user.id, matched_keywords)

        if not user_record.settings.initialized:
            await self.db.set_user_initialized(user_record.user.id)
