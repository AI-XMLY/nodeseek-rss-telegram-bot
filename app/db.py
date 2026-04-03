from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from app.utils import utc_now_iso


@dataclass(slots=True)
class UserRecord:
    id: int
    tg_user_id: int
    chat_id: int
    username: str | None
    first_name: str | None


@dataclass(slots=True)
class SubscriptionRecord:
    id: int
    user_id: int
    feed_url: str
    feed_title: str | None
    keywords: str
    match_mode: str
    target_chat_id: int
    enabled: bool
    initialized: bool
    created_at: str


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    @asynccontextmanager
    async def _connect(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            yield db

    async def init(self) -> None:
        async with self._connect() as db:
            await db.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_user_id INTEGER NOT NULL UNIQUE,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    feed_url TEXT NOT NULL,
                    feed_title TEXT,
                    keywords TEXT NOT NULL DEFAULT '',
                    match_mode TEXT NOT NULL DEFAULT 'any',
                    target_chat_id INTEGER NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    initialized INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id INTEGER NOT NULL,
                    item_key TEXT NOT NULL,
                    delivered_at TEXT NOT NULL,
                    UNIQUE(subscription_id, item_key),
                    FOREIGN KEY(subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id
                ON subscriptions(user_id);
                """
            )
            await db.commit()

    async def upsert_user(
        self,
        tg_user_id: int,
        chat_id: int,
        username: str | None,
        first_name: str | None,
    ) -> UserRecord:
        now = utc_now_iso()
        async with self._connect() as db:
            await db.execute(
                """
                INSERT INTO users (tg_user_id, chat_id, username, first_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(tg_user_id) DO UPDATE SET
                    chat_id = excluded.chat_id,
                    username = excluded.username,
                    first_name = excluded.first_name,
                    updated_at = excluded.updated_at
                """,
                (tg_user_id, chat_id, username, first_name, now, now),
            )
            await db.commit()
            cursor = await db.execute(
                """
                SELECT id, tg_user_id, chat_id, username, first_name
                FROM users
                WHERE tg_user_id = ?
                """,
                (tg_user_id,),
            )
            row = await cursor.fetchone()
        return UserRecord(*row)

    async def add_subscription(
        self,
        user_id: int,
        feed_url: str,
        keywords: str,
        match_mode: str,
        target_chat_id: int,
    ) -> int:
        now = utc_now_iso()
        async with self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO subscriptions (
                    user_id, feed_url, keywords, match_mode, target_chat_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, feed_url, keywords, match_mode, target_chat_id, now, now),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_subscriptions_by_tg_user(self, tg_user_id: int) -> list[SubscriptionRecord]:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT s.id, s.user_id, s.feed_url, s.feed_title, s.keywords, s.match_mode,
                       s.target_chat_id, s.enabled, s.initialized, s.created_at
                FROM subscriptions s
                JOIN users u ON u.id = s.user_id
                WHERE u.tg_user_id = ?
                ORDER BY s.id ASC
                """,
                (tg_user_id,),
            )
            rows = await cursor.fetchall()
        return [SubscriptionRecord(*row) for row in rows]

    async def count_subscriptions_by_tg_user(self, tg_user_id: int) -> int:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*)
                FROM subscriptions s
                JOIN users u ON u.id = s.user_id
                WHERE u.tg_user_id = ?
                """,
                (tg_user_id,),
            )
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def get_all_enabled_subscriptions(self) -> list[SubscriptionRecord]:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT id, user_id, feed_url, feed_title, keywords, match_mode,
                       target_chat_id, enabled, initialized, created_at
                FROM subscriptions
                WHERE enabled = 1
                ORDER BY id ASC
                """
            )
            rows = await cursor.fetchall()
        return [SubscriptionRecord(*row) for row in rows]

    async def set_subscription_enabled(self, subscription_id: int, tg_user_id: int, enabled: bool) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                UPDATE subscriptions
                SET enabled = ?, updated_at = ?
                WHERE id = ?
                  AND user_id = (SELECT id FROM users WHERE tg_user_id = ?)
                """,
                (1 if enabled else 0, utc_now_iso(), subscription_id, tg_user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_subscription(self, subscription_id: int, tg_user_id: int) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                DELETE FROM subscriptions
                WHERE id = ?
                  AND user_id = (SELECT id FROM users WHERE tg_user_id = ?)
                """,
                (subscription_id, tg_user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_subscription_keywords(
        self,
        subscription_id: int,
        tg_user_id: int,
        keywords: str,
    ) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                UPDATE subscriptions
                SET keywords = ?, updated_at = ?
                WHERE id = ?
                  AND user_id = (SELECT id FROM users WHERE tg_user_id = ?)
                """,
                (keywords, utc_now_iso(), subscription_id, tg_user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_subscription_match_mode(
        self,
        subscription_id: int,
        tg_user_id: int,
        match_mode: str,
    ) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                UPDATE subscriptions
                SET match_mode = ?, updated_at = ?
                WHERE id = ?
                  AND user_id = (SELECT id FROM users WHERE tg_user_id = ?)
                """,
                (match_mode, utc_now_iso(), subscription_id, tg_user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_subscription_target_chat(
        self,
        subscription_id: int,
        tg_user_id: int,
        target_chat_id: int,
    ) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                UPDATE subscriptions
                SET target_chat_id = ?, updated_at = ?
                WHERE id = ?
                  AND user_id = (SELECT id FROM users WHERE tg_user_id = ?)
                """,
                (target_chat_id, utc_now_iso(), subscription_id, tg_user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_feed_title(self, subscription_id: int, feed_title: str | None) -> None:
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE subscriptions
                SET feed_title = ?, updated_at = ?
                WHERE id = ?
                """,
                (feed_title, utc_now_iso(), subscription_id),
            )
            await db.commit()

    async def is_delivered(self, subscription_id: int, item_key: str) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT 1
                FROM deliveries
                WHERE subscription_id = ? AND item_key = ?
                """,
                (subscription_id, item_key),
            )
            row = await cursor.fetchone()
        return row is not None

    async def mark_delivered(self, subscription_id: int, item_key: str) -> None:
        async with self._connect() as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO deliveries (subscription_id, item_key, delivered_at)
                VALUES (?, ?, ?)
                """,
                (subscription_id, item_key, utc_now_iso()),
            )
            await db.commit()

    async def set_initialized(self, subscription_id: int) -> None:
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE subscriptions
                SET initialized = 1, updated_at = ?
                WHERE id = ?
                """,
                (utc_now_iso(), subscription_id),
            )
            await db.commit()
