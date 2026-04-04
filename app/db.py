from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from app.utils import normalize_keywords, utc_now_iso


@dataclass(slots=True)
class UserRecord:
    id: int
    tg_user_id: int
    chat_id: int
    username: str | None
    first_name: str | None


@dataclass(slots=True)
class UserSettingsRecord:
    user_id: int
    category_slugs: str
    enabled: bool
    initialized: bool


@dataclass(slots=True)
class KeywordRecord:
    id: int
    user_id: int
    keyword: str
    normalized_keyword: str
    enabled: bool
    hit_count: int
    last_hit_at: str | None


@dataclass(slots=True)
class TargetRecord:
    id: int
    user_id: int
    chat_id: int
    chat_title: str | None
    chat_type: str | None
    enabled: bool


@dataclass(slots=True)
class DeliveryRecord:
    id: int
    user_id: int
    item_key: str
    title: str
    link: str
    category_slug: str | None
    matched_keywords: str
    delivered_at: str


@dataclass(slots=True)
class PollingUserRecord:
    user: UserRecord
    settings: UserSettingsRecord
    keywords: list[KeywordRecord]
    targets: list[TargetRecord]


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

                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    category_slugs TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    initialized INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    normalized_keyword TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    hit_count INTEGER NOT NULL DEFAULT 0,
                    last_hit_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, normalized_keyword),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    chat_title TEXT,
                    chat_type TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, chat_id),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS delivery_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    item_key TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    link TEXT NOT NULL DEFAULT '',
                    category_slug TEXT,
                    matched_keywords TEXT NOT NULL DEFAULT '',
                    delivered_at TEXT NOT NULL,
                    UNIQUE(user_id, item_key),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_keywords_user_id ON keywords(user_id);
                CREATE INDEX IF NOT EXISTS idx_targets_user_id ON targets(user_id);
                CREATE INDEX IF NOT EXISTS idx_delivery_history_user_id ON delivery_history(user_id);
                """
            )
            await self._migrate_legacy_schema(db)
            await db.commit()

    async def _migrate_legacy_schema(self, db: aiosqlite.Connection) -> None:
        cursor = await db.execute(
            "SELECT value FROM schema_meta WHERE key = 'legacy_subscriptions_migrated'"
        )
        row = await cursor.fetchone()
        if row is not None:
            return

        cursor = await db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'subscriptions'
            """
        )
        if await cursor.fetchone() is None:
            await db.execute(
                """
                INSERT OR REPLACE INTO schema_meta (key, value)
                VALUES ('legacy_subscriptions_migrated', '1')
                """
            )
            return

        cursor = await db.execute(
            """
            SELECT id, user_id, keywords, target_chat_id, enabled, initialized, created_at
            FROM subscriptions
            ORDER BY id ASC
            """
        )
        subscriptions = await cursor.fetchall()
        if not subscriptions:
            await db.execute(
                """
                INSERT OR REPLACE INTO schema_meta (key, value)
                VALUES ('legacy_subscriptions_migrated', '1')
                """
            )
            return

        user_agg: dict[int, dict[str, object]] = {}
        for _, user_id, keywords, target_chat_id, enabled, initialized, created_at in subscriptions:
            aggregate = user_agg.setdefault(
                user_id,
                {
                    "targets": set(),
                    "keywords": set(),
                    "enabled": False,
                    "initialized": False,
                    "created_at": created_at,
                },
            )
            aggregate["targets"].add(target_chat_id)
            aggregate["enabled"] = bool(aggregate["enabled"]) or bool(enabled)
            aggregate["initialized"] = bool(aggregate["initialized"]) or bool(initialized)
            for keyword in normalize_keywords(keywords):
                aggregate["keywords"].add(keyword)

        for user_id, aggregate in user_agg.items():
            created_at = str(aggregate["created_at"])
            await db.execute(
                """
                INSERT OR IGNORE INTO user_settings (
                    user_id, category_slugs, enabled, initialized, created_at, updated_at
                )
                VALUES (?, '', ?, ?, ?, ?)
                """,
                (
                    user_id,
                    1 if aggregate["enabled"] else 0,
                    1 if aggregate["initialized"] else 0,
                    created_at,
                    created_at,
                ),
            )
            for chat_id in aggregate["targets"]:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO targets (
                        user_id, chat_id, chat_title, chat_type, enabled, created_at, updated_at
                    )
                    VALUES (?, ?, NULL, NULL, 1, ?, ?)
                    """,
                    (user_id, int(chat_id), created_at, created_at),
                )
            for keyword in aggregate["keywords"]:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO keywords (
                        user_id, keyword, normalized_keyword, enabled, hit_count, last_hit_at, created_at, updated_at
                    )
                    VALUES (?, ?, ?, 1, 0, NULL, ?, ?)
                    """,
                    (user_id, keyword, keyword.lower(), created_at, created_at),
                )

        cursor = await db.execute(
            """
            SELECT s.user_id, d.item_key, d.delivered_at
            FROM deliveries d
            JOIN subscriptions s ON s.id = d.subscription_id
            """
        )
        for user_id, item_key, delivered_at in await cursor.fetchall():
            await db.execute(
                """
                INSERT OR IGNORE INTO delivery_history (
                    user_id, item_key, title, link, category_slug, matched_keywords, delivered_at
                )
                VALUES (?, ?, '', '', NULL, '', ?)
                """,
                (user_id, item_key, delivered_at),
            )

        await db.execute(
            """
            INSERT OR REPLACE INTO schema_meta (key, value)
            VALUES ('legacy_subscriptions_migrated', '1')
            """
        )

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

    async def ensure_user_profile(
        self,
        tg_user_id: int,
        chat_id: int,
        username: str | None,
        first_name: str | None,
        chat_title: str | None,
        chat_type: str | None,
    ) -> UserRecord:
        user = await self.upsert_user(tg_user_id, chat_id, username, first_name)
        await self.ensure_user_settings(user.id)
        if await self.count_targets_by_user_id(user.id) == 0:
            await self.add_target(
                user.id,
                chat_id,
                chat_title=chat_title,
                chat_type=chat_type,
            )
        return user

    async def ensure_user_settings(self, user_id: int) -> None:
        now = utc_now_iso()
        async with self._connect() as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO user_settings (
                    user_id, category_slugs, enabled, initialized, created_at, updated_at
                )
                VALUES (?, '', 1, 0, ?, ?)
                """,
                (user_id, now, now),
            )
            await db.commit()

    async def get_user_settings_by_tg_user(self, tg_user_id: int) -> UserSettingsRecord | None:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT us.user_id, us.category_slugs, us.enabled, us.initialized
                FROM user_settings us
                JOIN users u ON u.id = us.user_id
                WHERE u.tg_user_id = ?
                """,
                (tg_user_id,),
            )
            row = await cursor.fetchone()
        return UserSettingsRecord(*row) if row else None

    async def set_user_enabled(self, tg_user_id: int, enabled: bool) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                UPDATE user_settings
                SET enabled = ?, updated_at = ?
                WHERE user_id = (SELECT id FROM users WHERE tg_user_id = ?)
                """,
                (1 if enabled else 0, utc_now_iso(), tg_user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def set_user_initialized(self, user_id: int) -> None:
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE user_settings
                SET initialized = 1, updated_at = ?
                WHERE user_id = ?
                """,
                (utc_now_iso(), user_id),
            )
            await db.commit()

    async def set_user_categories(self, tg_user_id: int, slugs: list[str]) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                UPDATE user_settings
                SET category_slugs = ?, updated_at = ?
                WHERE user_id = (SELECT id FROM users WHERE tg_user_id = ?)
                """,
                (",".join(slugs), utc_now_iso(), tg_user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def count_keywords_by_tg_user(self, tg_user_id: int) -> int:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*)
                FROM keywords k
                JOIN users u ON u.id = k.user_id
                WHERE u.tg_user_id = ?
                """,
                (tg_user_id,),
            )
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def add_keyword(self, tg_user_id: int, keyword: str) -> tuple[bool, KeywordRecord | None]:
        normalized = keyword.strip().lower()
        if not normalized:
            return False, None
        now = utc_now_iso()
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT id
                FROM users
                WHERE tg_user_id = ?
                """,
                (tg_user_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return False, None
            user_id = int(row[0])
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO keywords (
                    user_id, keyword, normalized_keyword, enabled, hit_count, last_hit_at, created_at, updated_at
                )
                VALUES (?, ?, ?, 1, 0, NULL, ?, ?)
                """,
                (user_id, keyword.strip(), normalized, now, now),
            )
            inserted = cursor.rowcount > 0
            await db.commit()
            cursor = await db.execute(
                """
                SELECT id, user_id, keyword, normalized_keyword, enabled, hit_count, last_hit_at
                FROM keywords
                WHERE user_id = ? AND normalized_keyword = ?
                """,
                (user_id, normalized),
            )
            keyword_row = await cursor.fetchone()
        return inserted, KeywordRecord(*keyword_row) if keyword_row else None

    async def list_keywords_by_tg_user(self, tg_user_id: int) -> list[KeywordRecord]:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT k.id, k.user_id, k.keyword, k.normalized_keyword, k.enabled, k.hit_count, k.last_hit_at
                FROM keywords k
                JOIN users u ON u.id = k.user_id
                WHERE u.tg_user_id = ?
                ORDER BY k.id ASC
                """,
                (tg_user_id,),
            )
            rows = await cursor.fetchall()
        return [KeywordRecord(*row) for row in rows]

    async def set_keyword_enabled(self, tg_user_id: int, keyword_id: int, enabled: bool) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                UPDATE keywords
                SET enabled = ?, updated_at = ?
                WHERE id = ?
                  AND user_id = (SELECT id FROM users WHERE tg_user_id = ?)
                """,
                (1 if enabled else 0, utc_now_iso(), keyword_id, tg_user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_keyword(self, tg_user_id: int, keyword_id: int) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                DELETE FROM keywords
                WHERE id = ?
                  AND user_id = (SELECT id FROM users WHERE tg_user_id = ?)
                """,
                (keyword_id, tg_user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def bump_keyword_hits(self, user_id: int, normalized_keywords: list[str]) -> None:
        if not normalized_keywords:
            return
        async with self._connect() as db:
            for keyword in normalized_keywords:
                await db.execute(
                    """
                    UPDATE keywords
                    SET hit_count = hit_count + 1,
                        last_hit_at = ?,
                        updated_at = ?
                    WHERE user_id = ? AND normalized_keyword = ?
                    """,
                    (utc_now_iso(), utc_now_iso(), user_id, keyword.lower()),
                )
            await db.commit()

    async def count_targets_by_user_id(self, user_id: int) -> int:
        async with self._connect() as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM targets WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def count_targets_by_tg_user(self, tg_user_id: int) -> int:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*)
                FROM targets t
                JOIN users u ON u.id = t.user_id
                WHERE u.tg_user_id = ?
                """,
                (tg_user_id,),
            )
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def add_target(
        self,
        user_id: int,
        chat_id: int,
        *,
        chat_title: str | None,
        chat_type: str | None,
    ) -> bool:
        now = utc_now_iso()
        async with self._connect() as db:
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO targets (
                    user_id, chat_id, chat_title, chat_type, enabled, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (user_id, chat_id, chat_title, chat_type, now, now),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def add_target_by_tg_user(
        self,
        tg_user_id: int,
        chat_id: int,
        *,
        chat_title: str | None,
        chat_type: str | None,
    ) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                "SELECT id FROM users WHERE tg_user_id = ?",
                (tg_user_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return False
            user_id = int(row[0])
        return await self.add_target(
            user_id,
            chat_id,
            chat_title=chat_title,
            chat_type=chat_type,
        )

    async def list_targets_by_tg_user(self, tg_user_id: int) -> list[TargetRecord]:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT t.id, t.user_id, t.chat_id, t.chat_title, t.chat_type, t.enabled
                FROM targets t
                JOIN users u ON u.id = t.user_id
                WHERE u.tg_user_id = ?
                ORDER BY t.id ASC
                """,
                (tg_user_id,),
            )
            rows = await cursor.fetchall()
        return [TargetRecord(*row) for row in rows]

    async def delete_target(self, tg_user_id: int, target_id: int) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                DELETE FROM targets
                WHERE id = ?
                  AND user_id = (SELECT id FROM users WHERE tg_user_id = ?)
                """,
                (target_id, tg_user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def list_history_by_tg_user(self, tg_user_id: int, limit: int) -> list[DeliveryRecord]:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT d.id, d.user_id, d.item_key, d.title, d.link, d.category_slug, d.matched_keywords, d.delivered_at
                FROM delivery_history d
                JOIN users u ON u.id = d.user_id
                WHERE u.tg_user_id = ?
                ORDER BY d.id DESC
                LIMIT ?
                """,
                (tg_user_id, limit),
            )
            rows = await cursor.fetchall()
        return [DeliveryRecord(*row) for row in rows]

    async def get_polling_users(self) -> list[PollingUserRecord]:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT u.id, u.tg_user_id, u.chat_id, u.username, u.first_name,
                       us.category_slugs, us.enabled, us.initialized
                FROM users u
                JOIN user_settings us ON us.user_id = u.id
                WHERE us.enabled = 1
                ORDER BY u.id ASC
                """
            )
            user_rows = await cursor.fetchall()

            results: list[PollingUserRecord] = []
            for row in user_rows:
                user = UserRecord(*row[:5])
                settings = UserSettingsRecord(user.id, row[5], row[6], row[7])

                cursor = await db.execute(
                    """
                    SELECT id, user_id, keyword, normalized_keyword, enabled, hit_count, last_hit_at
                    FROM keywords
                    WHERE user_id = ? AND enabled = 1
                    ORDER BY id ASC
                    """,
                    (user.id,),
                )
                keyword_rows = await cursor.fetchall()
                if not keyword_rows:
                    continue

                cursor = await db.execute(
                    """
                    SELECT id, user_id, chat_id, chat_title, chat_type, enabled
                    FROM targets
                    WHERE user_id = ? AND enabled = 1
                    ORDER BY id ASC
                    """,
                    (user.id,),
                )
                target_rows = await cursor.fetchall()
                if not target_rows:
                    continue

                results.append(
                    PollingUserRecord(
                        user=user,
                        settings=settings,
                        keywords=[KeywordRecord(*item) for item in keyword_rows],
                        targets=[TargetRecord(*item) for item in target_rows],
                    )
                )

        return results

    async def is_delivered(self, user_id: int, item_key: str) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                """
                SELECT 1
                FROM delivery_history
                WHERE user_id = ? AND item_key = ?
                """,
                (user_id, item_key),
            )
            row = await cursor.fetchone()
        return row is not None

    async def mark_delivered(
        self,
        user_id: int,
        item_key: str,
        *,
        title: str,
        link: str,
        category_slug: str | None,
        matched_keywords: list[str],
    ) -> None:
        async with self._connect() as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO delivery_history (
                    user_id, item_key, title, link, category_slug, matched_keywords, delivered_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    item_key,
                    title,
                    link,
                    category_slug,
                    ",".join(matched_keywords),
                    utc_now_iso(),
                ),
            )
            await db.commit()
