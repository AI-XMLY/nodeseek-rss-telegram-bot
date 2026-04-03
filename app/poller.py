from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from telegram import Bot

from app.config import Settings
from app.db import Database, SubscriptionRecord
from app.formatter import MessageFormatter
from app.rss import FeedClient, match_keywords

logger = logging.getLogger(__name__)


class FeedPoller:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db
        self.feed_client = FeedClient(
            timeout_seconds=settings.http_timeout_seconds,
            max_summary_length=settings.max_summary_length,
            max_entries_per_feed=settings.max_entries_per_feed,
        )
        self.formatter = MessageFormatter(settings)
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
        subscriptions = await self.db.get_all_enabled_subscriptions()
        for subscription in subscriptions:
            await self._handle_subscription(bot, subscription)

    async def _handle_subscription(self, bot: Bot, subscription: SubscriptionRecord) -> None:
        try:
            result = await self.feed_client.fetch(subscription.feed_url)
        except Exception:
            logger.exception("Failed to fetch feed for subscription %s", subscription.id)
            return

        await self.db.update_feed_title(subscription.id, result.feed_title)
        entries = list(reversed(result.entries))

        if not subscription.initialized and self.settings.mark_as_read_on_first_poll:
            for entry in entries:
                await self.db.mark_delivered(subscription.id, entry.item_key)
            await self.db.set_initialized(subscription.id)
            logger.info("Subscription %s initialized without backfill", subscription.id)
            return

        for entry in entries:
            if await self.db.is_delivered(subscription.id, entry.item_key):
                continue

            matched, matched_keywords = match_keywords(
                entry.source_text,
                subscription.keywords,
                subscription.match_mode,
            )
            if not matched:
                continue

            message = self.formatter.render(
                title=entry.title,
                summary=entry.summary,
                link=entry.link,
                feed_title=result.feed_title,
                matched_keywords=matched_keywords,
                published_at=entry.published_at,
            )
            try:
                await bot.send_message(
                    chat_id=subscription.target_chat_id,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=self.settings.disable_web_page_preview,
                )
            except Exception:
                logger.exception(
                    "Failed to send message for subscription %s to chat %s",
                    subscription.id,
                    subscription.target_chat_id,
                )
                continue

            await self.db.mark_delivered(subscription.id, entry.item_key)

        if not subscription.initialized:
            await self.db.set_initialized(subscription.id)

